"""
Utilitaires partagés entre les 6 scrapers (Century21, Orpi, PAP, ParuVendu,
SeLoger, Vizzit) : factory du driver Chrome furtif, helper de sélecteurs CSS
en cascade, écriture CSV atomique et décorateur retry/backoff.

Objectif : centraliser la logique dupliquée dans chaque scraper_*.py pour
qu'une correction de robustesse n'ait plus besoin d'être répétée 6 fois.
"""

import logging
import os
import time
from functools import wraps

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

from csv_atomic_writer import atomic_csv_writer

__all__ = [
    "get_chrome_driver",
    "find_first",
    "atomic_csv_writer",
    "retry_with_backoff",
    "get_scraper_logger",
]

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def get_chrome_driver(ignore_certificate_errors=True, block_images=False):
    """
    Factory undetected_chromedriver commune aux scrapers.
    `block_images` désactive le chargement des images (utile pour accélérer
    certains sites, cf. scraper_vizzit.py).
    """
    options = uc.ChromeOptions()
    if ignore_certificate_errors:
        options.add_argument("--ignore-certificate-errors")
    if block_images:
        options.add_experimental_option(
            "prefs", {"profile.managed_default_content_settings.images": 2}
        )
    return uc.Chrome(options=options)


def find_first(element, selectors, default=""):
    """
    Essaie chaque sélecteur CSS de `selectors` dans l'ordre sur `element` et
    renvoie le texte du premier trouvé (cascade de fallback), sinon `default`.
    """
    for selector in selectors:
        try:
            return element.find_element(By.CSS_SELECTOR, selector).text.strip()
        except Exception:
            continue
    return default


def get_scraper_logger(name):
    """
    Logger structuré commun aux scrapers : format et niveaux cohérents entre
    les 6 sites. Sortie console (INFO+) et persistance de chaque run par
    append dans scripts/logs/<name>.log, pour garder un historique des taux
    d'échec/réussite d'un run à l'autre.
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(f"scraper.{name}")

    if logger.handlers:
        return logger  # déjà configuré (ex : appels multiples dans le même run)

    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(os.path.join(LOG_DIR, f"{name}.log"), encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def retry_with_backoff(max_retries=3, backoff_seconds=2, exceptions=(Exception,)):
    """
    Décorateur retry/backoff générique pour les opérations de scraping
    instables (ex : navigation vers une page). Relève la dernière exception
    si toutes les tentatives échouent.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_error = exc
                    if attempt < max_retries:
                        time.sleep(backoff_seconds * attempt)
            raise last_error
        return wrapper
    return decorator
