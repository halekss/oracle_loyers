"""
Re-vérification via navigateur furtif (undetected_chromedriver) des annonces
restées "ambiguës" après le nettoyage HTTP simple
(backend/scripts/prune_dead_annonces.py) — typiquement des 403 anti-bot
(SeLoger) qui empêchent une requête HTTP basique de trancher (ORA-134).

Vit dans scripts/ (pas backend/scripts/) et tourne sous scripts/.venv : c'est
là que vivent Selenium/undetected_chromedriver, volontairement absents des
dépendances backend pour ne pas alourdir son image de déploiement (voir
README, section "Annonces mortes : TTL par re-scraping + nettoyage ponctuel").

Tourne en `headless=True` (contrairement aux 6 scrapers, qui gardent une
fenêtre visible par défaut pour l'anti-détection) : ce script s'exécute dans
des environnements sans session d'affichage graphique disponible (CI,
sandbox), où `undetected_chromedriver` ne peut pas ouvrir de vraie fenêtre
(`SessionNotCreatedException: unable to discover open pages`).

Stratégie en deux passes :
  1. Re-teste chaque url encore en base via `check_url_status` (HTTP simple,
     rapide) — le statut peut avoir changé depuis le dernier run de
     prune_dead_annonces.py (ex: blocage anti-bot temporaire levé entretemps).
  2. Seules les urls restées ambiguës sont rouvertes dans un vrai navigateur,
     plus lent mais capable de passer l'anti-bot comme les 6 scrapers.

Toujours conservateur : si même le navigateur ne permet pas de trancher
(page plantée, timeout...), l'annonce est conservée.

Usage :
    python scripts/recheck_dead_annonces.py [--dry-run] [--limit N]
"""
import argparse
import os
import random
import sys
import time
from urllib.parse import urlparse

import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
backend_dir = os.path.join(repo_root, "backend")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services import annonces_store  # noqa: E402 (après le sys.path.insert nécessaire)
from scripts.prune_dead_annonces import (  # noqa: E402
    DEFAULT_DELAY_RANGE,
    check_url_status,
    looks_like_soft_404,
    _fetch_all_annonces,
)

from scraper_utils import (  # noqa: E402
    get_chrome_driver,
    get_scraper_logger,
    pick_proxy,
    pick_user_agent,
)

logger = get_scraper_logger("recheck_dead_annonces")

BROWSER_PAGE_LOAD_TIMEOUT = 20
BROWSER_DELAY_RANGE = (2, 4)


def check_url_status_browser(url, driver, page_load_timeout=BROWSER_PAGE_LOAD_TIMEOUT):
    """Vérifie une url via un vrai navigateur furtif. Renvoie True (confirmée
    morte), False (vivante), ou None si même le navigateur ne permet pas de
    trancher (à conserver par prudence).

    Deux signaux, dans cet ordre :
    - Redirection vers la page d'accueil (`/`) : plusieurs sites redirigent
      une annonce expirée vers leur accueil plutôt que d'afficher un message.
    - `looks_like_soft_404` appliqué au contenu rendu (même détection que
      `check_url_status`, réutilisée pour une seule source de vérité).
    """
    try:
        driver.set_page_load_timeout(page_load_timeout)
        driver.get(url)
        time.sleep(1.5)  # laisse le temps aux éventuelles redirections JS de s'exécuter

        final_path = urlparse(driver.current_url).path
        original_path = urlparse(url).path
        if final_path in ("", "/") and original_path not in ("", "/"):
            logger.info("Redirection vers la page d'accueil détectée pour %s", url)
            return True

        if looks_like_soft_404(driver.page_source):
            logger.info("Soft 404 détecté (navigateur) pour %s", url)
            return True

        return False
    except Exception as exc:
        logger.warning("Vérification navigateur ambiguë pour %s (%s) : conservée par prudence.", url, exc)
        return None


def recheck_ambiguous(
    db_path=None,
    delay_range=DEFAULT_DELAY_RANGE,
    browser_delay_range=BROWSER_DELAY_RANGE,
    dry_run=False,
    limit=None,
    checker=check_url_status,
    browser_checker=check_url_status_browser,
    driver_factory=None,
):
    """Re-teste chaque annonce de `db_path` en HTTP, puis escalade au
    navigateur celles restées ambiguës. Supprime celles confirmées mortes
    (sauf `dry_run=True`).

    Renvoie {"rechecked", "escalated_to_browser", "dead", "deleted", "still_ambiguous"}.
    """
    db_path = db_path or annonces_store.DEFAULT_DB_PATH
    annonces = _fetch_all_annonces(db_path)
    driver_factory = driver_factory or (
        lambda: get_chrome_driver(user_agent=pick_user_agent(), proxy=pick_proxy(), headless=True)
    )

    session = requests.Session()
    ambiguous = []
    try:
        for annonce in annonces:
            status = checker(annonce["url"], session)
            if status is None:
                ambiguous.append(annonce)
            time.sleep(random.uniform(*delay_range))
    finally:
        session.close()

    logger.info("%s annonce(s) ambiguë(s) après la passe HTTP, à re-vérifier via navigateur.", len(ambiguous))
    if limit is not None:
        ambiguous = ambiguous[:limit]

    dead = deleted = still_ambiguous = 0
    if ambiguous:
        driver = driver_factory()
        try:
            for annonce in ambiguous:
                status = browser_checker(annonce["url"], driver)

                if status is True:
                    dead += 1
                    logger.info("Confirmée morte (navigateur) : %s — %s", annonce["url"], annonce.get("titre"))
                    if not dry_run:
                        if annonces_store.delete_annonce(annonce_id=annonce["id"], db_path=db_path):
                            deleted += 1
                elif status is None:
                    still_ambiguous += 1

                time.sleep(random.uniform(*browser_delay_range))
        finally:
            driver.quit()

    logger.info(
        "Terminé : %s re-vérifiées, %s mortes (%s supprimées%s), %s toujours ambiguës.",
        len(ambiguous), dead, deleted, " — dry-run" if dry_run else "", still_ambiguous,
    )
    return {
        "rechecked": len(ambiguous),
        "dead": dead,
        "deleted": deleted,
        "still_ambiguous": still_ambiguous,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Vérifie et logue sans rien supprimer.")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limite le nombre d'annonces ambiguës re-vérifiées via navigateur (debug/tests).",
    )
    args = parser.parse_args()
    recheck_ambiguous(dry_run=args.dry_run, limit=args.limit)
