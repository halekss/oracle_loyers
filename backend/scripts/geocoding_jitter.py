import pandas as pd
import numpy as np
import os
import random
import warnings
from shapely.geometry import MultiPoint, Point

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
# On remonte d'un niveau pour trouver le dossier data
data_dir = os.path.join(script_dir, '..', 'data')

INPUT_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_complet.csv")
CAVALIERS_CSV = os.path.join(data_dir, "cavaliers_lyon.csv")
OUTPUT_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_geocoded.csv")

# 🗺️ ZONES DE SECOURS (Cercles)
# Utilisées uniquement si on n'a pas assez de cavaliers pour dessiner un polygone
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

# Dictionnaire global pour stocker les formes géométriques calculées
POLYGONS_MAP = {}

def build_shapes_from_cavaliers():
    """Lit les cavaliers et dessine les frontières des arrondissements"""
    print("🎨 Dessin des arrondissements basé sur les cavaliers...")
    
    if not os.path.exists(CAVALIERS_CSV):
        print("⚠️ Pas de fichier cavaliers trouvé, on utilisera les cercles simples.")
        return

    try:
        df_cav = pd.read_csv(CAVALIERS_CSV)
        # Nettoyage CP
        df_cav['code_postal'] = df_cav['code_postal'].fillna(0).astype(str).apply(lambda x: x.split('.')[0])
        
        # On ne garde que les codes postaux valides (on ignore le '0' hors zone)
        valid_cav = df_cav[df_cav['code_postal'].str.startswith('69')]
        
        grouped = valid_cav.groupby('code_postal')
        
        for cp, group in grouped:
            # Il faut au moins 4 points pour faire une forme fiable
            if len(group) >= 4:
                points = list(zip(group.longitude, group.latitude))
                # Création de l'enveloppe convexe (l'élastique autour des clous)
                hull = MultiPoint(points).convex_hull
                # On ajoute un petit "buffer" (marge) de 0.001 degrés (~100m) pour lisser
                POLYGONS_MAP[cp] = hull.buffer(0.001)
                
        print(f"✅ {len(POLYGONS_MAP)} arrondissements dessinés avec précision.")
        
    except Exception as e:
        print(f"⚠️ Erreur lors du calcul des formes : {e}")

def get_random_point_in_polygon(polygon):
    """Trouve un point aléatoire DANS le polygone"""
    minx, miny, maxx, maxy = polygon.bounds
    # On essaie jusqu'à trouver un point dedans
    for _ in range(100):
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(p):
            return p.y, p.x # Lat, Lon
    # Si échec (forme trop bizarre), on retourne le centre
    return polygon.centroid.y, polygon.centroid.x

def get_point_in_circle(center_lat, center_lon, radius):
    """Fallback : Cercle simple"""
    angle = random.uniform(0, 2 * np.pi)
    r = radius * np.sqrt(random.uniform(0, 1))
    lat = center_lat + r * np.cos(angle)
    lon = center_lon + r * np.sin(angle)
    return lat, lon

def get_point_for_zipcode(cp):
    """Logique principale : Polygone Cavalier > Cercle Secours > Centre Lyon"""
    
    # 1. Priorité absolue : Forme réelle dessinée par les cavaliers
    if cp in POLYGONS_MAP:
        return get_random_point_in_polygon(POLYGONS_MAP[cp]), "Polygone"
    
    # 2. Secours : Cercle manuel défini en haut du script
    elif cp in FALLBACK_ZONES:
        zone = FALLBACK_ZONES[cp]
        return get_point_in_circle(zone["lat"], zone["lon"], zone["radius"]), "Cercle"
    
    # 3. Dernier recours : Centre ville (Hotel de ville)
    else:
        return get_point_in_circle(45.7640, 4.8357, 0.02), "Defaut"

def clean_zipcode(val):
    try:
        return str(int(float(val))).strip()
    except:
        return str(val).strip()

# --- MAIN ---
print("🚀 Démarrage du Géocodage (Mode : Enveloppe Convexe)...")

if not os.path.exists(INPUT_CSV):
    print(f"❌ Fichier non trouvé: {INPUT_CSV}")
    exit()

# 1. On construit les formes
build_shapes_from_cavaliers()

# 2. On place les annonces
df = pd.read_csv(INPUT_CSV)
print(f"📂 {len(df)} annonces à placer.")

df['code_postal'] = df['code_postal'].fillna(69000).apply(clean_zipcode)

lats = []
lons = []
stats_method = {"Polygone": 0, "Cercle": 0, "Defaut": 0}

for index, row in df.iterrows():
    cp = row['code_postal']
    
    # Appel de la fonction corrigée
    (lat, lon), method = get_point_for_zipcode(cp)
    
    lats.append(lat)
    lons.append(lon)
    stats_method[method] += 1

df['latitude'] = lats
df['longitude'] = lons

df.to_csv(OUTPUT_CSV, index=False)

print("\n" + "="*50)
print(f"✅ TERMINÉ ! Fichier généré : {OUTPUT_CSV}")
print("📊 Méthode de placement utilisée :")
print(f"   🔹 Polygone (Précis)  : {stats_method['Polygone']} annonces")
print(f"   🔸 Cercle (Approx)    : {stats_method['Cercle']} annonces")
print(f"   🔻 Défaut (Inconnu)   : {stats_method['Defaut']} annonces")
print("="*50)
print("⚠️ RELANCE 'compute_features.py' pour mettre à jour les distances !")