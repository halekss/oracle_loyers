import pandas as pd
import requests as r
import numpy as np
import os
import time
from tqdm import tqdm

# --- CONFIGURATION ---
# Définition dynamique du dossier data (backend/data) par rapport au script (backend/scripts)
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')

INPUT_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_complet.csv")
OUTPUT_CSV = os.path.join(data_dir, "base_de_donnees_immo_lyon_geocoded.csv")

# Paramètres
JITTER_RANGE = 0.003
MAX_RETRIES = 3
BASE_SLEEP = 0.2

def get_lat_lon_smart(query):
    """Interroge l'API avec Retry et Timeout"""
    url = "https://api-adresse.data.gouv.fr/search/"
    params = {'q': query, 'limit': 1}
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Timeout court pour ne pas bloquer si l'API lag
            response = r.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data['features']:
                    coords = data['features'][0]['geometry']['coordinates']
                    return coords[1], coords[0] # lat, lon
                else:
                    return None, None # Pas trouvé
            
            elif response.status_code in [429, 503, 504]:
                # Trop de requêtes ou serveur down -> on attend
                time.sleep(2 ** attempt) # Backoff exponentiel
            else:
                return None, None # Erreur client (400, 404...)
                
        except r.exceptions.RequestException:
            time.sleep(1)

    return None, None

# --- MAIN ---

if not os.path.exists(INPUT_CSV):
    print(f"❌ Erreur : Le fichier d'entrée est introuvable ici : {INPUT_CSV}")
    exit()

print("🚀 Chargement des données...")
df = pd.read_csv(INPUT_CSV)

# 1. Construction de la requête API
# On combine : Adresse (si dispo, sinon juste Ville) + CP
# Ici, comme on n'a pas l'adresse précise, on va faire : CP + Ville + Description (début) pour tenter d'être précis
# OU PLUS SIMPLE : On prend le CP + Ville + un bout du titre pour varier, 
# mais l'API adresse.data.gouv est faite pour des adresses postales.
# Stratégie : On va géocoder le "Code Postal + Ville" (centre du quartier) 
# puis appliquer le Jitter pour disperser.

# Création colonne pour requête
df['api_query'] = df['code_postal'].astype(str) + " " + df['ville'] + " France"

# 2. Géocodage (avec cache pour ne pas requêter 50 fois "69003 Lyon")
unique_queries = df['api_query'].unique()
print(f"🌍 {len(unique_queries)} lieux uniques à géolocaliser (ex: '69003 Lyon France')...")

loc_mapping = {}

for query in tqdm(unique_queries, desc="📡 Requêtes API"):
    if pd.isna(query) or query.strip() == "France": continue
    
    lat, lon = get_lat_lon_smart(query)
    
    if lat and lon:
        loc_mapping[query] = (lat, lon)
    else:
        print(f"⚠️ Non trouvé : {query}")
    
    time.sleep(BASE_SLEEP)

# 3. Application
print("📍 Application des coordonnées...")
df['ref_lat'] = df['api_query'].map(lambda x: loc_mapping.get(x, (None, None))[0])
df['ref_lon'] = df['api_query'].map(lambda x: loc_mapping.get(x, (None, None))[1])

# Vérification des pertes
missing = df[df['ref_lat'].isna()]
if len(missing) > 0:
    print(f"⚠️ {len(missing)} annonces perdues. Exemples de lieux non trouvés :")
    print(missing['api_query'].unique()[:5])

df = df.dropna(subset=['ref_lat', 'ref_lon'])

# 4. Jitter
print("🎲 Ajout du bruit aléatoire...")
jitter_lat = np.random.uniform(-JITTER_RANGE, JITTER_RANGE, size=len(df))
jitter_lon = np.random.uniform(-JITTER_RANGE, JITTER_RANGE, size=len(df))

# Latitude : 1 deg ~= 111km. 0.003 ~= 300m
# Longitude : dépend de la latitude, mais à Lyon similaire.
df['latitude'] = df['ref_lat'] + jitter_lat
df['longitude'] = df['ref_lon'] + jitter_lon

# Nettoyage
final_df = df.drop(columns=['api_query', 'ref_lat', 'ref_lon'])

print(f"💾 Sauvegarde dans {OUTPUT_CSV}...")
final_df.to_csv(OUTPUT_CSV, index=False)
print("✅ Terminé !")