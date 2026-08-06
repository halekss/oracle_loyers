"""Récupère une fois les polygones des 9 arrondissements de Lyon (Nominatim/
OSM) et les écrit dans backend/data/lyon_arrondissements.geojson (ORA-104).

Script ponctuel, pas exécuté à runtime par l'app : la couche "Quartiers" de
generate_map.py lit le GeoJSON versionné dans le repo, sans dépendance
réseau. À relancer uniquement si les tracés OSM sont mis à jour.

Données © contributeurs OpenStreetMap, ODbL 1.0 — https://www.openstreetmap.org/copyright
"""
import json
import os
import time

import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
OUTPUT_PATH = os.path.join(DATA_DIR, 'lyon_arrondissements.geojson')

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim exige un User-Agent identifiant l'appelant (politique d'usage) :
# https://operations.osmfoundation.org/policies/nominatim/
USER_AGENT = "oracle-loyers-dev-script/1.0 (portfolio project, one-time fetch)"

# Politique Nominatim : 1 requête/seconde maximum.
REQUEST_DELAY_S = 1.1


def ordinal_label(numero):
    return "1er" if numero == 1 else f"{numero}e"


def fetch_arrondissement_boundary(numero):
    """Récupère le polygone GeoJSON d'un arrondissement de Lyon via Nominatim."""
    label = ordinal_label(numero)
    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": f"Lyon {label} Arrondissement, France",
            "format": "geojson",
            "polygon_geojson": 1,
            "limit": 1,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    features = data.get("features") or []
    if not features:
        raise ValueError(f"Aucun résultat Nominatim pour l'arrondissement {numero}")

    return {
        "type": "Feature",
        "properties": {"nom": f"Lyon {label}", "arrondissement": numero},
        "geometry": features[0]["geometry"],
    }


def main():
    features = []
    for numero in range(1, 10):
        print(f"Récupération de l'arrondissement {ordinal_label(numero)}...")
        features.append(fetch_arrondissement_boundary(numero))
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

    print(f"✅ {len(features)} arrondissements écrits dans {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
