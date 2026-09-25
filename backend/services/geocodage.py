"""Géocodage d'une adresse de Lyon via la Géoplateforme de l'IGN (ORA-180).

Gratuit, sans clé. Seule la chaîne « 52 rue André Bollier » (+ le code postal
déjà connu) part vers l'API : ni URL, ni description, ni prix. Jamais bloquant :
toute erreur réseau renvoie None (l'annonce retombe sur le code postal) et
n'est pas mise en cache ; un « aucun résultat » de l'API, lui, l'est.
"""
import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

URL = "https://data.geopf.fr/geocodage/search"
CITYCODE_LYON = "69123"
SCORE_MIN = 0.7
TIMEOUT_S = 5
ESSAIS = 2
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "geocodage_cache.json")

_cache = None


def _charger_cache(path):
    global _cache
    if _cache is None:
        try:
            with open(path, encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, ValueError):
            _cache = {}
    return _cache


def _interroger(adresse, postcode):
    params = {"q": f"{adresse} Lyon", "citycode": CITYCODE_LYON, "limit": 1}
    if postcode:
        params["postcode"] = postcode
    for essai in range(ESSAIS):
        try:
            r = requests.get(URL, params=params, timeout=TIMEOUT_S)
            r.raise_for_status()
            return r.json().get("features", [])
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Géocodage « %s » (essai %d/%d) : %s", adresse, essai + 1, ESSAIS, exc)
    return None


def geocoder(adresse, postcode=None, cache_path=CACHE_PATH):
    """{'lat', 'lon', 'precision': 'numero'|'rue', 'cp'} ou None.

    `postcode` (arrondissement déjà connu) restreint la recherche ; la validation
    croisée du résultat reste à la charge de l'appelant.
    """
    cache = _charger_cache(cache_path)
    cle = f"{adresse.lower()}|{postcode or ''}"
    if cle not in cache:
        features = _interroger(adresse, postcode)
        if features is None:
            return None
        cache[cle] = None
        if features:
            p = features[0]["properties"]
            lon, lat = features[0]["geometry"]["coordinates"]
            precision = {"housenumber": "numero", "street": "rue"}.get(p.get("type"))
            if precision and p.get("score", 0) >= SCORE_MIN:
                cache[cle] = {"lat": lat, "lon": lon, "precision": precision, "cp": p.get("postcode")}
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
        except OSError as exc:
            logger.warning("Cache géocodage non écrit : %s", exc)
    return cache[cle]
