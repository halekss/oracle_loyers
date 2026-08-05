"""
Utilitaires partagés entre les 6 scrapers (Century21, Orpi, PAP, ParuVendu,
SeLoger, Vizzit) : factory du driver Chrome furtif, helper de sélecteurs CSS
en cascade, écriture CSV atomique et décorateur retry/backoff.

Objectif : centraliser la logique dupliquée dans chaque scraper_*.py pour
qu'une correction de robustesse n'ait plus besoin d'être répétée 6 fois.
"""

import csv
import json
import logging
import os
import random
import re
import subprocess
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
    "load_site_config",
    "pick_user_agent",
    "pick_proxy",
    "load_existing_rows",
]

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraping_config.json")


def load_site_config(site_key, config_path=CONFIG_PATH):
    """Charge la config de la ville active (URL de recherche, paramètre de pagination)
    pour un portail donné, afin que changer de ville ne nécessite pas de modifier le
    code Python des scrapers — seulement `scraping_config.json`.

    Renvoie un dict {ville_nom, ville_slug, base_url, page_query_param}.
    `page_query_param` est None quand la pagination est déjà intégrée dans `base_url`
    (ex : Century21, Orpi, PAP, Vizzit utilisent un `{}` positionnel dans l'URL).
    """
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    ville_active = config["ville_active"]
    ville_config = config["villes"][ville_active]
    site_config = ville_config[site_key]

    return {
        "ville_nom": ville_config["nom"],
        "ville_slug": ville_config["slug"],
        "base_url": site_config["base_url"],
        "page_query_param": site_config.get("page_query_param"),
    }


def pick_user_agent(config_path=CONFIG_PATH):
    """Choisit un User-Agent réaliste au hasard dans le pool configuré (rotation, ORA-18).

    Renvoie None si le pool est vide/absent : le navigateur (undetected_chromedriver)
    garde alors son comportement par défaut, inchangé.
    """
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    user_agents = config.get("user_agents") or []
    return random.choice(user_agents) if user_agents else None


def pick_proxy(config_path=CONFIG_PATH):
    """Choisit un proxy au hasard dans le pool configuré (ORA-18), désactivé par défaut.

    Renvoie None si le pool est vide/absent : aucun proxy n'est utilisé, comportement
    par défaut inchangé. Le pool attend des URLs de proxy complètes
    (ex : "http://user:pass@host:port").
    """
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    proxies = config.get("proxies") or []
    return random.choice(proxies) if proxies else None


def load_existing_rows(path):
    """Charge les lignes déjà connues (écrites lors d'un run précédent) et l'ensemble de
    leurs liens, pour dédupliquer d'un run à l'autre et pas seulement au sein d'un même run.

    Stratégie retenue : append. Une annonce déjà vue lors d'un run précédent est ignorée
    (ni ré-écrite, ni mise à jour) ; sa ligne existante est conservée telle quelle et
    réécrite avec le reste. Le lien (dernière colonne de chaque ligne, par convention sur
    les 6 scrapers) sert de clé de déduplication.

    Renvoie ([], set()) si `path` n'existe pas encore (premier run).
    """
    if not os.path.exists(path):
        return [], set()

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # en-tête
        rows = [row for row in reader if row]

    liens_vus = {row[-1] for row in rows}
    return rows, liens_vus


def _detect_local_chrome_major_version():
    """Détecte la version majeure du Chrome installé localement en interrogeant
    le binaire directement, pour la transmettre à undetected_chromedriver.

    Nécessaire car uc peut télécharger le ChromeDriver de la dernière version
    stable connue, en avance de quelques jours sur l'auto-update réel du
    navigateur local (ex : ChromeDriver 151 alors que Chrome reste en 150) —
    ce qui casse la négociation de session Selenium. Renvoie None si la
    détection échoue : uc retombe alors sur son comportement par défaut.
    """
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
    ]
    for candidate in candidates:
        try:
            output = subprocess.check_output(
                [candidate, "--version"], stderr=subprocess.DEVNULL, timeout=5
            ).decode()
        except (OSError, subprocess.SubprocessError):
            continue
        match = re.search(r"(\d+)\.", output)
        if match:
            return int(match.group(1))
    return None


def get_chrome_driver(
    ignore_certificate_errors=True,
    block_images=False,
    user_agent=None,
    proxy=None,
    page_load_timeout=30,
):
    """
    Factory undetected_chromedriver commune aux scrapers.
    `block_images` désactive le chargement des images (utile pour accélérer
    certains sites, cf. scraper_vizzit.py).
    `user_agent`/`proxy` sont optionnels (None par défaut = comportement inchangé) :
    voir pick_user_agent()/pick_proxy() pour les tirer du pool configuré (ORA-18).
    `page_load_timeout` (secondes) borne chaque driver.get() : par défaut Selenium
    peut attendre indéfiniment si une page ne termine jamais son chargement.
    Combiné à retry_with_backoff (déjà en place autour de driver.get() dans les
    6 scrapers), un dépassement lève une TimeoutException qui est retentée puis
    loggée en ERROR sans planter le run (ORA-25).
    """
    options = uc.ChromeOptions()
    if ignore_certificate_errors:
        options.add_argument("--ignore-certificate-errors")
    if block_images:
        options.add_experimental_option(
            "prefs", {"profile.managed_default_content_settings.images": 2}
        )
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")
    driver = uc.Chrome(options=options, version_main=_detect_local_chrome_major_version())
    driver.set_page_load_timeout(page_load_timeout)
    return driver


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
