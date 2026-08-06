"""
Nettoyage ponctuel des annonces mortes dans master_immo_final.csv + carte (ORA-134).

master_immo_final.csv (carte Leaflet via generate_map.py, /api/listings,
entraînement du modèle) est un fichier différent de annonces.db, généré
indépendamment par clean_immo.py — le nettoyage de annonces.db
(prune_dead_annonces.py / recheck_dead_annonces.py) ne le concernait pas.
Il ne contient pas non plus de colonne date_dernier_scan (fichier généré
avant le correctif TTL, ORA-134), donc le TTL structurel ne le nettoiera pas
tant que le pipeline complet (data_fusion.py -> clean_immo.py) n'aura pas
tourné avec des données fraîchement re-scrapées.

Même stratégie de vérification que recheck_dead_annonces.py (HTTP rapide via
check_url_status, navigateur headless en repli via check_url_status_browser
pour les urls ambiguës — réutilisés tels quels, une seule source de vérité
pour la détection). Retire les lignes confirmées mortes de
master_immo_final.csv (écriture atomique) puis régénère la carte
(generate_map.py) pour que le correctif soit visible dans l'app.

N'affecte PAS le modèle ML (price_predictor.pkl) : les lignes retirées ici
restent des points de prix historiques statistiquement valables pour
l'entraînement même si le lien source a expiré. Un ré-entraînement éventuel
sur le dataset filtré est un choix produit séparé, pas fait ici.

Usage :
    python scripts/prune_dead_map_listings.py [--dry-run] [--skip-map-regen] [--limit N]
"""
import argparse
import os
import random
import subprocess
import sys
import time

import pandas as pd
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
backend_dir = os.path.join(repo_root, "backend")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.prune_dead_annonces import (  # noqa: E402
    DEFAULT_DELAY_RANGE,
    check_url_status,
)
from recheck_dead_annonces import (  # noqa: E402
    BROWSER_DELAY_RANGE,
    check_url_status_browser,
)
from scraper_utils import (  # noqa: E402
    get_chrome_driver,
    get_scraper_logger,
    pick_proxy,
    pick_user_agent,
)

logger = get_scraper_logger("prune_dead_map_listings")

MASTER_CSV_PATH = os.path.join(backend_dir, "data", "master_immo_final.csv")
GENERATE_MAP_SCRIPT = os.path.join(backend_dir, "scripts", "generate_map.py")
# generate_map.py dépend de folium/pandas installés dans backend/.venv, pas
# scripts/.venv (Selenium) : sys.executable pointerait vers le mauvais
# interpréteur puisque ce script tourne sous scripts/.venv.
BACKEND_PYTHON = os.path.join(backend_dir, ".venv", "bin", "python")


def _write_csv_atomically(df, path):
    """Écrit dans un fichier temporaire puis remplace `path` via os.replace
    (atomique) — même principe que csv_atomic_writer.py utilisé par les
    scrapers (ORA-12) : en cas d'échec avant le replace, le fichier existant
    reste intact."""
    tmp_path = f"{path}.tmp"
    df.to_csv(tmp_path, index=False)
    os.replace(tmp_path, path)


def prune_dead_map_listings(
    csv_path=MASTER_CSV_PATH,
    delay_range=DEFAULT_DELAY_RANGE,
    browser_delay_range=BROWSER_DELAY_RANGE,
    dry_run=False,
    regenerate_map=True,
    limit=None,
    checker=check_url_status,
    browser_checker=check_url_status_browser,
    driver_factory=None,
    generate_map_script=GENERATE_MAP_SCRIPT,
    map_python=BACKEND_PYTHON,
):
    """Vérifie chaque url de `csv_path` (HTTP puis navigateur headless pour les
    ambiguës) et retire les lignes confirmées mortes (sauf `dry_run=True`).
    Régénère la carte après une purge réelle, sauf `regenerate_map=False`.

    Renvoie {"total", "dead", "deleted", "still_ambiguous"}.
    """
    df = pd.read_csv(csv_path)
    driver_factory = driver_factory or (
        lambda: get_chrome_driver(user_agent=pick_user_agent(), proxy=pick_proxy(), headless=True)
    )

    session = requests.Session()
    dead_indices = []
    ambiguous_indices = []
    try:
        for idx, row in df.iterrows():
            url = row.get("url")
            if not isinstance(url, str) or not url.strip():
                continue

            status = checker(url, session)
            if status is True:
                dead_indices.append(idx)
            elif status is None:
                ambiguous_indices.append(idx)

            time.sleep(random.uniform(*delay_range))
    finally:
        session.close()

    logger.info(
        "%s ligne(s) confirmée(s) morte(s) (HTTP), %s ambiguë(s) à re-vérifier via navigateur.",
        len(dead_indices), len(ambiguous_indices),
    )
    if limit is not None:
        ambiguous_indices = ambiguous_indices[:limit]

    still_ambiguous = 0
    if ambiguous_indices:
        driver = driver_factory()
        try:
            for idx in ambiguous_indices:
                url = df.at[idx, "url"]
                status = browser_checker(url, driver)

                if status is True:
                    dead_indices.append(idx)
                    logger.info("Confirmée morte (navigateur) : %s", url)
                elif status is None:
                    still_ambiguous += 1

                time.sleep(random.uniform(*browser_delay_range))
        finally:
            driver.quit()

    deleted = 0
    if dead_indices and not dry_run:
        cleaned_df = df.drop(index=dead_indices).reset_index(drop=True)
        _write_csv_atomically(cleaned_df, csv_path)
        deleted = len(dead_indices)
        logger.info("%s -> %s lignes après purge, écrit dans %s", len(df), len(cleaned_df), csv_path)

        if regenerate_map:
            logger.info("Régénération de la carte (generate_map.py)...")
            subprocess.run([map_python, generate_map_script], check=True)

    logger.info(
        "Terminé : %s lignes vérifiées, %s mortes (%s supprimées%s), %s toujours ambiguës.",
        len(df), len(dead_indices), deleted, " — dry-run" if dry_run else "", still_ambiguous,
    )
    return {
        "total": len(df),
        "dead": len(dead_indices),
        "deleted": deleted,
        "still_ambiguous": still_ambiguous,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Vérifie et logue sans rien modifier.")
    parser.add_argument("--skip-map-regen", action="store_true", help="Ne régénère pas la carte après la purge.")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limite le nombre de lignes ambiguës re-vérifiées via navigateur (debug/tests).",
    )
    args = parser.parse_args()
    prune_dead_map_listings(dry_run=args.dry_run, regenerate_map=not args.skip_map_regen, limit=args.limit)
