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
    enrich_descriptions,
    find_first_image_url,
    get_chrome_driver,
    get_scraper_logger,
    load_existing_rows,
    load_site_config,
    pick_proxy,
    pick_user_agent,
    retry_with_backoff,
    selenium_description_fetcher,
    archive_stale_rows,
    should_continue_pagination,
    today_iso,
)

site_config = load_site_config("orpi")
logger = get_scraper_logger("orpi")

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', f"annonces_{site_config['ville_slug']}_orpi.csv")
base_url = site_config['base_url']

# Sélecteurs avec fallbacks ordonnés par stabilité

# ORA-161 : « L'avis de l'agent » = texte libre de l'annonce, seul `.s-cms` de la
# page détail (relevé sur le DOM réel le 2026-09-24).
DESCRIPTION_SELECTORS = ["div.s-cms", ".s-cms"]
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
# ORA-159 : le nom de quartier est déjà dans la carte, dans son propre élément
# ("Lyon 8- Monplaisir - Frères Lumière", relevé sur le DOM réel le
# 2026-09-24) — inutile de le rechercher par regex dans le blob `Infos`
# (`[class*='detail']`), qui mélange prix, boutons ("Message", "Favoris") et tags.
QUARTIER_SELECTORS = [
    "[class*='estate-thumb__infos__location']",
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

def parse_quartier(location):
    """Nom de quartier seul depuis le libellé de localisation Orpi
    ("Lyon 8- Monplaisir - Frères Lumière" -> "Monplaisir - Frères Lumière").
    Chaîne vide si le libellé n'a pas de partie quartier (ex. "Lyon 5")."""
    parts = re.split(r'-\s+', location.strip(), maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""

def extract_price_from_text(text):
    match = re.search(r'(\d[\d\s]*€|\d[\d\s]*eur)', text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

@retry_with_backoff(max_retries=3, backoff_seconds=2)
def load_page(driver, url):
    driver.get(url)

if __name__ == '__main__':
    logger.info("Lancement du mode 'Ascenseur' Automatique pour ORPI (%s)...", site_config['ville_nom'])

    driver = get_chrome_driver(user_agent=pick_user_agent(), proxy=pick_proxy())

    CSV_HEADER = ['Titre_Lieu', 'Prix', 'Infos', 'Lien', 'Image', 'DerniereVue', 'Quartier', 'Description']
    LIEN_INDEX = CSV_HEADER.index('Lien')
    DESCRIPTION_INDEX = CSV_HEADER.index('Description')
    DERNIERE_VUE_INDEX = CSV_HEADER.index('DerniereVue')

    existing_rows, liens_vus = load_existing_rows(OUTPUT_PATH, CSV_HEADER)
    rows_by_lien = {row[LIEN_INDEX]: row for row in existing_rows}
    today = today_iso()

    erreurs = 0
    total_nouveaux_run = 0
    total_cards_vues = 0
    consecutive_empty_pages = 0
    vus_ce_run = set()
    run_complet = False

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
            run_complet = page_num > 1
            break

        vus_avant_page = len(vus_ce_run)
        total_cards_vues += len(annonces)
        compteur_nouveaux = 0
        for annonce in annonces:
            try:
                try:
                    lien_elem = annonce.find_element(By.TAG_NAME, "a")
                    href = lien_elem.get_attribute("href")
                except Exception:
                    continue

                if not href:
                    continue

                if href in rows_by_lien:
                    # Déjà connue : pas de re-scraping de ses détails, on note juste
                    # qu'elle est toujours présente sur le site (ORA-134, TTL).
                    rows_by_lien[href][DERNIERE_VUE_INDEX] = today
                    vus_ce_run.add(href)
                    continue

                # Extraction structurée avec fallback sur le texte brut
                titre = find_text(annonce, TITRE_SELECTORS)
                prix = find_text(annonce, PRIX_SELECTORS)
                infos = find_text(annonce, INFOS_SELECTORS)
                quartier = parse_quartier(find_text(annonce, QUARTIER_SELECTORS))

                # Si pas de prix via sélecteur, chercher dans le texte complet
                if not prix:
                    prix = extract_price_from_text(annonce.text)

                if not prix:
                    continue

                image = find_first_image_url(annonce, base_url=driver.current_url)

                rows_by_lien[href] = [titre, prix, infos, href, image, today, quartier, ""]
                liens_vus.add(href)
                vus_ce_run.add(href)
                compteur_nouveaux += 1
                logger.info("Annonce trouvée : %s -- %s", titre[:60], prix)

            except Exception as exc:
                erreurs += 1
                logger.warning("Erreur lors du parsing d'une annonce : %s", exc)
                continue

        logger.info("Page %s terminée : %s annonces ajoutées.", page_num, compteur_nouveaux)
        total_nouveaux_run += compteur_nouveaux
        checkpoint()

        continuer, consecutive_empty_pages = should_continue_pagination(len(vus_ce_run) - vus_avant_page, consecutive_empty_pages)
        if not continuer:
            run_complet = True
            logger.info("Fin des nouvelles annonces (%s page(s) consécutive(s) sans nouveauté).", consecutive_empty_pages)
        page_num += 1

    # Non revues pendant ce run -> fichier d'archive (historique des prix), avant enrichissement.
    archive_stale_rows(rows_by_lien, vus_ce_run, OUTPUT_PATH, CSV_HEADER, logger, run_complet)
    checkpoint()

    # ORA-161 : description libre depuis la page détail (plafonnée, cf. scraper_utils)
    enrich_descriptions(rows_by_lien, LIEN_INDEX, DESCRIPTION_INDEX,
                        selenium_description_fetcher(driver, DESCRIPTION_SELECTORS), logger)
    checkpoint()

    driver.quit()

    if total_cards_vues == 0:
        logger.error("0 annonce trouvée pour ORPI. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(rows_by_lien), total_nouveaux_run, erreurs, OUTPUT_PATH
    )
