from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import sys

from scraper_utils import (
    atomic_csv_writer,
    find_first_image_url,
    get_chrome_driver,
    get_scraper_logger,
    load_existing_rows,
    load_site_config,
    pick_proxy,
    pick_user_agent,
    retry_with_backoff,
    should_continue_pagination,
    today_iso,
)

site_config = load_site_config("pap")
logger = get_scraper_logger("pap")

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', f"annonces_{site_config['ville_slug']}_pap.csv")
BASE_URL = site_config['base_url']

CARD_SELECTORS = [
    "div[class*='search-list-item']",
    "article[class*='search-list-item']",
    "div[class*='listing-item']",
    "[class*='annonce-item']",
]
LIEU_SELECTORS = [
    ".h1", "h2.h1", "[class*='location']", "[class*='lieu']", "h2", "h3",
]
PRIX_SELECTORS = [
    ".item-price", "[class*='item-price']", "[class*='price']", "[class*='prix']",
]
DETAILS_SELECTORS = [
    ".item-tags", "[class*='item-tags']", "[class*='tags']", "[class*='detail']",
]

def find_text(element, selectors, default=""):
    for sel in selectors:
        try:
            return element.find_element(By.CSS_SELECTOR, sel).text.strip()
        except Exception:
            continue
    return default

def scroll_to_bottom(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(2, 4))
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        logger.info("Suite chargée...")

@retry_with_backoff(max_retries=3, backoff_seconds=2)
def load_page(driver, url):
    driver.get(url)

if __name__ == '__main__':
    logger.info("Lancement du mode Furtif pour PAP (%s)...", site_config['ville_nom'])

    driver = get_chrome_driver(ignore_certificate_errors=False, user_agent=pick_user_agent(), proxy=pick_proxy())
    wait = WebDriverWait(driver, 60)

    CSV_HEADER = ['Lieu', 'Prix', 'Détails', 'Lien', 'Image', 'DerniereVue']
    LIEN_INDEX = CSV_HEADER.index('Lien')
    DERNIERE_VUE_INDEX = CSV_HEADER.index('DerniereVue')

    existing_rows, liens_vus = load_existing_rows(OUTPUT_PATH, CSV_HEADER)
    rows_by_lien = {row[LIEN_INDEX]: row for row in existing_rows}
    today = today_iso()

    erreurs = 0
    total_nouveaux_run = 0
    total_cards_vues = 0
    consecutive_empty_pages = 0

    def checkpoint():
        """Persiste l'état courant de `rows_by_lien` (écriture atomique complète,
        pas un append). Appelée après chaque page plutôt qu'une seule fois à la
        fin du run : régression réelle constatée sur scraper_seloger.py (242
        pages perdues suite à un hoquet Selenium transitoire tardif, alors que
        atomic_csv_writer n'était appelé qu'une fois à la toute fin du run)."""
        with atomic_csv_writer(OUTPUT_PATH, CSV_HEADER) as writer:
            for row in rows_by_lien.values():
                writer.writerow(row)

    page_num = 1
    continuer = True

    while continuer:
        url = BASE_URL.format(page_num)
        logger.info("Analyse de la page %s", page_num)
        try:
            load_page(driver, url)
        except Exception as exc:
            logger.error("Impossible de charger la page %s après plusieurs tentatives : %s", page_num, exc)
            break

        if page_num == 1:
            logger.info("Attente automatique du chargement des annonces...")
            card_found = False
            for sel in CARD_SELECTORS:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                    logger.info("Annonces détectées (%s)", sel)
                    card_found = True
                    break
                except Exception:
                    continue
            if not card_found:
                logger.error("Impossible de détecter les annonces. Structure inconnue.")
                break

        logger.info("Défilement automatique...")
        scroll_to_bottom(driver)
        logger.info("Page entièrement chargée.")
        time.sleep(2)

        annonces = []
        for sel in CARD_SELECTORS:
            annonces = driver.find_elements(By.CSS_SELECTOR, sel)
            if annonces:
                break

        if not annonces:
            logger.warning("Aucune annonce trouvée sur la page %s.", page_num)
            break

        total_cards_vues += len(annonces)
        logger.info("%s annonces détectées.", len(annonces))
        compteur = 0

        for annonce in annonces:
            try:
                lieu = find_text(annonce, LIEU_SELECTORS, "Lieu Inconnu")
                prix = find_text(annonce, PRIX_SELECTORS, "N/C")
                details = find_text(annonce, DETAILS_SELECTORS).replace('\n', ' - ')

                try:
                    lien_elem = annonce.find_element(By.TAG_NAME, "a")
                    lien = lien_elem.get_attribute("href") or ""
                except Exception:
                    lien = ""

                if lieu == "Lieu Inconnu" and prix == "N/C":
                    continue

                if lien in rows_by_lien:
                    # Déjà connue : pas de re-scraping de ses détails, on note juste
                    # qu'elle est toujours présente sur le site (ORA-134, TTL).
                    rows_by_lien[lien][DERNIERE_VUE_INDEX] = today
                    continue

                image = find_first_image_url(annonce, base_url=driver.current_url)

                logger.info("Annonce trouvée : %s | %s -- %s", lieu, details, prix)
                rows_by_lien[lien] = [lieu, prix, details, lien, image, today]
                liens_vus.add(lien)
                compteur += 1

            except Exception as exc:
                erreurs += 1
                logger.warning("Erreur lors du parsing d'une annonce : %s", exc)
                continue

        logger.info("Page %s terminée : %s annonces ajoutées.", page_num, compteur)
        total_nouveaux_run += compteur
        checkpoint()

        continuer, consecutive_empty_pages = should_continue_pagination(compteur, consecutive_empty_pages)
        if not continuer:
            logger.info("Fin des nouvelles annonces (%s page(s) consécutive(s) sans nouveauté).", consecutive_empty_pages)
        else:
            time.sleep(random.uniform(2, 4))
        page_num += 1

    driver.quit()

    if total_cards_vues == 0:
        logger.error("0 annonce trouvée pour PAP. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(rows_by_lien), total_nouveaux_run, erreurs, OUTPUT_PATH
    )
