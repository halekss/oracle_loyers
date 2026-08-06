import pandas as pd
import numpy as np
import os
import random
import sys
import warnings
import re
from shapely.geometry import MultiPoint, Point
from sklearn.neighbors import BallTree

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION ET CHEMINS
# =============================================================================
print("⚙️  Configuration du pipeline...")
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
backend_dir = os.path.dirname(script_dir)

# backend/services (annonces_store) n'est pas sur sys.path par défaut quand ce
# script est lancé depuis backend/scripts/ (ex: `python clean_immo.py`, ou
# l'étape DAG Airflow `clean_immo`) plutôt que depuis backend/ (comme app.py).
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services import annonces_store  # noqa: E402 (après le sys.path.insert nécessaire)

# Fichiers d'entrée/sortie
INPUT_RAW_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_complet.csv")
CAVALIERS_CSV = os.path.join(data_dir, "cavaliers_lyon.csv")
OUTPUT_FINAL_CSV = os.path.join(data_dir, "master_immo_final.csv")
ANNONCES_DB_PATH = os.path.join(data_dir, "annonces.db")

# Paramètres globaux
RADIUS_METERS = 500
# Seed fixe du jitter géographique : garantit qu'à données brutes égales,
# deux exécutions du pipeline produisent des coordonnées identiques (donc
# des features de distance et un modèle identiques). Ne pas changer sans
# ré-entraîner et recommitter price_predictor.pkl.
GEOCODING_JITTER_SEED = 42
# Nombre de jours au-delà duquel une annonce non re-confirmée par le scraping
# est considérée expirée et exclue du pipeline (ORA-134 : le pipeline n'avait
# auparavant aucun mécanisme de suppression, les annonces retirées/louées sur
# le site source restaient indéfiniment). ~2 runs hebdomadaires de marge pour
# absorber un run manqué/en échec sans purger à tort une annonce encore active.
TTL_JOURS_DERNIER_SCAN = 14
FALLBACK_ZONES = {
    "69001": {"lat": 45.7705, "lon": 4.8306, "radius": 0.005},
    "69002": {"lat": 45.7533, "lon": 4.8327, "radius": 0.008},
    "69003": {"lat": 45.7562, "lon": 4.8655, "radius": 0.015},
    "69004": {"lat": 45.7770, "lon": 4.8270, "radius": 0.007},
    "69005": {"lat": 45.7580, "lon": 4.8050, "radius": 0.008},
    "69006": {"lat": 45.7690, "lon": 4.8550, "radius": 0.007},
    "69007": {"lat": 45.7350, "lon": 4.8380, "radius": 0.015},
    "69008": {"lat": 45.7380, "lon": 4.8700, "radius": 0.010},
    "69009": {"lat": 45.7780, "lon": 4.8030, "radius": 0.012},
    "69100": {"lat": 45.7720, "lon": 4.8850, "radius": 0.020},
}

# =============================================================================
# ETAPE 1 : GEOCODING & JITTER (geocoding_jitter.py)
# =============================================================================
def build_shapes_from_cavaliers(cavaliers_csv_path=CAVALIERS_CSV):
    """Dessine les arrondissements basés sur les cavaliers.

    Renvoie un dict {code_postal: shapely.Polygon} au lieu de muter un global,
    pour rester testable avec des entrées/sorties explicites.
    """
    print("   🎨 Construction des formes géographiques...")
    polygons_map = {}

    if not os.path.exists(cavaliers_csv_path):
        print("   ⚠️ Pas de fichier cavaliers, utilisation des cercles simples.")
        return polygons_map

    try:
        df_cav = pd.read_csv(cavaliers_csv_path)
        df_cav['code_postal'] = df_cav['code_postal'].fillna(0).astype(str).apply(lambda x: x.split('.')[0])
        valid_cav = df_cav[df_cav['code_postal'].str.startswith('69')]
        grouped = valid_cav.groupby('code_postal')

        for cp, group in grouped:
            if len(group) >= 4:
                points = list(zip(group.longitude, group.latitude))
                hull = MultiPoint(points).convex_hull
                polygons_map[cp] = hull.buffer(0.001)
    except Exception as e:
        print(f"   ⚠️ Erreur formes : {e}")

    return polygons_map

def get_random_point_in_polygon(polygon):
    minx, miny, maxx, maxy = polygon.bounds
    for _ in range(100):
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(p):
            return p.y, p.x
    return polygon.centroid.y, polygon.centroid.x

def get_point_in_circle(center_lat, center_lon, radius):
    angle = random.uniform(0, 2 * np.pi)
    r = radius * np.sqrt(random.uniform(0, 1))
    return center_lat + r * np.cos(angle), center_lon + r * np.sin(angle)

def get_point_for_zipcode(cp, polygons_map):
    if cp in polygons_map:
        return get_random_point_in_polygon(polygons_map[cp])
    elif cp in FALLBACK_ZONES:
        z = FALLBACK_ZONES[cp]
        return get_point_in_circle(z["lat"], z["lon"], z["radius"])
    else:
        return get_point_in_circle(45.7640, 4.8357, 0.02)

def clean_zipcode(val):
    try:
        return str(int(float(val))).strip()
    except:
        return str(val).strip()

def step_prune_expired(df, ttl_days=TTL_JOURS_DERNIER_SCAN, reference_date=None):
    """Exclut les annonces dont `date_dernier_scan` dépasse `ttl_days` (ORA-134) :
    une annonce non revue par le scraping depuis trop longtemps est considérée
    disparue du site source (louée, expirée, retirée) plutôt que de rester
    indéfiniment dans `master_immo_final.csv`/`annonces.db`.

    Conservateur par construction : une ligne sans `date_dernier_scan` exploitable
    (colonne absente du CSV d'entrée, ou valeur manquante/invalide — cas des
    lignes écrites avant l'ajout de cette colonne aux 6 scrapers) est conservée
    plutôt que purgée, faute d'information pour trancher. Le stock déjà
    accumulé avant ce correctif n'est donc nettoyé qu'au fil des prochains runs
    de scraping, pas rétroactivement ici (cf. le nettoyage ponctuel
    `prune_dead_annonces.py`, basé sur une vérification HTTP directe, pour le
    stock déjà en place au moment de ce correctif).
    """
    print("\n🗑️  ETAPE 0 : Purge des annonces expirées (TTL)...")

    if 'date_dernier_scan' not in df.columns:
        print("   ⚠️  Colonne 'date_dernier_scan' absente (CSV antérieur à ORA-134) : purge ignorée.")
        return df

    reference_date = reference_date or pd.Timestamp.now(tz='UTC').normalize()
    dernier_scan = pd.to_datetime(df['date_dernier_scan'], errors='coerce', utc=True)
    age_jours = (reference_date - dernier_scan).dt.days

    # NaN (date manquante/invalide) : comparaison pandas -> False -> conservée.
    expiree = age_jours > ttl_days
    if expiree.any():
        print(f"   ✅ {int(expiree.sum())} annonce(s) expirée(s) (non revue(s) depuis >{ttl_days}j) exclue(s).")
    else:
        print("   ✅ Aucune annonce expirée.")
    return df[~expiree].reset_index(drop=True)


def step_geocoding(df, cavaliers_csv_path=CAVALIERS_CSV, seed=GEOCODING_JITTER_SEED):
    print("\n📍 ETAPE 1 : Géocodage & Jitter...")
    random.seed(seed)
    polygons_map = build_shapes_from_cavaliers(cavaliers_csv_path)

    df['code_postal'] = df['code_postal'].fillna(69000).apply(clean_zipcode)
    
    lats, lons = [], []
    for _, row in df.iterrows():
        # --- MODIFICATION START : Si coordonnées présentes (Vizzit), on garde ---
        if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')) and row.get('latitude') != "" and row.get('longitude') != "":
             try:
                lats.append(float(row['latitude']))
                lons.append(float(row['longitude']))
                continue # On passe à la ligne suivante
             except:
                pass # Si erreur conversion, on génère
        # --- MODIFICATION END ---

        # Sinon (pas de coords), on génère comme avant
        lat, lon = get_point_for_zipcode(row['code_postal'], polygons_map)
        lats.append(lat)
        lons.append(lon)
    
    df['latitude'] = lats
    df['longitude'] = lons
    print(f"   ✅ {len(df)} annonces placées sur la carte.")
    return df

# =============================================================================
# ETAPE 2 : ASSIGNATION QUARTIERS (quartier_assignation.py)
# =============================================================================
def trouver_quartier(row):
    lat, lon = row['latitude'], row['longitude']
    if pd.isna(row['code_postal']): return "Inconnu"
    try: cp = str(int(float(row['code_postal'])))
    except: cp = str(row['code_postal'])

    if pd.isna(lat) or pd.isna(lon): return f"Secteur {cp}"

    if cp == '69001': return "Pentes Croix-Rousse" if lat > 45.769 else "Terreaux / Hotel de Ville"
    if cp == '69002': return "Confluence" if lat < 45.749 else "Ainay" if lat < 45.756 else "Bellecour / Cordeliers"
    if cp == '69003': return "Montchat" if lon > 4.875 else "Préfecture / Quais" if lon < 4.848 else "Part-Dieu / Villette"
    if cp == '69004': return "Croix-Rousse Plateau"
    if cp == '69005': return "Vieux Lyon" if lon > 4.818 else "Point du Jour / St Just"
    if cp == '69006': return "Brotteaux / Foch"
    if cp == '69007': return "Gerland" if lat < 45.736 else "Guillotière / Jean Macé"
    if cp == '69008': return "Monplaisir / Bachut"
    if cp == '69009': return "Vaise / Valmy"
    return "Grand Lyon / Autre"

def step_quartiers(df):
    print("\n🗺️  ETAPE 2 : Détermination des quartiers...")
    df['quartier'] = df.apply(trouver_quartier, axis=1)
    print("   ✅ Quartiers assignés.")
    return df

# =============================================================================
# ETAPE 3 : MISE A JOUR DES TYPES (update_types.py)
# =============================================================================
def determine_type_local(row):
    text = (str(row.get('type', '')) + " " + str(row.get('description', ''))).lower()
    surface = row.get('surface', 0)

    if re.search(r'\b(t[4-9]|f[4-9]|[4-9]\s*pièce|maison)\b', text): return 'Grand (T4+)'
    if re.search(r'\b(t3|f3|3\s*pièce)\b', text): return 'T3'
    if re.search(r'\b(t2|f2|2\s*pièce)\b', text): return 'T2'
    if re.search(r'\b(t1|f1|1\s*pièce|studio)\b', text): return 'Studio/T1'

    try:
        s = float(surface)
        if s < 35: return 'Studio/T1'
        elif s < 55: return 'T2'
        elif s < 75: return 'T3'
        else: return 'Grand (T4+)'
    except: return 'Inconnu'

def step_types(df):
    print("\n🏠 ETAPE 3 : Classification des types (T1, T2...)...")
    df['type_local'] = df.apply(determine_type_local, axis=1)
    print("   ✅ Types mis à jour.")
    return df

# =============================================================================
# ETAPE 4 : CALCUL FEATURES (compute_features.py)
# =============================================================================
def get_nearest_distance_and_count(df_main, df_poi):
    if len(df_poi) == 0:
        return np.full(len(df_main), np.nan), np.zeros(len(df_main))

    coords_main = np.radians(df_main[['latitude', 'longitude']].values)
    coords_poi = np.radians(df_poi[['latitude', 'longitude']].values)
    
    tree = BallTree(coords_poi, metric='haversine')
    dist_rad, _ = tree.query(coords_main, k=1)
    dist_meters = dist_rad[:, 0] * 6371000
    
    radius_rad = RADIUS_METERS / 6371000
    counts = tree.query_radius(coords_main, r=radius_rad, count_only=True)
    
    return dist_meters, counts

def step_features(df, df_cavaliers):
    """Calcule les distances/comptages aux points d'intérêt.

    `df_cavaliers` est fourni explicitement par l'appelant (plutôt que lu depuis un
    chemin de fichier en dur) pour rester testable avec un petit jeu de données en mémoire.
    Un `df_cavaliers` vide est un cas limite valide : `df` est renvoyé inchangé.
    """
    print("\n🧮 ETAPE 4 : Calcul des distances (Points d'intérêt)...")
    if df_cavaliers is None or df_cavaliers.empty:
        print("   ⚠️ Pas de données cavaliers, aucune feature de distance calculée.")
        return df

    categories = df_cavaliers['categorie_cavalier'].unique()

    for cat in categories:
        subset_cav = df_cavaliers[df_cavaliers['categorie_cavalier'] == cat]
        clean_name = cat.replace(" - ", "_").replace(" ", "_").lower()
        
        # Calculs
        dists, counts = get_nearest_distance_and_count(df, subset_cav)
        
        # Assignation colonnes
        df[f"dist_{clean_name}"] = np.round(dists, 0)
        df[f"nb_{clean_name}_{RADIUS_METERS}m"] = counts
        print(f"   🔹 {cat} traité.")
        
    print("   ✅ Features calculées.")
    return df

# =============================================================================
# ETAPE 5 : CORRECTION IDS (fix_ids.py)
# =============================================================================
def step_ids(df):
    print("\n🔧 ETAPE 5 : Réindexation des IDs...")
    df['id_annonce'] = range(1, len(df) + 1)
    print(f"   ✅ {len(df)} annonces réindexées.")
    return df

# =============================================================================
# ETAPE 6 : SYNCHRONISATION DU STORE SQLITE (ORA-112)
# =============================================================================
def build_titre(row):
    """Pas de vrai champ 'titre' dans le CSV master (seulement 'description',
    un texte libre déjà nettoyé par data_fusion.py) : on synthétise un titre
    court et lisible à partir du type de bien + quartier, cohérent avec ce
    qu'affiche AnnonceCard.jsx."""
    type_local = str(row.get('type_local') or '').strip()
    quartier = str(row.get('quartier') or '').strip()
    if type_local and quartier:
        return f"{type_local} — {quartier}"
    return type_local or quartier or str(row.get('description') or '').strip()[:80] or None


def step_sync_annonces_store(df, db_path=ANNONCES_DB_PATH):
    """Alimente la table SQLite `annonces` (services/annonces_store.py) à partir
    du dataframe final, pour que `/api/annonces` (liste "Annonces récentes",
    tracking de clics) ait réellement des données à servir — jusqu'ici cette
    table n'était peuplée que par les tests unitaires, jamais par le pipeline
    (ORA-112). `upsert_annonce` dédoublonne par `url` (contrainte UNIQUE),
    donc rejouer cette étape sur les mêmes annonces les met juste à jour.
    """
    print("\n🗃️  ETAPE 6 : Synchronisation du store annonces (SQLite)...")
    annonces_store.init_db(db_path)

    synced = 0
    skipped = 0
    for _, row in df.iterrows():
        url = row.get('url')
        if not isinstance(url, str) or not url.strip():
            skipped += 1
            continue

        image = row.get('image')
        images = [image] if isinstance(image, str) and image.strip() else None

        try:
            annonces_store.upsert_annonce(
                titre=build_titre(row),
                prix=float(row['prix']) if pd.notna(row.get('prix')) else None,
                surface=float(row['surface']) if pd.notna(row.get('surface')) else None,
                ville=row.get('ville') or None,
                quartier=row.get('quartier') or None,
                url=url,
                images=images,
                db_path=db_path,
            )
            synced += 1
        except ValueError:
            # url vide/blanche après strip malgré le filtre ci-dessus (garde-fou) :
            # upsert_annonce lève ValueError plutôt que d'insérer une ligne invalide.
            skipped += 1

    print(f"   ✅ {synced} annonces synchronisées, {skipped} ignorées (url manquante).")
    return df

# =============================================================================
# MAIN PIPELINE
# =============================================================================
def load_cavaliers(cavaliers_csv_path=CAVALIERS_CSV):
    """Charge le CSV des cavaliers, ou un DataFrame vide (mêmes colonnes) s'il est absent."""
    if os.path.exists(cavaliers_csv_path):
        return pd.read_csv(cavaliers_csv_path)
    return pd.DataFrame(columns=['categorie_cavalier', 'type_osm', 'nom_lieu', 'latitude', 'longitude'])

def main():
    print("🚀 DÉMARRAGE DU PIPELINE ETL COMPLET")
    print(f"📂 Entrée : {INPUT_RAW_CSV}")
    print(f"📂 Sortie : {OUTPUT_FINAL_CSV}")

    # 1. Chargement initial
    if not os.path.exists(INPUT_RAW_CSV):
        print("❌ Fichier d'entrée introuvable.")
        return

    df = pd.read_csv(INPUT_RAW_CSV)
    df_cavaliers = load_cavaliers(CAVALIERS_CSV)

    # 2. Exécution séquentielle en mémoire (orchestration pure, pas de logique métier ici)
    df = step_prune_expired(df)
    df = step_geocoding(df, CAVALIERS_CSV)
    df = step_quartiers(df)
    df = step_types(df)
    df = step_features(df, df_cavaliers)
    df = step_ids(df)

    # 3. Sauvegarde finale
    print(f"\n💾 Sauvegarde finale vers {OUTPUT_FINAL_CSV}...")
    df.to_csv(OUTPUT_FINAL_CSV, index=False)
    print("✨ TERMINÉ ! Le fichier master est prêt.")

    # 4. Synchronisation du store SQLite consommé par /api/annonces (ORA-112)
    step_sync_annonces_store(df)

if __name__ == "__main__":
    main()