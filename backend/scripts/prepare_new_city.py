"""Détecte le régime "code postal" d'une ville avant de l'ajouter (ORA-160).

Lyon (1 CP = 1 arrondissement) et Lille (1 CP partagé par ~10 quartiers) ont
chacun demandé une logique de placement/jitter différente dans clean_immo.py,
découverte après coup. Ce script interroge l'API publique officielle
geo.api.gouv.fr et classe la ville :

  lyon_like            arrondissements municipaux, un CP chacun (Lyon, Marseille)
  lille_like           un CP principal partagé par les quartiers, éventuels CP
                       secondaires partagés avec d'autres communes (Lille)
  hybride_a_verifier   plusieurs CP propres à la ville, sans arrondissements
                       (ex. Bordeaux) : ni l'un ni l'autre, à décider à la main

Usage : python prepare_new_city.py Bordeaux

Sortie : un rapport JSON (stdout) + un squelette de bloc `scraping_config.json`
à compléter à la main. Ce script n'écrit JAMAIS dans scraping_config.json.
"""
import json
import re
import sys
import unicodedata

import requests

GEO_API_URL = "https://geo.api.gouv.fr/communes"

SOURCES = ("century21", "orpi", "pap", "paruvendu", "seloger", "vizzit")


def _get(**params):
    response = requests.get(GEO_API_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_commune(nom):
    results = _get(nom=nom, boost="population", limit=1, fields="nom,code,codesPostaux,population")
    if not results:
        raise ValueError(f"Aucune commune trouvée pour « {nom} »")
    return results[0]


def fetch_arrondissements(code_commune):
    return _get(type="arrondissement-municipal", codeParent=code_commune, fields="nom,codesPostaux")


def fetch_shared_postal_codes(commune):
    """CP de la commune aussi utilisés par une autre commune."""
    shared = []
    for cp in commune["codesPostaux"]:
        others = _get(codePostal=cp, type="commune-actuelle", fields="code")
        if any(o["code"] != commune["code"] for o in others):
            shared.append(cp)
    return shared


def classify(codes_postaux, arrondissements, shared_postal_codes):
    """Renvoie (régime, raison). Fonction pure : testable sans réseau."""
    cps = set(codes_postaux)

    arrondissement_cps = [cp for a in arrondissements for cp in a["codesPostaux"]]
    if arrondissements and len(arrondissement_cps) == len(arrondissements) and set(arrondissement_cps) == cps:
        return "lyon_like", f"{len(arrondissements)} arrondissements, 1 CP chacun, couvrant tous les CP de la commune"

    if len(cps) == 1:
        return "lille_like", "un seul CP pour toute la commune (partagé par tous les quartiers)"

    # ponytail: heuristique — des CP secondaires partagés avec d'autres
    # communes (Lille : 59160, 59260) signalent des communes absorbées à CP
    # distinctif, comme Lille. Ne voit pas le découpage réel en quartiers :
    # le résultat reste à confirmer à la main (squelette jamais appliqué).
    if shared_postal_codes:
        return "lille_like", f"CP principal + CP secondaires partagés avec d'autres communes : {sorted(shared_postal_codes)}"

    return "hybride_a_verifier", f"{len(cps)} CP propres à la ville, sans arrondissements municipaux"


def slugify(nom):
    ascii_nom = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_nom.lower()).strip("-")


def build_config_skeleton(commune):
    principal = sorted(commune["codesPostaux"])[0]
    skeleton = {
        "nom": commune["nom"],
        "slug": slugify(commune["nom"]),
        "code_postal_defaut": principal,
    }
    for source in SOURCES:
        skeleton[source] = {"base_url": "A_COMPLETER"}
    return skeleton


def build_report(nom):
    commune = fetch_commune(nom)
    arrondissements = fetch_arrondissements(commune["code"])
    shared = fetch_shared_postal_codes(commune)
    regime, raison = classify(commune["codesPostaux"], arrondissements, shared)
    return {
        "ville": commune["nom"],
        "code_insee": commune["code"],
        "population": commune.get("population"),
        "codes_postaux": commune["codesPostaux"],
        "regime": regime,
        "raison": raison,
        "squelette_scraping_config": build_config_skeleton(commune),
    }


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage : python prepare_new_city.py <nom de la ville>")
    print(json.dumps(build_report(sys.argv[1]), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
