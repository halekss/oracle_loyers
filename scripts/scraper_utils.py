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
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urljoin

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

from csv_atomic_writer import atomic_csv_writer

__all__ = [
    "get_chrome_driver",
    "find_first",
    "find_first_image_url",
    "atomic_csv_writer",
    "retry_with_backoff",
    "get_scraper_logger",
    "load_site_config",
    "pick_user_agent",
    "pick_proxy",
    "load_existing_rows",
    "today_iso",
    "should_continue_pagination",
    "GRACE_PAGES_SANS_NOUVEAUTE",
]

# Nombre de pages consécutives sans nouvelle annonce à parcourir avant d'arrêter
# la pagination (ORA-134). Sans cette marge, la pagination s'arrêterait dès la
# 1ère page entièrement déjà-connue et les annonces plus profondément paginées
# ne seraient jamais revues — un TTL basé sur "dernière fois vue" les
# expirerait alors à tort, qu'elles soient encore actives ou non sur le site.
GRACE_PAGES_SANS_NOUVEAUTE = 3

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


def load_existing_rows(path, header):
    """Charge les lignes déjà connues (écrites lors d'un run précédent) et l'ensemble de
    leurs liens, pour dédupliquer d'un run à l'autre et pas seulement au sein d'un même run.

    Stratégie retenue : append/update en place. Une annonce déjà vue lors d'un run
    précédent n'est pas re-scrapée en détail ; sa ligne existante est conservée et
    réécrite avec le reste — l'appelant peut cependant en muter des champs
    (typiquement la colonne 'DerniereVue', ORA-134) si l'annonce est revue au cours
    de ce run, puisque les lignes renvoyées sont les objets `list` mutables utilisés
    ensuite pour l'écriture. `header` (liste de colonnes du CSV_HEADER courant) sert
    à localiser 'Lien' par nom plutôt que par position fixe, pour rester robuste à
    l'ajout de colonnes en fin de header (ex: 'Image', puis 'DerniereVue').

    Les lignes plus courtes que `header` (écrites avant l'ajout d'une colonne) sont
    complétées avec des chaînes vides à la fin, pour rester alignées avec le header
    courant et éviter un CSV en dents de scie que `pandas.read_csv` lirait mal.

    Renvoie ([], set()) si `path` n'existe pas encore (premier run).
    """
    if not os.path.exists(path):
        return [], set()

    lien_index = header.index("Lien")

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # en-tête
        rows = [row for row in reader if row]

    rows = [row + [""] * (len(header) - len(row)) for row in rows]
    liens_vus = {row[lien_index] for row in rows}
    return rows, liens_vus


def today_iso():
    """Date du jour (UTC) au format ISO — utilisée pour horodater la colonne
    'DerniereVue' des scrapers (ORA-134 : TTL par re-scraping)."""
    return datetime.now(timezone.utc).date().isoformat()


def should_continue_pagination(compteur_nouveaux, consecutive_empty_pages):
    """Décide si la pagination d'un scraper doit continuer après une page où
    `compteur_nouveaux` nouvelles annonces ont été trouvées (ORA-134).

    Une page sans nouvelle annonce ne stoppe plus immédiatement la pagination :
    elle bénéficie de `GRACE_PAGES_SANS_NOUVEAUTE` pages de marge, pour laisser
    une chance de re-confirmer périodiquement la présence des annonces déjà
    connues plus profondément paginées (sans quoi elles ne seraient jamais
    revues, et un TTL basé sur 'dernière fois vue' les expirerait à tort).

    Renvoie `(continuer, nouveau_consecutive_empty_pages)`.
    """
    if compteur_nouveaux > 0:
        return True, 0

    consecutive_empty_pages += 1
    return consecutive_empty_pages < GRACE_PAGES_SANS_NOUVEAUTE, consecutive_empty_pages


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


IMAGE_ATTRIBUTES = ("data-src", "data-lazy-src", "data-lazy", "srcset", "src")


def find_first_image_url(element, selectors=("img",), attributes=IMAGE_ATTRIBUTES, base_url=None):
    """
    Cherche la première balise <img> correspondant à l'un des `selectors` dans
    `element`, et renvoie une URL d'image exploitable.

    La plupart des portails immobiliers font du lazy-loading (l'attribut `src`
    réel n'est peuplé qu'au scroll, remplacé entre-temps par un placeholder) :
    on essaie donc les attributs `data-src`/`data-lazy-src`/`data-lazy` avant
    `src`, et on parse `srcset` (garde la première URL, avant le descripteur
    de taille "500w"/"2x") si aucun des attributs directs n'est présent.

    `base_url` (ex: `driver.current_url`) résout les chemins relatifs/racine
    (ex: "/imagesBien/...") en URL absolue via `urljoin` : sans ça, une image
    valide mais relative serait rejetée plus tard par `sanitize_image_url`
    (generate_map.py), qui n'accepte que du http(s) absolu.

    Renvoie "" si aucune image exploitable n'est trouvée (annonce sans photo,
    ou sélecteur qui ne correspond plus à la structure du site).
    """
    for selector in selectors:
        try:
            img = element.find_element(By.CSS_SELECTOR, selector)
        except Exception:
            continue

        for attribute in attributes:
            value = (img.get_attribute(attribute) or "").strip()
            if not value:
                continue
            if attribute == "srcset":
                value = value.split(",")[0].strip().split(" ")[0].strip()
            if value:
                return urljoin(base_url, value) if base_url else value

    return ""


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
