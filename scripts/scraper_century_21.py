from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import sys

from scraper_utils import get_chrome_driver, find_first, atomic_csv_writer, retry_with_backoff, get_scraper_logger

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', 'annonces_lyon_century21.csv')
base_url = "https://www.century21.fr/annonces/f/location-maison-appartement/v-lyon/page-{}/"

CARD_SELECTOR = "div[class*='c-the-property-thumbnail-with-content']"
TITRE_SELECTORS = [
    "[class*='c-text-theme-heading-3']",
    "[class*='heading-3']",
    "h3",
    "h2",
]
PRIX_SELECTORS = [
    "[class*='c-text-theme-heading-1']",
    "[class*='heading-1']",
    "[class*='price']",
    "[class*='prix']",
]
INFOS_SELECTORS = [
    "[class*='c-text-theme-heading-4']",
    "[class*='heading-4']",
    "[class*='surface']",
    "[class*='detail']",
]

logger = get_scraper_logger("century21")

@retry_with_backoff(max_retries=3, backoff_seconds=2)
def load_page(driver, url):
    driver.get(url)

if __name__ == '__main__':
    logger.info("Lancement du mode Furtif Automatique pour Century 21...")

    driver = get_chrome_driver()

    liens_vus = set()
    erreurs = 0

    with atomic_csv_writer(OUTPUT_PATH, ['Titre', 'Prix', 'Lieu_Surface', 'Lien']) as writer:
        page_num = 1
        continuer = True

        while continuer:
            url = base_url.format(page_num)
            logger.info("Analyse de la page %s", page_num)
            load_page(driver, url)

            if page_num == 1:
                logger.info("En attente de la validation des cookies...")
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, CARD_SELECTOR))
                    )
                    logger.info("Validation détectée, démarrage du scraping.")
                except Exception:
                    logger.error("Temps d'attente dépassé lors de la validation des cookies.")
                    break
            else:
                time.sleep(random.uniform(2, 4))

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            annonces = driver.find_elements(By.CSS_SELECTOR, CARD_SELECTOR)
            if not annonces:
                logger.warning("Aucun bloc d'annonce trouvé sur la page %s. Fin de la recherche.", page_num)
                break

            compteur_nouveaux = 0
            for annonce in annonces:
                try:
                    lien_elem = annonce.find_element(By.TAG_NAME, "a")
                    lien = lien_elem.get_attribute("href")
                    if not lien or lien in liens_vus:
                        continue

                    titre = find_first(annonce, TITRE_SELECTORS)
                    prix = find_first(annonce, PRIX_SELECTORS).replace('\n', ' ')
                    infos = find_first(annonce, INFOS_SELECTORS).replace('\n', ' ')

                    if not prix:
                        continue

                    writer.writerow([titre, prix, infos, lien])
                    liens_vus.add(lien)
                    compteur_nouveaux += 1
                    logger.info("Annonce trouvée : %s - %s", titre, prix)
                except Exception as exc:
                    erreurs += 1
                    logger.warning("Erreur lors du parsing d'une annonce : %s", exc)
                    continue

            logger.info("Page %s terminée : %s annonces ajoutées.", page_num, compteur_nouveaux)

            if compteur_nouveaux == 0:
                logger.info("Fin des nouvelles annonces.")
                continuer = False
            else:
                page_num += 1

    driver.quit()

    if len(liens_vus) == 0:
        logger.error("0 annonce trouvée pour Century 21. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(liens_vus), len(liens_vus), erreurs, OUTPUT_PATH
    )
