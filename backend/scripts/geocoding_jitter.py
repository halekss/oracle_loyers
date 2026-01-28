import pandas as pd
import requests as r
import numpy as np
import os
from tqdm import tqdm
from shapely.geometry import shape, Point
from shapely.ops import unary_union
import random
import time

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')

INPUT_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_complet.csv")
OUTPUT_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_geocoded.csv")

# Liste des codes postaux qu'on veut cartographier précisément
TARGET_ZIPS = [
    "69001", "69002", "69003", "69004", "69005", 
    "69006", "69007", "69008", "69009", "69100" # Villeurbanne aussi
]

# Cache pour stocker les formes géométriques (Polygones)
POLYGON_MAP = {}
ALL_LYON_POLYGON = None # Pour gérer le cas "69000"

def load_polygons():
    """Télécharge les formes officielles des arrondissements au démarrage"""
    global ALL_LYON_POLYGON
    print("🌍 Téléchargement des frontières officielles des arrondissements...")
    
    polygons_list = []
    
    for cp in tqdm(TARGET_ZIPS, desc="Chargement cartes"):
        # On interroge l'API Gouv pour avoir le contour du code postal
        url = "https://geo.api.gouv.fr/communes"
        params = {
            'codePostal': cp,
            'fields': 'contour',
            'format': 'geojson',
            'geometry': 'contour'
        }
        
        try:
            res = r.get(url, params=params, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data and 'features' in data:
                    # Conversion JSON -> Objet Mathématique Shapely
                    geom = shape(data['features'][0]['geometry'])
                    POLYGON_MAP[cp] = geom
                    polygons_list.append(geom)
            time.sleep(0.1) # Politesse API
        except Exception as e:
            print(f"⚠️ Impossible de charger la carte pour {cp}: {e}")

    # On crée une forme géante "Grand Lyon" pour les codes postaux pourris (69000)
    if polygons_list:
        ALL_LYON_POLYGON = unary_union(polygons_list)
        print("✅ Carte globale assemblée avec succès.")

def get_random_point_in_polygon(polygon):
    """Trouve un point GPS valide à l'intérieur d'un polygone"""
    if not polygon: return 45.76, 4.83 # Fallback centre Lyon
    
    min_x, min_y, max_x, max_y = polygon.bounds
    
    # On essaie 50 fois de trouver un point DANS la forme
    for _ in range(50):
        # On tire au hasard dans le carré englobant
        p = Point(random.uniform(min_x, max_x), random.uniform(min_y, max_y))
        # On vérifie si le point est vraiment DANS la forme (pas dans le Rhône ou hors frontières)
        if polygon.contains(p):
            return p.y, p.x # Latitude, Longitude
            
    # Si échec, on rend le centre du quartier
    return polygon.centroid.y, polygon.centroid.x

# --- MAIN ---
print("🚀 Démarrage du Jittering par Polygones...")

# 1. On charge les cartes
load_polygons()

if not os.path.exists(INPUT_CSV):
    print(f"❌ Fichier non trouvé: {INPUT_CSV}")
    exit()

df = pd.read_csv(INPUT_CSV)
lats = []
lons = []

# 2. On traite chaque ligne
for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Placement des annonces"):
    cp = str(row['code_postal']).replace('.0', '').strip()
    
    target_poly = None
    
    # Cas 1 : Code Postal connu (ex: 69003)
    if cp in POLYGON_MAP:
        target_poly = POLYGON_MAP[cp]
    
    # Cas 2 : Code Postal générique (69000) ou inconnu
    elif ALL_LYON_POLYGON:
        # On place au hasard n'importe où dans Lyon
        target_poly = ALL_LYON_POLYGON
    
    # Génération du point
    lat, lon = get_random_point_in_polygon(target_poly)
    lats.append(lat)
    lons.append(lon)

df['latitude'] = lats
df['longitude'] = lons

# Sauvegarde
df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Terminé ! Fichier généré : {OUTPUT_CSV}")
print("⚠️ N'oublie pas de relancer le calcul des distances (feature engineering) maintenant !")