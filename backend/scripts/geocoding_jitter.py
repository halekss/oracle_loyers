import pandas as pd
import numpy as np
import os
import random
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
# CORRECTION ICI : On remonte d'un niveau (..) pour trouver le dossier data
data_dir = os.path.join(script_dir, '..', 'data')

INPUT_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_complet.csv")
OUTPUT_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_geocoded.csv")

# 🗺️ ZONES PAR ARRONDISSEMENT (Mode Manuel / Hors-Ligne)
LYON_ZONES = {
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

def get_point_in_circle(center_lat, center_lon, radius):
    """Génère un point aléatoire uniforme dans un cercle"""
    angle = random.uniform(0, 2 * np.pi)
    r = radius * np.sqrt(random.uniform(0, 1)) 
    lat = center_lat + r * np.cos(angle)
    lon = center_lon + r * np.sin(angle)
    return lat, lon

def get_point_for_zipcode(cp):
    """Attribue des coordonnées GPS en fonction du code postal."""
    if cp in LYON_ZONES:
        zone = LYON_ZONES[cp]
        return get_point_in_circle(zone["lat"], zone["lon"], zone["radius"])
    else:
        # Fallback : Centre Lyon
        return get_point_in_circle(45.7640, 4.8357, 0.02)

def clean_zipcode(val):
    try:
        return str(int(float(val))).strip()
    except:
        return str(val).strip()

# --- MAIN ---
print("🚀 Démarrage du Géocodage Manuel...")

if not os.path.exists(INPUT_CSV):
    print(f"❌ Fichier non trouvé: {INPUT_CSV}")
    print(f"👉 Vérifie que le fichier est bien dans : {os.path.abspath(data_dir)}")
    exit()

df = pd.read_csv(INPUT_CSV)
print(f"📂 {len(df)} annonces chargées.")

# Nettoyage
df['code_postal'] = df['code_postal'].fillna(69000).apply(clean_zipcode)

# Génération
lats = []
lons = []

for index, row in df.iterrows():
    cp = row['code_postal']
    lat, lon = get_point_for_zipcode(cp)
    lats.append(lat)
    lons.append(lon)

df['latitude'] = lats
df['longitude'] = lons

df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Terminé ! Fichier généré : {OUTPUT_CSV}")
print("⚠️ N'oublie pas de relancer 'compute_features.py' pour mettre à jour les distances !")