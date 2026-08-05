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

site_config = load_site_config("orpi")
logger = get_scraper_logger("orpi")

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', f"annonces_{site_config['ville_slug']}_orpi.csv")
base_url = site_config['base_url']

# Sélecteurs avec fallbacks ordonnés par stabilité
CARD_SELECTORS = ["article.c-overlay", "article[class*='overlay']", "article[class*='card']", "article"]
TITRE_SELECTORS = [
    "[class*='c-the-ad-of-program__title']",
    # Refonte observée le 2026-08-03 (canari ORA-21) : le titre n'est plus dans
    # un élément de classe "title" ni un h2/h3, mais dans un <b> à l'intérieur
    # du bloc infos de la carte.
    "[class*='estate-thumb__infos__estate'] b",
    "[class*='title']",
    "h2", "h3",
]
PRIX_SELECTORS = [
    "[class*='price']",
    "[class*='prix']",
    "[class*='amount']",
]
INFOS_SELECTORS = [
    "[class*='detail']",
    "[class*='surface']",
    "[class*='info']",
    "[class*='caracteristique']",
]

def find_text(element, selectors):
    for sel in selectors:
        try:
            return element.find_element(By.CSS_SELECTOR, sel).text.strip()
        except Exception:
            continue
    return ""

def extract_price_from_text(text):
    match = re.search(r'(\d[\d\s]*€|\d[\d\s]*eur)', text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

@retry_with_backoff(max_retries=3, backoff_seconds=2)
def load_page(driver, url):
    driver.get(url)

if __name__ == '__main__':
    logger.info("Lancement du mode 'Ascenseur' Automatique pour ORPI (%s)...", site_config['ville_nom'])

    driver = get_chrome_driver(user_agent=pick_user_agent(), proxy=pick_proxy())

    CSV_HEADER = ['Titre_Lieu', 'Prix', 'Infos', 'Lien', 'Image']
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
            url = base_url.format(page_num)
            logger.info("Analyse de la page %s", page_num)
            try:
                load_page(driver, url)
            except Exception as exc:
                logger.error("Impossible de charger la page %s après plusieurs tentatives : %s", page_num, exc)
                break

            if page_num == 1:
                logger.info("En attente de la validation des cookies sur Orpi...")
                card_found = False
                for sel in CARD_SELECTORS:
                    try:
                        WebDriverWait(driver, 60).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        logger.info("Accès détecté avec sélecteur : %s", sel)
                        card_found = True
                        break
                    except Exception:
                        continue
                if not card_found:
                    logger.error("Aucun sélecteur de carte ne correspond. Structure inconnue.")
                    break
            else:
                time.sleep(random.uniform(3, 6))

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Essai des sélecteurs de carte dans l'ordre
            annonces = []
            for sel in CARD_SELECTORS:
                annonces = driver.find_elements(By.CSS_SELECTOR, sel)
                if annonces:
                    break

            if not annonces:
                logger.warning("Aucune annonce trouvée sur la page %s.", page_num)
                break

            total_cards_vues += len(annonces)
            compteur_nouveaux = 0
            for annonce in annonces:
                try:
                    try:
                        lien_elem = annonce.find_element(By.TAG_NAME, "a")
                        href = lien_elem.get_attribute("href")
                    except Exception:
                        continue

                    if not href or href in liens_vus:
                        continue

                    # Extraction structurée avec fallback sur le texte brut
                    titre = find_text(annonce, TITRE_SELECTORS)
                    prix = find_text(annonce, PRIX_SELECTORS)
                    infos = find_text(annonce, INFOS_SELECTORS)

                    # Si pas de prix via sélecteur, chercher dans le texte complet
                    if not prix:
                        prix = extract_price_from_text(annonce.text)

                    if not prix:
                        continue

                    image = find_first_image_url(annonce, base_url=driver.current_url)

                    writer.writerow([titre, prix, infos, href, image])
                    liens_vus.add(href)
                    compteur_nouveaux += 1
                    logger.info("Annonce trouvée : %s -- %s", titre[:60], prix)

                except Exception as exc:
                    erreurs += 1
                    logger.warning("Erreur lors du parsing d'une annonce : %s", exc)
                    continue

            logger.info("Page %s terminée : %s annonces ajoutées.", page_num, compteur_nouveaux)
            total_nouveaux_run += compteur_nouveaux

            if compteur_nouveaux == 0:
                logger.info("Fin des nouvelles annonces.")
                continuer = False
            else:
                page_num += 1

    driver.quit()

    if total_cards_vues == 0:
        logger.error("0 annonce trouvée pour ORPI. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(liens_vus), total_nouveaux_run, erreurs, OUTPUT_PATH
    )
