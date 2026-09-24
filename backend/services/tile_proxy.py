"""Proxy des tuiles du fond de carte CARTO.

CARTO exige une clé API sur ses tuiles. Mettre cette clé dans une URL chargée
par le navigateur l'expose (onglet réseau, sources de la page) : c'est donc le
backend qui appelle CARTO avec la clé, le navigateur ne demande ses tuiles
qu'à notre API (`/api/tiles/<z>/<x>/<y>.png`) et ne voit jamais la clé.

Sans `CARTO_API_KEY`, les tuiles sont quand même servies (CARTO répond avec un
filigrane « API KEY REQUIRED ») : dégradation visible, pas une panne.
"""
import os
from functools import lru_cache

import requests

CARTO_TILE_URL = "https://{sub}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
SUBDOMAINS = "abcd"
MAX_ZOOM = 19
UPSTREAM_TIMEOUT_S = 10
# Tuiles gardées en mémoire (~15 Ko chacune) : évite de rappeler CARTO pour la
# même tuile à chaque utilisateur/affichage.
TILE_CACHE_SIZE = 1024


def is_valid_tile(z, x, y):
    """Coordonnées de tuile plausibles : 0 <= z <= MAX_ZOOM, x et y dans [0, 2^z)."""
    return 0 <= z <= MAX_ZOOM and 0 <= x < 2 ** z and 0 <= y < 2 ** z


def build_upstream_url(z, x, y, retina=False):
    """URL CARTO d'une tuile (sans la clé : elle voyage en paramètre séparé)."""
    return CARTO_TILE_URL.format(
        sub=SUBDOMAINS[(x + y) % len(SUBDOMAINS)], z=z, x=x, y=y, r="@2x" if retina else "",
    )


@lru_cache(maxsize=TILE_CACHE_SIZE)
def get_tile(z, x, y, retina=False):
    """Contenu PNG d'une tuile ; lève `requests.RequestException` si CARTO échoue
    (les échecs ne sont pas mis en cache par `lru_cache`)."""
    params = {}
    api_key = os.environ.get("CARTO_API_KEY", "").strip()
    if api_key:
        params["key"] = api_key
    response = requests.get(build_upstream_url(z, x, y, retina), params=params, timeout=UPSTREAM_TIMEOUT_S)
    response.raise_for_status()
    return response.content
