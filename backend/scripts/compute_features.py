import pandas as pd
import numpy as np
import os
from sklearn.neighbors import BallTree

# --- CONFIGURATION ---
# Chemins relatifs (on est dans scripts/, on remonte vers data/)
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')

PATH_IMMO = os.path.join(data_dir, "base_de_donnees_immo_lyon_geocoded.csv")
PATH_CAVALIERS = os.path.join(data_dir, "cavaliers_lyon.csv")
OUTPUT_PATH = os.path.join(data_dir, "master_immo_final.csv")

# Rayon pour le calcul de densité (ex: combien de bars à moins de 500m ?)
RADIUS_METERS = 500

def get_nearest_distance_and_count(df_main, df_poi, poi_name):
    """
    Calcule la distance au point le plus proche et le nombre de points dans le rayon
    pour une catégorie donnée (ex: Kebabs).
    """
    if len(df_poi) == 0:
        return np.full(len(df_main), np.nan), np.zeros(len(df_main))

    # 1. Conversion en radians pour BallTree (la Terre est ronde !)
    # On a besoin de [lat, lon]
    coords_main = np.radians(df_main[['latitude', 'longitude']].values)
    coords_poi = np.radians(df_poi[['latitude', 'longitude']].values)

    # 2. Création de l'arbre (BallTree est optimisé pour les calculs géographiques)
    tree = BallTree(coords_poi, metric='haversine')

    # 3. Distance au plus proche (k=1)
    # query retourne (distances, indices). La distance est en radians.
    dist_rad, _ = tree.query(coords_main, k=1)
    
    # Conversion radians -> mètres (Terre ~ 6371 km)
    earth_radius = 6371000
    dist_meters = dist_rad[:, 0] * earth_radius

    # 4. Compte dans le rayon (query_radius)
    radius_rad = RADIUS_METERS / earth_radius
    counts = tree.query_radius(coords_main, r=radius_rad, count_only=True)

    return dist_meters, counts

# --- MAIN ---

print("🏗️  Chargement des données...")
if not os.path.exists(PATH_IMMO) or not os.path.exists(PATH_CAVALIERS):
    print(f"❌ Erreur : Fichiers manquants dans {data_dir}")
    print(f"Immo : {os.path.exists(PATH_IMMO)}")
    print(f"Cavaliers : {os.path.exists(PATH_CAVALIERS)}")
    exit()

df_immo = pd.read_csv(PATH_IMMO)
df_cav = pd.read_csv(PATH_CAVALIERS)

print(f"🏠 Annonces Immo : {len(df_immo)}")
print(f"🦄 Points d'intérêt : {len(df_cav)}")

# On récupère toutes les catégories uniques dans le fichier cavaliers
# Ex: 'Vice - Kebab', 'Superstition - Cimetière'
categories = df_cav['categorie_cavalier'].unique()

print(f"🧐 Catégories détectées : {categories}")

# Boucle sur chaque catégorie de "Vice"
for cat in categories:
    # On filtre les cavaliers pour ne garder que cette catégorie
    subset_cav = df_cav[df_cav['categorie_cavalier'] == cat]
    
    # Nom des futures colonnes (ex: dist_Vice_Kebab)
    # On nettoie le nom pour qu'il soit propre (pas d'espaces, pas de tirets bizarres)
    clean_name = cat.replace(" - ", "_").replace(" ", "_").lower()
    col_dist = f"dist_{clean_name}"
    col_count = f"nb_{clean_name}_{RADIUS_METERS}m"

    print(f"🚀 Traitement de : {cat} ({len(subset_cav)} lieux)...")
    
    # Calcul magique
    distances, counts = get_nearest_distance_and_count(df_immo, subset_cav, cat)
    
    # Ajout au tableau principal
    df_immo[col_dist] = distances.round(0) # Arrondi au mètre
    df_immo[col_count] = counts

# Nettoyage final : Remplacer les NaN (cas où aucun POI n'existe) par une valeur par défaut ?
# Pour les distances, si pas de POI, on peut laisser NaN ou mettre une grande valeur.
# On laisse NaN pour l'instant, le modèle gérera ou on fera un fillna plus tard.

print(f"💾 Export vers {OUTPUT_PATH}...")
df_immo.to_csv(OUTPUT_PATH, index=False)
print("✅ Calculs terminés avec succès !")