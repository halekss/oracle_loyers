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
from urllib.parse import urljoin, urlsplit, urlunsplit

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

from csv_atomic_writer import atomic_csv_writer

__all__ = [
    "clean_description",
    "enrich_descriptions",
    "load_details_config",
    "selenium_description_fetcher",
    "get_chrome_driver",
    "find_first",
    "find_first_image_url",
    "archive_stale_rows",
    "atomic_csv_writer",
    "retry_with_backoff",
    "get_scraper_logger",
    "load_site_config",
    "pick_user_agent",
    "pick_proxy",
    "blank_short_descriptions",
    "load_existing_rows",
    "today_iso",
    "should_continue_pagination",
    "GRACE_PAGES_SANS_NOUVEAUTE",
    "canonical_url",
]

# Nombre de pages consécutives sans nouvelle annonce à parcourir avant d'arrêter
# la pagination (ORA-134). Sans cette marge, la pagination s'arrêterait dès la
# 1ère page entièrement déjà-connue et les annonces plus profondément paginées
# ne seraient jamais revues — un TTL basé sur "dernière fois vue" les
# expirerait alors à tort, qu'elles soient encore actives ou non sur le site.
GRACE_PAGES_SANS_NOUVEAUTE = 2

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


def canonical_url(url):
    """Retire la query string et le fragment d'une URL d'annonce.

    Régression réelle constatée sur SeLoger (Lille) : le `href` de chaque
    carte annonce embarque le contexte de recherche courant (page, tri...),
    qui varie selon la page depuis laquelle l'annonce est atteinte -- une
    même annonce revue depuis une page différente produit donc un `href`
    différent. Utilisé tel quel comme clé de dédoublonnage (`rows_by_lien`),
    ça empêchait de jamais reconnaître une annonce déjà connue : elle était
    re-scrapée et réécrite en CSV à chaque nouvelle page où le site la
    présentait, jusqu'à des dizaines de fois (constaté : jusqu'à 144x pour
    une même annonce), et `should_continue_pagination` ne voyait alors
    jamais de page "sans nouveauté", ce qui empêchait aussi la pagination de
    s'arrêter d'elle-même une fois le vrai inventaire épuisé."""
    parts = urlsplit(str(url))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def should_continue_pagination(compteur_nouveaux, consecutive_empty_pages):
    """Décide si la pagination d'un scraper doit continuer après une page où
    `compteur_nouveaux` annonces jamais vues *pendant ce run* ont été trouvées
    (nouvelles ou déjà connues : ce qui compte est qu'elles n'aient pas déjà
    été rencontrées plus haut dans la liste).

    Le run parcourt donc toute la liste. Seule une page sans aucune annonce
    inédite (fin des résultats, ou dernière page répétée par le site) compte
    comme vide ; `GRACE_PAGES_SANS_NOUVEAUTE` pages vides de suite l'arrêtent.

    Renvoie `(continuer, nouveau_consecutive_empty_pages)`.
    """
    if compteur_nouveaux > 0:
        return True, 0

    consecutive_empty_pages += 1
    return consecutive_empty_pages < GRACE_PAGES_SANS_NOUVEAUTE, consecutive_empty_pages


def archive_stale_rows(rows_by_lien, vus_ce_run, output_path, header, logger, run_complet):
    """Déplace de `rows_by_lien` vers `<output>_archive.csv` les annonces non
    revues pendant ce run (nouvelles + doublons revus restent dans le CSV
    principal). L'archive est cumulative : elle garde le dernier état (prix,
    `DerniereVue`) de chaque annonce disparue, pour suivre l'évolution des prix.

    Ne fait rien si le run n'est pas allé au bout de la liste (`run_complet`
    faux : page bloquée, erreur réseau...) ou n'a rien vu : sinon un run bloqué
    archiverait tout le stock encore en ligne. Renvoie le nombre archivé."""
    if not run_complet or not vus_ce_run:
        logger.warning("Run incomplet ou sans annonce vue : aucune annonce archivée.")
        return 0
    stale = [lien for lien in rows_by_lien if lien not in vus_ce_run]
    if not stale:
        return 0

    root, ext = os.path.splitext(output_path)
    archive_path = f"{root}_archive{ext}"
    archived_rows, _ = load_existing_rows(archive_path, header)
    with atomic_csv_writer(archive_path, header) as writer:
        for row in archived_rows:
            writer.writerow(row)
        for lien in stale:
            writer.writerow(rows_by_lien[lien])
    for lien in stale:
        del rows_by_lien[lien]
    logger.info("%s annonce(s) non revue(s) déplacée(s) vers %s", len(stale), archive_path)
    return len(stale)


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
    headless=False,
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
    `headless` (False par défaut, comportement inchangé pour les 6 scrapers en
    production : une fenêtre visible est historiquement plus difficile à
    distinguer d'un vrai navigateur pour l'anti-bot) — à passer explicitement
    à True pour un usage ponctuel dans un environnement sans session
    d'affichage graphique disponible (ORA-134, `recheck_dead_annonces.py`).
    """
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
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


# --- ORA-161 : description libre depuis la page détail de l'annonce ---------

# En dessous, le texte capturé est un libellé d'interface, pas une description.
MIN_DESCRIPTION_CHARS = 20
# Nombre d'échecs consécutifs (page détail inaccessible) après lequel on arrête
# d'enrichir : signe probable de blocage, inutile d'insister sur le site.
MAX_CONSECUTIVE_DETAIL_ERRORS = 3
DEFAULT_DETAILS_CONFIG = {"max_per_run": 100, "delay_min_s": 2.0, "delay_max_s": 4.0}


def clean_description(text):
    """Texte de description normalisé : espaces/retours à la ligne repliés en
    un seul espace, libellé de section « Description » en tête retiré. Chaîne
    vide si le résultat est trop court pour être une vraie description."""
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"^description\b[\s:.-]*", "", text, flags=re.IGNORECASE)
    return text if len(text) >= MIN_DESCRIPTION_CHARS else ""


def blank_short_descriptions(rows, desc_index):
    """Vide les descriptions trop courtes pour en être une (bruit type « France
    Lille » capté par un ancien sélecteur) afin que `enrich_descriptions` les
    retente. Renvoie le nombre de lignes vidées."""
    n = 0
    for row in rows:
        if row[desc_index] and not clean_description(row[desc_index]):
            row[desc_index] = ""
            n += 1
    return n


def load_details_config(config_path=None):
    """Réglages de la visite des pages détail (bloc `details` de
    scraping_config.json) : `max_per_run` (plafond de pages visitées par run,
    0 = désactivé), `delay_min_s`/`delay_max_s` (pause entre deux pages).
    Valeurs par défaut prudentes si le bloc est absent."""
    config = dict(DEFAULT_DETAILS_CONFIG)
    try:
        with open(config_path or CONFIG_PATH, encoding="utf-8") as f:
            config.update(json.load(f).get("details") or {})
    except (OSError, ValueError):
        pass
    return config


def enrich_descriptions(rows_by_lien, lien_index, desc_index, fetch_description, logger,
                        max_per_run=None, delay_range=None, sleep=time.sleep):
    """Visite la page détail des annonces dont la description est vide et la
    complète dans `rows_by_lien` (lignes mutables, comme pour `DerniereVue`).

    Volume maîtrisé (risque de blocage, cf. ORA-161) : au plus `max_per_run`
    pages par run, les annonces les plus récentes d'abord, une pause aléatoire
    entre deux pages, arrêt après `MAX_CONSECUTIVE_DETAIL_ERRORS` échecs de
    suite. `fetch_description(url)` renvoie le texte ("" si la page n'en a pas)
    et lève une exception si la page est inaccessible.

    # ponytail: une annonce sans description sur sa page est re-tentée à
    # chaque run (pas de marqueur "déjà visitée") ; le plafond borne le coût,
    # un marqueur persistant s'ajoutera si ces re-visites pèsent.

    Renvoie les statistiques du run (volume, trouvées, vides, erreurs)."""
    config = load_details_config()
    if max_per_run is None:
        max_per_run = config["max_per_run"]
    if delay_range is None:
        delay_range = (config["delay_min_s"], config["delay_max_s"])

    todo = [row for row in reversed(list(rows_by_lien.values())) if not row[desc_index]]
    stats = {"candidates": len(todo), "visited": 0, "found": 0, "empty": 0, "errors": 0, "aborted": False}
    consecutive_errors = 0

    for row in todo[:max(0, max_per_run)]:
        stats["visited"] += 1
        try:
            text = clean_description(fetch_description(row[lien_index]))
            consecutive_errors = 0
        except Exception as exc:
            stats["errors"] += 1
            consecutive_errors += 1
            logger.warning("Page détail inaccessible (%s) : %s", row[lien_index], exc)
            if consecutive_errors >= MAX_CONSECUTIVE_DETAIL_ERRORS:
                stats["aborted"] = True
                logger.error("%s échecs consécutifs sur les pages détail : arrêt (blocage probable).", consecutive_errors)
                break
        else:
            if text:
                row[desc_index] = text
                stats["found"] += 1
            else:
                stats["empty"] += 1
        sleep(random.uniform(*delay_range))

    logger.info(
        "Descriptions (pages détail) : %s à compléter, %s visitées, %s trouvées, %s vides, %s erreurs%s.",
        stats["candidates"], stats["visited"], stats["found"], stats["empty"], stats["errors"],
        " (arrêt anticipé)" if stats["aborted"] else "",
    )
    return stats


def selenium_description_fetcher(driver, selectors, timeout=10):
    """`fetch_description(url)` pour `enrich_descriptions` avec un driver
    Selenium : charge la page, attend qu'un des sélecteurs (cascade, du plus
    au moins précis) apparaisse et renvoie le premier texte non vide. Page
    sans description (timeout sur l'attente) = "" et non une erreur ; un
    échec de chargement de la page lève."""
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait

    def fetch(url):
        driver.get(url)
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: any(d.find_elements(By.CSS_SELECTOR, sel) for sel in selectors)
            )
        except TimeoutException:
            return ""
        for sel in selectors:
            for element in driver.find_elements(By.CSS_SELECTOR, sel):
                text = clean_description(element.text)
                if text:
                    return text
        return ""

    return fetch
