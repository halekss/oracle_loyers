import pandas as pd
import numpy as np
import os
import random
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

# Fichiers d'entrée/sortie
INPUT_RAW_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_complet.csv")
CAVALIERS_CSV = os.path.join(data_dir, "cavaliers_lyon.csv")
OUTPUT_FINAL_CSV = os.path.join(data_dir, "master_immo_final.csv")

# Paramètres globaux
RADIUS_METERS = 500
POLYGONS_MAP = {} # Stockage des formes géographiques
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
def build_shapes_from_cavaliers():
    """Dessine les arrondissements basés sur les cavaliers"""
    print("   🎨 Construction des formes géographiques...")
    if not os.path.exists(CAVALIERS_CSV):
        print("   ⚠️ Pas de fichier cavaliers, utilisation des cercles simples.")
        return

    try:
        df_cav = pd.read_csv(CAVALIERS_CSV)
        df_cav['code_postal'] = df_cav['code_postal'].fillna(0).astype(str).apply(lambda x: x.split('.')[0])
        valid_cav = df_cav[df_cav['code_postal'].str.startswith('69')]
        grouped = valid_cav.groupby('code_postal')
        
        for cp, group in grouped:
            if len(group) >= 4:
                points = list(zip(group.longitude, group.latitude))
                hull = MultiPoint(points).convex_hull
                POLYGONS_MAP[cp] = hull.buffer(0.001)
    except Exception as e:
        print(f"   ⚠️ Erreur formes : {e}")

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

def get_point_for_zipcode(cp):
    if cp in POLYGONS_MAP:
        return get_random_point_in_polygon(POLYGONS_MAP[cp])
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

def step_geocoding(df):
    print("\n📍 ETAPE 1 : Géocodage & Jitter...")
    build_shapes_from_cavaliers()
    
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
        lat, lon = get_point_for_zipcode(row['code_postal'])
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

def step_features(df):
    print("\n🧮 ETAPE 4 : Calcul des distances (Points d'intérêt)...")
    if not os.path.exists(CAVALIERS_CSV):
        print("   ❌ Erreur : Fichier cavaliers manquant.")
        return df

    df_cav = pd.read_csv(CAVALIERS_CSV)
    categories = df_cav['categorie_cavalier'].unique()
    
    for cat in categories:
        subset_cav = df_cav[df_cav['categorie_cavalier'] == cat]
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
# MAIN PIPELINE
# =============================================================================
def main():
    print("🚀 DÉMARRAGE DU PIPELINE ETL COMPLET")
    print(f"📂 Entrée : {INPUT_RAW_CSV}")
    print(f"📂 Sortie : {OUTPUT_FINAL_CSV}")

    # 1. Chargement initial
    if not os.path.exists(INPUT_RAW_CSV):
        print("❌ Fichier d'entrée introuvable.")
        return
    
    df = pd.read_csv(INPUT_RAW_CSV)
    
    # 2. Exécution séquentielle en mémoire
    df = step_geocoding(df)
    df = step_quartiers(df)
    df = step_types(df)
    df = step_features(df)
    df = step_ids(df)

    # 3. Sauvegarde finale
    print(f"\n💾 Sauvegarde finale vers {OUTPUT_FINAL_CSV}...")
    df.to_csv(OUTPUT_FINAL_CSV, index=False)
    print("✨ TERMINÉ ! Le fichier master est prêt.")

if __name__ == "__main__":
    main()