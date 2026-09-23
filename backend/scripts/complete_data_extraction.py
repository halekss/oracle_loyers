import argparse
import pandas as pd
import re
import time
import os
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

from http_retry import request_with_retry

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')

# Headers pour imiter un vrai navigateur (évite le blocage)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
}


def resolve_paths(ville):
    """Chemins d'entrée/sortie pour une ville donnée (slug scraping_config.json,
    ex: 'lyon'/'lille') — un seul script pour toutes les villes déclarées,
    au lieu d'un chemin Lyon codé en dur (ORA-71)."""
    return (
        os.path.join(data_dir, f"annonces_{ville}_vizzit.csv"),
        os.path.join(data_dir, f"annonces_{ville}_vizzit_geoloc_complete.csv"),
    )


# Coordonnées réelles de l'annonce, dans un objet JS structuré propre à
# Vizzit (constaté sur le HTML réel d'une fiche annonce, 2026-08-11) :
#   window.advert = { coordinates: { latitude: 50.63381, longitude: 3.06689, ... } }
# Signal fiable et indépendant de la ville (contrairement aux anciennes
# stratégies codées en dur sur des préfixes lyonnais 45./4., qui ne
# matchaient donc jamais pour Lille (50./3.) — c'est pourquoi aucune
# coordonnée Lille n'était récupérée). Une autre valeur
# ("CurrentCountryCoordinates":{"Latitude":46.6...}) existe aussi sur la
# page mais c'est le centre géographique de la France, pas celui de
# l'annonce : le motif ci-dessous cible spécifiquement l'objet
# "coordinates" de "advert" pour ne jamais la capturer par erreur.
COORDINATES_RE = re.compile(r'coordinates:\s*\{\s*latitude:\s*([\d.]+),\s*longitude:\s*([\d.]+)')

# Repli : meta tags Open Graph (présents sur certains portails, souvent
# absents de Vizzit lui-même mais gardés au cas où une autre source les ait).
META_LAT_RE = re.compile(r'property=["\'](?:og:latitude|place:location:latitude)["\']\s+content=["\']([\d.]+)["\']')
META_LON_RE = re.compile(r'property=["\'](?:og:longitude|place:location:longitude)["\']\s+content=["\']([\d.]+)["\']')


def extract_coordinates_from_html(html):
    """Coordonnées GPS (lat, lon) trouvées dans le HTML d'une fiche annonce,
    ou (None, None) si rien de fiable n'a été trouvé. Fonction pure, testable
    sans réseau : c'est ce qui décide si get_gps_from_url renvoie un
    résultat, indépendamment de la récupération HTTP elle-même."""
    match = COORDINATES_RE.search(html)
    if match:
        return float(match.group(1)), float(match.group(2))

    lat_meta = META_LAT_RE.search(html)
    lon_meta = META_LON_RE.search(html)
    if lat_meta and lon_meta:
        return float(lat_meta.group(1)), float(lon_meta.group(1))

    return None, None


def get_gps_from_url(url):
    """Télécharge la page et en extrait les coordonnées GPS réelles."""
    if pd.isna(url) or "vizzit.fr" not in str(url):
        return None, None

    try:
        # Timeout explicite + retry/backoff sur erreur transitoire (modèle http_retry)
        r = request_with_retry("GET", url, headers=HEADERS, timeout=10)

        if r is None or r.status_code != 200:
            return None, None

        return extract_coordinates_from_html(r.text)
    except Exception:
        return None, None

def process_row(args):
    """Fonction exécutée par chaque thread"""
    index, row = args
    lat, lon = get_gps_from_url(row['Lien'])
    return index, lat, lon

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Complète les annonces Vizzit avec leurs coordonnées GPS réelles.")
    parser.add_argument('--ville', default='lyon', help="Slug de la ville (cf. scraping_config.json), ex: lyon, lille.")
    args = parser.parse_args()
    input_file, output_file = resolve_paths(args.ville)

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
        # On garde Adresse_Extraite car c'est utile pour vérifier. DerniereVue
        # (ORA-134, TTL par re-scraping) doit survivre à cette étape intermédiaire
        # pour rester exploitable par data_fusion.py.
        cols = ['Lieu', 'Prix', 'Details', 'Lien', 'DerniereVue', 'Lat', 'Lon', 'Adresse_Extraite']
        # Si des colonnes manquent dans le fichier source, on ne plante pas
        final_cols = [c for c in cols if c in df.columns]

        final_df = df[final_cols]
        final_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        print(f"\n✅ Terminé ! Coordonnées récupérées : {found_count} / {len(df)}")
        print(f"💾 Fichier final généré : {output_file}")
        print("\n--- Aperçu ---")
        print(final_df[['Lieu', 'Lat', 'Lon']].head())

    else:
        print(f"❌ Fichier d'entrée introuvable : {input_file}")
