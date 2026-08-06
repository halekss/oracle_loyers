"""
Nettoyage ponctuel des annonces mortes dans annonces.db (ORA-134).

Le pipeline de scraping n'a jamais eu de mécanisme de suppression : une annonce
retirée/louée/expirée sur le site source reste indéfiniment dans annonces.db
(cf. ORA-134, LEGAL_DECISIONS.md non concerné ici — pas de question légale,
juste de la fraîcheur de données). Ce script vérifie en direct chaque url
encore en base et retire celles confirmées introuvables sur le site source.

Volontairement conservateur : seul un 404/410 HTTP explicite déclenche une
suppression. Un statut ambigu (403 anti-bot, timeout, 5xx, redirection vers
autre chose) est laissé tel quel plutôt que de risquer de supprimer à tort une
annonce encore active à cause d'un blocage anti-scraping — voir
`DEAD_STATUS_CODES` ci-dessous. Ne détecte donc pas les "soft 404" (page HTTP
200 avec un message "annonce non disponible") : hors périmètre de cette
première passe, trop spécifique à chaque site pour être fiable sans plus de
maintenance.

C'est un nettoyage ponctuel du stock déjà accumulé ; le correctif structurel
qui évite que le problème ne revienne (TTL par re-scraping) est dans
`clean_immo.py` (étape de purge par ancienneté de `date_dernier_scan`).

Usage :
    python backend/scripts/prune_dead_annonces.py [--dry-run]
"""
import argparse
import logging
import os
import random
import sys
import time

import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services import annonces_store  # noqa: E402 (après le sys.path.insert nécessaire)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEAD_STATUS_CODES = {404, 410}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
REQUEST_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept-Language": "fr-FR,fr;q=0.9",
}
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_DELAY_RANGE = (0.4, 0.9)


def check_url_status(url, session, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Vérifie une url en direct. Renvoie True (confirmée morte), False (vivante),
    ou None (statut ambigu : ni l'un ni l'autre ne peut être affirmé, à conserver
    par prudence plutôt que de risquer une suppression à tort)."""
    try:
        response = session.get(
            url, headers=REQUEST_HEADERS, timeout=timeout, allow_redirects=True
        )
    except requests.RequestException as exc:
        logger.warning("Statut ambigu pour %s (%s) : conservée par prudence.", url, exc)
        return None

    if response.status_code in DEAD_STATUS_CODES:
        return True
    if response.status_code == 200:
        return False

    logger.warning(
        "Statut ambigu pour %s (HTTP %s) : conservée par prudence.", url, response.status_code
    )
    return None


def _fetch_all_annonces(db_path):
    """Snapshot complet (id, url, titre) pris avant toute suppression : évite le
    bug classique de pagination OFFSET/LIMIT quand on supprime des lignes en
    cours de parcours (list_annonces() n'est pas adaptée à cet usage)."""
    conn = annonces_store.get_connection(db_path)
    try:
        rows = conn.execute("SELECT id, url, titre FROM annonces ORDER BY id").fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def prune_dead_annonces(
    db_path=None,
    delay_range=DEFAULT_DELAY_RANGE,
    dry_run=False,
    checker=check_url_status,
):
    """Vérifie chaque annonce de `db_path` (DEFAULT_DB_PATH si None) et supprime
    celles confirmées mortes (sauf `dry_run=True`, qui se contente de compter).

    Renvoie {"checked", "dead", "deleted", "ambiguous"}.
    """
    db_path = db_path or annonces_store.DEFAULT_DB_PATH
    annonces = _fetch_all_annonces(db_path)
    session = requests.Session()

    checked = dead = deleted = ambiguous = 0
    try:
        for annonce in annonces:
            checked += 1
            status = checker(annonce["url"], session)

            if status is True:
                dead += 1
                logger.info("Morte (404/410) : %s — %s", annonce["url"], annonce.get("titre"))
                if not dry_run:
                    if annonces_store.delete_annonce(annonce_id=annonce["id"], db_path=db_path):
                        deleted += 1
            elif status is None:
                ambiguous += 1

            time.sleep(random.uniform(*delay_range))
    finally:
        session.close()

    logger.info(
        "Terminé : %s vérifiées, %s mortes (%s supprimées%s), %s ambiguës (conservées).",
        checked, dead, deleted, " — dry-run" if dry_run else "", ambiguous,
    )
    return {"checked": checked, "dead": dead, "deleted": deleted, "ambiguous": ambiguous}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dry-run", action="store_true", help="Vérifie et logue sans rien supprimer."
    )
    args = parser.parse_args()
    prune_dead_annonces(dry_run=args.dry_run)
