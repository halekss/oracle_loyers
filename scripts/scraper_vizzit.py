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
)

site_config = load_site_config("vizzit")
logger = get_scraper_logger("vizzit")

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', f"annonces_{site_config['ville_slug']}_vizzit.csv")
SEARCH_URL = site_config['base_url']

CARD_SELECTORS = [
    # Refonte observée le 2026-08-03 (canari ORA-21) : nouvelle classe de carte.
    "div.announce-card",
    "div.item__content-area",
    "div[class*='item__content']",
    "article[class*='item']",
    "div[class*='property-card']",
]
LIEN_SELECTORS = ["a.item__link", "a[class*='item__link']", "a[class*='property-link']", "a"]
PRIX_SELECTORS = ["strong.info-price", "div.display", "div[class*='display']", "[class*='price']", "[class*='prix']"]
LIEU_SELECTORS = [
    "div.announce-localisation",
    "p.item__location",
    "p[class*='location']",
    "[class*='location']",
    "[class*='lieu']",
]
DETAIL_SELECTORS = ["span.detail__item", "span[class*='detail']", "[class*='feature']"]
DESC_SELECTORS = ["p.description__text", "p[class*='description']", "div[class*='description']", "[class*='desc']"]
IMAGE_SELECTORS = [
    "img[class*='gallery']",
    "img[class*='carousel']",
    "picture img",
    "img[class*='photo']",
    "img",
]

def find_text(element, selectors, default=""):
    for sel in selectors:
        try:
            return element.find_element(By.CSS_SELECTOR, sel).text.strip()
        except Exception:
            continue
    return default

def find_attr(element, selectors, attr):
    for sel in selectors:
        try:
            el = element.find_element(By.CSS_SELECTOR, sel)
            val = el.get_attribute(attr)
            if val:
                return val
        except Exception:
            continue
    return ""

@retry_with_backoff(max_retries=3, backoff_seconds=2)
def load_page(driver, url):
    driver.get(url)

if __name__ == '__main__':
    logger.info("Lancement du scraper Vizzit Automatique (%s)...", site_config['ville_nom'])

    driver = get_chrome_driver(block_images=True, user_agent=pick_user_agent(), proxy=pick_proxy())
    wait = WebDriverWait(driver, 15)
    erreurs = 0
    total_nouveaux_run = 0
    total_cards_vues = 0

    CSV_HEADER = ['Lieu', 'Prix', 'Details', 'Description', 'Lien', 'Image']
    existing_rows, liens_vus = load_existing_rows(OUTPUT_PATH, expected_columns=len(CSV_HEADER))

    with atomic_csv_writer(OUTPUT_PATH, CSV_HEADER) as writer:
        for row in existing_rows:
            writer.writerow(row)

        page_num = 1
        continuer = True

        while continuer:
            logger.info("Analyse de la page %s", page_num)
            try:
                load_page(driver, SEARCH_URL.format(page_num))
            except Exception as exc:
                logger.error("Impossible de charger la page %s après plusieurs tentatives : %s", page_num, exc)
                break

            if page_num == 1:
                logger.info("En attente de la validation des cookies sur Vizzit...")
                card_found = False
                for sel in CARD_SELECTORS:
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                        logger.info("Accès détecté (%s)", sel)
                        card_found = True
                        break
                    except Exception:
                        continue
                if not card_found:
                    logger.error("Aucune carte détectée.")
                    break

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            blocs = []
            for sel in CARD_SELECTORS:
                blocs = driver.find_elements(By.CSS_SELECTOR, sel)
                if blocs:
                    break

            if not blocs:
                logger.warning("Fin des résultats à la page %s.", page_num)
                break

            total_cards_vues += len(blocs)
            annonces_a_visiter = []
            for b in blocs:
                try:
                    lien = find_attr(b, LIEN_SELECTORS, "href")
                    if not lien or lien in liens_vus:
                        continue
                    prix = find_text(b, PRIX_SELECTORS)
                    lieu = find_text(b, LIEU_SELECTORS)
                    details_elems = []
                    for sel in DETAIL_SELECTORS:
                        details_elems = b.find_elements(By.CSS_SELECTOR, sel)
                        if details_elems:
                            break
                    details = " - ".join(d.text.strip() for d in details_elems if d.text.strip())
                    annonces_a_visiter.append({'lieu': lieu, 'prix': prix, 'details': details, 'lien': lien})
                except Exception as exc:
                    erreurs += 1
                    logger.warning("Erreur lors du parsing d'un bloc d'annonce : %s", exc)
                    continue

            compteur_page = 0
            for info in annonces_a_visiter:
                try:
                    load_page(driver, info['lien'])
                    description = ""
                    for sel in DESC_SELECTORS:
                        try:
                            desc_elem = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                            )
                            description = desc_elem.text.strip().replace('\n', ' ')
                            break
                        except Exception:
                            continue

                    image = find_first_image_url(driver, selectors=IMAGE_SELECTORS, base_url=driver.current_url)

                    writer.writerow([info['lieu'], info['prix'], info['details'], description, info['lien'], image])
                    liens_vus.add(info['lien'])
                    compteur_page += 1
                    logger.info("Annonce récupérée : %s", info['lieu'])
                    time.sleep(random.uniform(1, 2))

                except Exception as exc:
                    erreurs += 1
                    logger.warning("Erreur lors de la récupération d'une annonce : %s", exc)
                    try:
                        load_page(driver, SEARCH_URL.format(page_num))
                    except Exception as exc_recovery:
                        logger.error("Impossible de revenir à la page de résultats %s : %s", page_num, exc_recovery)
                    continue

            logger.info("Page %s terminée : %s annonces sauvegardées.", page_num, compteur_page)
            total_nouveaux_run += compteur_page

            if compteur_page == 0:
                continuer = False
            else:
                page_num += 1

    driver.quit()

    if total_cards_vues == 0:
        logger.error("0 annonce trouvée pour Vizzit. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(liens_vus), total_nouveaux_run, erreurs, OUTPUT_PATH
    )
