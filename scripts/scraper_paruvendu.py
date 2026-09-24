import requests
from bs4 import BeautifulSoup
import time
import random
import os
import sys
from urllib.parse import urljoin

from scraper_utils import (
    atomic_csv_writer,
    clean_description,
    enrich_descriptions,
    get_scraper_logger,
    load_existing_rows,
    load_site_config,
    pick_proxy,
    pick_user_agent,
    retry_with_backoff,
    archive_stale_rows,
    should_continue_pagination,
    today_iso,
)

site_config = load_site_config("paruvendu")
logger = get_scraper_logger("paruvendu")

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', f"annonces_{site_config['ville_slug']}_paruvendu.csv")
base_url = site_config['base_url']
PAGE_QUERY_PARAM = site_config['page_query_param']

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

headers = {
    "User-Agent": pick_user_agent() or DEFAULT_USER_AGENT,
    "Accept-Language": "fr-FR,fr;q=0.9",
}

_proxy = pick_proxy()
PROXIES = {"http": _proxy, "https": _proxy} if _proxy else None

# Sélecteurs avec fallbacks ordonnés par stabilité
CARD_SELECTORS = [
    # Refonte observée le 2026-08-03 (canari ORA-21) : blocAnnonce est
    # maintenant porté par un <div>, plus par un <article>.
    ("div", {"class": "blocAnnonce"}),
    ("article", {"class": "blocAnnonce"}),
    ("article", {"class_": lambda c: c and "annonce" in c.lower()}),
    ("div", {"class": "annonce"}),
    ("li", {"class_": lambda c: c and "annonce" in c.lower()}),
]
TITRE_SELECTORS = [
    ("a", {"class": "popinphoto_liste_titre"}),
    ("a", {"class_": lambda c: c and "titre" in c.lower()}),
    ("h2", {}),
    ("h3", {}),
]
PRIX_SELECTORS = [
    ("div", {"class": "popinphoto_liste_prix"}),
    ("span", {"class_": lambda c: c and "prix" in c.lower()}),
    ("div", {"class_": lambda c: c and "prix" in c.lower()}),
    ("span", {"class_": lambda c: c and "price" in c.lower()}),
    # Refonte observée le 2026-08-03 (canari ORA-21) : le prix n'a plus de
    # classe dédiée, seul son conteneur ("encoded-lnk") reste identifiable.
    ("div", {"class": "encoded-lnk"}),
]

def find_bs4(soup_elem, selectors):
    for tag, attrs in selectors:
        try:
            found = soup_elem.find(tag, attrs)
            if found:
                return found
        except Exception:
            continue
    return None


IMAGE_ATTRIBUTES = ("data-src", "data-lazy-src", "data-lazy", "srcset", "src")


def find_image_bs4(soup_elem, base_url=None):
    """Équivalent BeautifulSoup de `scraper_utils.find_first_image_url` (pas de
    Selenium/WebElement ici) : même cascade d'attributs pour gérer le lazy-loading,
    et même résolution des chemins relatifs via `base_url` (l'URL de la page
    fetchée) en URL absolue."""
    img = soup_elem.find("img")
    if not img:
        return ""
    for attribute in IMAGE_ATTRIBUTES:
        value = (img.get(attribute) or "").strip()
        if not value:
            continue
        if attribute == "srcset":
            value = value.split(",")[0].strip().split(" ")[0].strip()
        if value:
            return urljoin(base_url, value) if base_url else value
    return ""

@retry_with_backoff(max_retries=3, backoff_seconds=2, exceptions=(requests.exceptions.RequestException,))
def fetch_page(url):
    return requests.get(url, headers=headers, timeout=15, proxies=PROXIES)


# ORA-161 : description libre de la page détail (relevé sur le DOM réel le
# 2026-09-24 : `#txtAnnonceTrunc`, contient l'adresse complète de l'annonce).
DESCRIPTION_SELECTORS = ["#txtAnnonceTrunc", "div.txt_annonceauto", "[class*='txt_annonce']"]


def find_lien_partiel(annonce, titre_elem):
    """Lien de l'annonce : le titre s'il est un <a>, sinon le premier lien
    /immobilier/ de la carte (le titre est un <h3> depuis la refonte du site,
    2026-09-24 : sans ce repli, les 30 cartes de chaque page étaient ignorées)."""
    if titre_elem.name == 'a':
        return titre_elem.get('href')
    lien = annonce.find('a', href=lambda h: h and h.startswith('/immobilier/'))
    return lien.get('href') if lien else None


def find_description_bs4(soup):
    """Équivalent BeautifulSoup de `selenium_description_fetcher` : premier
    texte de description non vide de la page détail, "" si aucun."""
    for selector in DESCRIPTION_SELECTORS:
        for element in soup.select(selector):
            text = clean_description(element.get_text(" ", strip=True))
            if text:
                return text
    return ""


def fetch_description(url):
    """Description libre d'une annonce ParuVendu ("" si l'annonce n'existe plus
    ou n'a pas de texte) ; lève si la page est inaccessible."""
    response = fetch_page(url)
    if response.status_code in (404, 410):  # annonce retirée : pas une erreur de blocage
        return ""
    response.raise_for_status()
    if "antiaspiration" in response.url:  # captcha anti-bot : blocage, pas une annonce sans texte
        raise RuntimeError("Captcha anti-aspiration ParuVendu (requêtes bloquées)")
    return find_description_bs4(BeautifulSoup(response.text, "html.parser"))

if __name__ == '__main__':
    logger.info("Lancement du Scraper ParuVendu (Mode Rapide) (%s)...", site_config['ville_nom'])

    CSV_HEADER = ['Titre', 'Prix', 'Lien', 'Image', 'DerniereVue', 'Description']
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
    page_num = 1
    continuer = True

    def checkpoint():
        """Persiste l'état courant de `rows_by_lien` (écriture atomique complète,
        pas un append). Appelée après chaque page plutôt qu'une seule fois à la
        fin du run : régression réelle constatée sur scraper_seloger.py (242
        pages perdues suite à un hoquet Selenium transitoire tardif, alors que
        atomic_csv_writer n'était appelé qu'une fois à la toute fin du run)."""
        with atomic_csv_writer(OUTPUT_PATH, CSV_HEADER) as writer:
            for row in rows_by_lien.values():
                writer.writerow(row)

    while continuer:
        url_page = base_url if page_num == 1 else f"{base_url}&{PAGE_QUERY_PARAM}={page_num}"
        logger.info("Analyse de la page %s", page_num)

        try:
            response = fetch_page(url_page)
        except requests.exceptions.RequestException as exc:
            logger.error("Échec réseau persistant après plusieurs tentatives sur la page %s : %s", page_num, exc)
            break

        if response.status_code != 200:
            logger.error("Erreur de réponse HTTP : %s", response.status_code)
            break

        soup = BeautifulSoup(response.text, "html.parser")

        # Essai des sélecteurs de carte dans l'ordre
        annonces = []
        for tag, attrs in CARD_SELECTORS:
            annonces = soup.find_all(tag, attrs)
            if annonces:
                break

        if not annonces:
            logger.warning("Aucune annonce trouvée sur la page %s (fin des résultats).", page_num)
            run_complet = page_num > 1
            break

        vus_avant_page = len(vus_ce_run)
        total_cards_vues += len(annonces)
        compteur_page = 0
        for annonce in annonces:
            try:
                titre_elem = find_bs4(annonce, TITRE_SELECTORS)
                prix_elem = find_bs4(annonce, PRIX_SELECTORS)

                if not titre_elem:
                    continue

                titre = " ".join(titre_elem.text.split())
                prix = prix_elem.text.strip() if prix_elem else "N/C"
                lien_partiel = find_lien_partiel(annonce, titre_elem)
                lien = f"https://www.paruvendu.fr{lien_partiel}" if lien_partiel else "Pas de lien"

                if lien == "Pas de lien":
                    continue

                if lien in rows_by_lien:
                    # Déjà connue : pas de re-scraping de ses détails, on note juste
                    # qu'elle est toujours présente sur le site (ORA-134, TTL).
                    rows_by_lien[lien][DERNIERE_VUE_INDEX] = today
                    vus_ce_run.add(lien)
                    continue

                image = find_image_bs4(annonce, base_url=url_page)

                rows_by_lien[lien] = [titre, prix, lien, image, today, ""]
                liens_vus.add(lien)
                vus_ce_run.add(lien)
                compteur_page += 1
                logger.info("Annonce trouvée : %s -- %s", titre, prix)

            except Exception as exc:
                erreurs += 1
                logger.warning("Erreur lors du parsing d'une annonce : %s", exc)
                continue

        logger.info("Page %s terminée : %s annonces ajoutées.", page_num, compteur_page)
        total_nouveaux_run += compteur_page
        checkpoint()

        continuer, consecutive_empty_pages = should_continue_pagination(len(vus_ce_run) - vus_avant_page, consecutive_empty_pages)
        if not continuer:
            run_complet = True
            logger.info("Fin des nouvelles annonces (%s page(s) consécutive(s) sans nouveauté).", consecutive_empty_pages)
        else:
            time.sleep(random.uniform(1.5, 3))
        page_num += 1

    # Non revues pendant ce run -> fichier d'archive (historique des prix), avant enrichissement.
    archive_stale_rows(rows_by_lien, vus_ce_run, OUTPUT_PATH, CSV_HEADER, logger, run_complet)
    checkpoint()

    # ORA-161 : description libre depuis la page détail (plafonnée, cf. scraper_utils)
    enrich_descriptions(rows_by_lien, LIEN_INDEX, DESCRIPTION_INDEX, fetch_description, logger)
    checkpoint()

    if total_cards_vues == 0:
        logger.error("0 annonce trouvée pour ParuVendu. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(rows_by_lien), total_nouveaux_run, erreurs, OUTPUT_PATH
    )
