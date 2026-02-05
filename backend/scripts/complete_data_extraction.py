import pandas as pd
import requests
import re
import time
import os
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')

# Fichier d'entrée (celui qui a déjà les infos Prix/Lieu/Lien)
input_file = os.path.join(data_dir, "annonces_lyon_vizzit_clean_final.csv")
# Fichier de sortie
output_file = os.path.join(data_dir, "annonces_lyon_vizzit_geoloc_complete.csv")

# Headers pour imiter un vrai navigateur (évite le blocage)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
}

def get_gps_from_url(url):
    """Télécharge la page et extrait les coordonnées GPS brutes via Regex"""
    if pd.isna(url) or "vizzit.fr" not in str(url):
        return None, None
        
    try:
        # On télécharge le code source de la page
        # On utilise une session pour garder les cookies si besoin
        with requests.Session() as s:
            r = s.get(url, headers=HEADERS, timeout=10)
            
            if r.status_code != 200:
                return None, None
                
            html = r.text
        
        # --- STRATÉGIE DE RECHERCHE ---
        
        # 1. Meta Tags (Souvent le plus propre pour Facebook/Google)
        # <meta property="og:latitude" content="45.7..." />
        lat_meta = re.search(r'property=["\'](?:og:latitude|place:location:latitude)["\']\s+content=["\']([\d\.]+)["\']', html)
        lon_meta = re.search(r'property=["\'](?:og:longitude|place:location:longitude)["\']\s+content=["\']([\d\.]+)["\']', html)
        
        if lat_meta and lon_meta:
            return float(lat_meta.group(1)), float(lon_meta.group(1))

        # 2. Variables Javascript (Mapbox/Leaflet/Google)
        # "lat": 45.75, "lng": 4.85
        # On cherche des objets JSON proches
        match_lat = re.search(r'["\']?lat(?:itude)?["\']?\s*[:=]\s*(45\.\d{3,})', html)
        match_lng = re.search(r'["\']?l(?:ng|on|ongitude)?["\']?\s*[:=]\s*(4\.\d{3,})', html)
        
        if match_lat and match_lng:
            return float(match_lat.group(1)), float(match_lng.group(1))

        # 3. Tableaux de coordonnées [4.8, 45.7]
        # Attention ordre GeoJSON : [Lon, Lat]
        match_arr = re.search(r'\[\s*(4\.\d{3,})\s*,\s*(45\.\d{3,})\s*\]', html)
        if match_arr:
            return float(match_arr.group(2)), float(match_arr.group(1)) # Lat, Lon
            
    except Exception:
        pass
        
    return None, None

def process_row(args):
    """Fonction exécutée par chaque thread"""
    index, row = args
    lat, lon = get_gps_from_url(row['Lien'])
    return index, lat, lon

if __name__ == "__main__":
    print("🚀 Démarrage de l'assemblage FINAL (Infos + GPS)...")
    
    if os.path.exists(input_file):
        df = pd.read_csv(input_file)
        print(f"📊 {len(df)} annonces à traiter.")
        
        # Préparation des colonnes
        df['Lat'] = None
        df['Lon'] = None
        
        # Liste des tâches (tuples index/row)
        tasks = list(df.iterrows())
        
        print("⏳ Récupération des coordonnées sur chaque fiche (Multithread)...")
        # On lance 10 navigateurs en parallèle
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(tqdm(executor.map(process_row, tasks), total=len(tasks)))
            
        # Intégration des résultats
        found_count = 0
        for idx, lat, lon in results:
            if lat and lon:
                df.at[idx, 'Lat'] = lat
                df.at[idx, 'Lon'] = lon
                found_count += 1
        
        # Sélection des colonnes demandées + Sauvegarde
        # On garde Adresse_Extraite car c'est utile pour vérifier
        cols = ['Lieu', 'Prix', 'Details', 'Lien', 'Lat', 'Lon', 'Adresse_Extraite']
        # Si des colonnes manquent dans le fichier source, on ne plante pas
        final_cols = [c for c in cols if c in df.columns]
        
        final_df = df[final_cols]
        final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ Terminé ! Coordonnées récupérées : {found_count} / {len(df)}")
        print(f"💾 Fichier final généré : {output_file}")
        print("\n--- Aperçu ---")
        print(final_df[['Lieu', 'Lat', 'Lon']].head())
        
    else:
        print("❌ Fichier d'entrée (annonces_lyon_vizzit_clean_final.csv) introuvable.")