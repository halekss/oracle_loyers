"""Récupère une fois les contours réels des quartiers de Lille (+ Lomme,
Hellemmes) via Nominatim/OSM et les écrit dans
backend/data/lille_quartiers.geojson (ORA-157).

Pendant de fetch_lyon_arrondissements.py : script ponctuel, pas exécuté à
runtime, aucune dépendance à des données déjà présentes dans le repo (source
= API publique uniquement). À relancer uniquement si les tracés OSM changent.

Si OSM n'a pas de contour polygonal pour un nom (simple point), l'entrée est
signalée et ignorée plutôt que d'écrire un point/bbox à sa place.

Données © contributeurs OpenStreetMap, ODbL 1.0 — https://www.openstreetmap.org/copyright
"""
import json
import os
import sys
import time

import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
OUTPUT_PATH = os.path.join(DATA_DIR, 'lille_quartiers.geojson')

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Politique d'usage Nominatim : User-Agent identifiant + 1 requête/seconde max.
# https://operations.osmfoundation.org/policies/nominatim/
USER_AGENT = "oracle-loyers-dev-script/1.0 (portfolio project, one-time fetch)"
REQUEST_DELAY_S = 1.1

# Mêmes noms que QUARTIERS_LILLE (clean_immo.py) + communes associées.
QUARTIERS = [
    "Lille-Centre", "Vieux-Lille", "Wazemmes", "Lille-Moulins",
    "Vauban-Esquermes", "Lille-Sud", "Faubourg de Béthune", "Bois Blancs",
    "Fives", "Saint-Maurice Pellevoisin", "Lomme", "Hellemmes", "Euralille",
]

POLYGON_TYPES = ("Polygon", "MultiPolygon")


def fetch_boundary(nom):
    """Renvoie une Feature GeoJSON polygonale pour `nom`, ou None si OSM n'a
    pas de contour (résultat absent ou simple point)."""
    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": f"{nom}, Lille, France",
            "format": "geojson",
            "polygon_geojson": 1,
            # Plusieurs candidats : le 1er résultat est parfois un point
            # (commerce, arrêt de métro) homonyme du quartier.
            "limit": 5,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    for feature in response.json().get("features") or []:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") in POLYGON_TYPES:
            return {
                "type": "Feature",
                "properties": {"nom": nom},
                "geometry": geometry,
            }
    return None


def main():
    features = []
    for nom in QUARTIERS:
        print(f"Récupération de {nom}...")
        feature = fetch_boundary(nom)
        if feature is None:
            print(f"   ⚠️  pas de contour polygonal OSM pour {nom}, ignoré", file=sys.stderr)
        else:
            features.append(feature)
        time.sleep(REQUEST_DELAY_S)

    geojson = {
        "type": "FeatureCollection",
        "properties": {
            "source": "OpenStreetMap contributors, via Nominatim",
            "licence": "ODbL 1.0 — https://www.openstreetmap.org/copyright",
        },
        "features": features,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False)

    print(f"✅ {len(features)}/{len(QUARTIERS)} contours écrits dans {OUTPUT_PATH}")
    if len(features) < 10:
        sys.exit("❌ moins de 10 contours récupérés : critère d'acceptation ORA-157 non atteint")


if __name__ == "__main__":
    main()
