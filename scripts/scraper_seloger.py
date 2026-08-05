from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import re
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

site_config = load_site_config("seloger")
logger = get_scraper_logger("seloger")

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', f"annonces_{site_config['ville_slug']}_seloger.csv")
base_url = site_config['base_url']
PAGE_QUERY_PARAM = site_config['page_query_param']

CARD_SELECTORS = [
    "a[data-testid='card-mfe-covering-link-testid']",
    "a[data-testid*='covering-link']",
    "a[data-testid*='card']",
]
# Sélecteurs DOM fallback quand le title attribute n'est pas parsable
TITRE_DOM_SELECTORS = ["[data-testid*='title']", "h2", "h3", "[class*='title']"]
PRIX_DOM_SELECTORS = ["[data-testid*='price']", "[class*='price']", "[class*='prix']"]
LIEU_DOM_SELECTORS = ["[data-testid*='location']", "[class*='location']", "[class*='lieu']", "[class*='address']"]
INFOS_DOM_SELECTORS = ["[data-testid*='detail']", "[class*='detail']", "[class*='info']", "[class*='surface']"]

def find_text(element, selectors):
    for sel in selectors:
        try:
            return element.find_element(By.CSS_SELECTOR, sel).text.strip()
        except Exception:
            continue
    return ""

def parse_title_attribute(full_title):
    """Parse 'Type - Lieu - Prix - Infos' format. Returns None if format unrecognized."""
    if not full_title or ' - ' not in full_title:
        return None
    parts = full_title.split(' - ')
    titre = parts[0].strip()
    lieu = parts[1].strip() if len(parts) > 1 else "Lyon"
    prix = ""
    infos_parts = []
    for part in parts[2:]:
        if re.search(r'\d.*€', part):
            prix = part.strip()
        else:
            infos_parts.append(part.strip())
    return titre, lieu, prix, " - ".join(infos_parts)

@retry_with_backoff(max_retries=3, backoff_seconds=2)
def load_page(driver, url):
    driver.get(url)

if __name__ == '__main__':
    logger.info("Lancement du mode Furtif Automatique pour SeLoger (%s)...", site_config['ville_nom'])

    driver = get_chrome_driver(user_agent=pick_user_agent(), proxy=pick_proxy())

    CSV_HEADER = ['Titre', 'Prix', 'Lieu', 'Infos', 'Lien', 'Image']
    existing_rows, liens_vus = load_existing_rows(OUTPUT_PATH, expected_columns=len(CSV_HEADER))
    erreurs = 0
    total_nouveaux_run = 0
    total_cards_vues = 0

    with atomic_csv_writer(OUTPUT_PATH, CSV_HEADER) as writer:
        for row in existing_rows:
            writer.writerow(row)

        page_num = 1
        continuer = True

        while continuer:
            url = base_url if page_num == 1 else f"{base_url}&{PAGE_QUERY_PARAM}={page_num}"
            logger.info("Analyse de la page %s", page_num)
            try:
                load_page(driver, url)
            except Exception as exc:
                logger.error("Impossible de charger la page %s après plusieurs tentatives : %s", page_num, exc)
                break

            if page_num == 1:
                logger.info("En attente de la validation du Captcha ou des Cookies...")
                card_found = False
                for sel in CARD_SELECTORS:
                    try:
                        WebDriverWait(driver, 120).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        logger.info("Page accessible (%s)", sel)
                        card_found = True
                        break
                    except Exception:
                        continue
                if not card_found:
                    logger.error("Aucune carte détectée. Captcha non résolu ou structure changée.")
                    break
            else:
                time.sleep(random.uniform(5, 8))

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
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
            compteur_page = 0
            for annonce in annonces:
                try:
                    lien = annonce.get_attribute("href")
                    if not lien or lien in liens_vus:
                        continue

                    # Stratégie 1 : parser l'attribut title
                    full_title = annonce.get_attribute("title") or ""
                    parsed = parse_title_attribute(full_title)

                    if parsed:
                        titre, lieu, prix, infos = parsed
                    else:
                        # Stratégie 2 : extraction DOM directe
                        titre = find_text(annonce, TITRE_DOM_SELECTORS)
                        prix = find_text(annonce, PRIX_DOM_SELECTORS)
                        lieu = find_text(annonce, LIEU_DOM_SELECTORS)
                        infos = find_text(annonce, INFOS_DOM_SELECTORS)

                    if not prix:
                        continue

                    image = find_first_image_url(annonce, base_url=driver.current_url)

                    writer.writerow([titre, prix, lieu, infos, lien, image])
                    liens_vus.add(lien)
                    compteur_page += 1
                    logger.info("Annonce trouvée : %s (%s) -- %s", titre, lieu, prix)

                except Exception as exc:
                    erreurs += 1
                    logger.warning("Erreur lors du parsing d'une annonce : %s", exc)
                    continue

            logger.info("Page %s terminée : %s nouvelles annonces.", page_num, compteur_page)
            total_nouveaux_run += compteur_page

            if compteur_page == 0:
                logger.info("Plus de nouvelles annonces uniques.")
                continuer = False
            else:
                page_num += 1

    driver.quit()

    if total_cards_vues == 0:
        logger.error("0 annonce trouvée pour SeLoger. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(liens_vus), total_nouveaux_run, erreurs, OUTPUT_PATH
    )
