from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
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
DETAIL_SELECTORS = [
    # Refonte observée le 2026-08-11 (ORA-71 POC) : "div.info-tag" a remplacé
    # "span.detail__item". Les anciens sélecteurs restent en repli.
    "div.info-tag",
    "span.detail__item",
    "span[class*='detail']",
    "[class*='feature']",
]
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

def decode_data_o_link(element):
    """Repli quand aucune balise <a href> n'est trouvée : Vizzit encode
    parfois le lien de la fiche annonce en base64 dans l'attribut data-o de
    la carte elle-même (classes "obf-link obf-blank" observées, technique
    anti-scraping) — constaté sur un run réel (0 lien trouvé via <a>, alors
    que la carte a bien un attribut data-o exploitable)."""
    try:
        data_o = element.get_attribute("data-o")
        if data_o:
            return base64.b64decode(data_o).decode("utf-8")
    except Exception:
        pass
    return ""

def build_page_url(base_url, page_num):
    """URL de résultats pour une page donnée. Vizzit pagine via le
    paramètre de requête p_n (ex: ...&p_n=2), pas via le numéro dans le
    chemin de l'URL — le `{}` de SEARCH_URL (hérité de l'ancienne
    structure) est ignoré par le site : constaté qu'un numéro différent
    dans le chemin renvoie exactement les mêmes annonces (bug réel qui
    plafonnait le scraper à sa première page, quel que soit le nombre
    total de résultats). Page 1 = URL de base seule, sans p_n."""
    url = base_url.format(1)
    if page_num > 1:
        url += f"&p_n={page_num}"
    return url

def apply_price_band(base_url, band):
    """Ajoute les filtres de prix mn_p/mx_p au searchQuery Vizzit (accolés
    à la fin du base_url — l'ordre des segments dash-delimited n'a pas
    d'effet observé, constaté en direct sur le site).

    Contourne un plafond réel du site : une recherche Vizzit ne renvoie
    jamais plus de 20 pages (~480 annonces) même si le total réel est plus
    grand (803 pour Lille) — d'où 480/803 annonces manquantes tant que la
    recherche n'est pas subdivisée en tranches de prix qui restent chacune
    sous ce plafond (cf. price_bands dans scraping_config.json)."""
    url = base_url
    if band.get("min") is not None:
        url += f"-mn_p-{band['min']}"
    if band.get("max") is not None:
        url += f"-mx_p-{band['max']}"
    return url

@retry_with_backoff(max_retries=3, backoff_seconds=2)
def load_page(driver, url):
    driver.get(url)

def scrape_search(driver, wait, search_url, rows_by_lien, liens_vus, today, derniere_vue_index, logger, checkpoint=lambda: None):
    """Parcourt toutes les pages d'une recherche Vizzit donnée (déjà filtrée
    par tranche de prix le cas échéant). Renvoie (nouveaux, cards_vues, erreurs).

    `checkpoint` (callable sans argument) est appelé après chaque page plutôt
    que de tout écrire une seule fois à la toute fin du run : régression
    réelle constatée sur scraper_seloger.py (242 pages perdues suite à un
    hoquet Selenium transitoire tardif, alors que atomic_csv_writer n'était
    appelé qu'une fois à la toute fin). Pas d'effet par défaut (no-op), pour
    rester testable sans dépendre du système de fichiers."""
    erreurs = 0
    nouveaux = 0
    cards_vues = 0
    consecutive_empty_pages = 0
    page_num = 1
    continuer = True

    while continuer:
        logger.info("Analyse de la page %s", page_num)
        try:
            load_page(driver, build_page_url(search_url, page_num))
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

        cards_vues += len(blocs)
        annonces_a_visiter = []
        for b in blocs:
            try:
                lien = find_attr(b, LIEN_SELECTORS, "href") or decode_data_o_link(b)
                if not lien:
                    continue

                if lien in rows_by_lien:
                    # Déjà connue : pas de re-visite de sa page détail, on note juste
                    # qu'elle est toujours présente sur le site (ORA-134, TTL).
                    rows_by_lien[lien][derniere_vue_index] = today
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

                rows_by_lien[info['lien']] = [
                    info['lieu'], info['prix'], info['details'], description, info['lien'], image, today
                ]
                liens_vus.add(info['lien'])
                compteur_page += 1
                logger.info("Annonce récupérée : %s", info['lieu'])
                time.sleep(random.uniform(1, 2))

            except Exception as exc:
                erreurs += 1
                logger.warning("Erreur lors de la récupération d'une annonce : %s", exc)
                try:
                    load_page(driver, build_page_url(search_url, page_num))
                except Exception as exc_recovery:
                    logger.error("Impossible de revenir à la page de résultats %s : %s", page_num, exc_recovery)
                continue

        logger.info("Page %s terminée : %s annonces sauvegardées.", page_num, compteur_page)
        nouveaux += compteur_page
        checkpoint()

        continuer, consecutive_empty_pages = should_continue_pagination(compteur_page, consecutive_empty_pages)
        page_num += 1

    return nouveaux, cards_vues, erreurs

if __name__ == '__main__':
    logger.info("Lancement du scraper Vizzit Automatique (%s)...", site_config['ville_nom'])

    driver = get_chrome_driver(block_images=True, user_agent=pick_user_agent(), proxy=pick_proxy())
    wait = WebDriverWait(driver, 15)
    erreurs = 0
    total_nouveaux_run = 0
    total_cards_vues = 0

    CSV_HEADER = ['Lieu', 'Prix', 'Details', 'Description', 'Lien', 'Image', 'DerniereVue']
    LIEN_INDEX = CSV_HEADER.index('Lien')
    DERNIERE_VUE_INDEX = CSV_HEADER.index('DerniereVue')

    existing_rows, liens_vus = load_existing_rows(OUTPUT_PATH, CSV_HEADER)
    rows_by_lien = {row[LIEN_INDEX]: row for row in existing_rows}
    today = today_iso()

    def checkpoint():
        with atomic_csv_writer(OUTPUT_PATH, CSV_HEADER) as writer:
            for row in rows_by_lien.values():
                writer.writerow(row)

    # Une recherche Vizzit ne renvoie jamais plus de 20 pages (~480
    # annonces), même si le nombre réel de résultats est plus grand (803
    # constatés pour Lille avec une seule recherche) : on subdivise donc en
    # tranches de prix (price_bands, cf. scraping_config.json) qui restent
    # chacune sous ce plafond. Les villes sans price_bands gardent le
    # comportement d'origine (une seule recherche, band vide).
    price_bands = site_config.get('price_bands') or [{}]

    for band in price_bands:
        band_url = apply_price_band(SEARCH_URL, band)
        logger.info("Tranche de prix %s : %s", band or "aucune", band_url)
        nouveaux, cards_vues, band_erreurs = scrape_search(
            driver, wait, band_url, rows_by_lien, liens_vus, today, DERNIERE_VUE_INDEX, logger, checkpoint
        )
        total_nouveaux_run += nouveaux
        total_cards_vues += cards_vues
        erreurs += band_erreurs

    driver.quit()

    if total_cards_vues == 0:
        logger.error("0 annonce trouvée pour Vizzit. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(rows_by_lien), total_nouveaux_run, erreurs, OUTPUT_PATH
    )
