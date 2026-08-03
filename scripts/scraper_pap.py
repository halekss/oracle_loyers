import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import sys

from csv_atomic_writer import atomic_csv_writer
from scraper_utils import get_scraper_logger

logger = get_scraper_logger("pap")

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', 'annonces_lyon_pap.csv')
BASE_URL = "https://www.pap.fr/annonce/locations-appartement-lyon-69-g43590-a-partir-du-2-pieces?page={}"

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

if __name__ == '__main__':
    logger.info("Lancement du mode Furtif pour PAP...")

    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 60)

    liens_vus = set()
    erreurs = 0

    with atomic_csv_writer(OUTPUT_PATH, ['Lieu', 'Prix', 'Détails', 'Lien']) as writer:
        page_num = 1
        continuer = True

        while continuer:
            url = BASE_URL.format(page_num)
            logger.info("Analyse de la page %s", page_num)
            driver.get(url)

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
                    if lien in liens_vus:
                        continue

                    logger.info("Annonce trouvée : %s | %s -- %s", lieu, details, prix)
                    writer.writerow([lieu, prix, details, lien])
                    liens_vus.add(lien)
                    compteur += 1

                except Exception as exc:
                    erreurs += 1
                    logger.warning("Erreur lors du parsing d'une annonce : %s", exc)
                    continue

            logger.info("Page %s terminée : %s annonces ajoutées.", page_num, compteur)

            if compteur == 0:
                logger.info("Plus de nouvelles annonces.")
                continuer = False
            else:
                page_num += 1
                time.sleep(random.uniform(2, 4))

    driver.quit()

    if len(liens_vus) == 0:
        logger.error("0 annonce trouvée pour PAP. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(liens_vus), len(liens_vus), erreurs, OUTPUT_PATH
    )
