import requests
from bs4 import BeautifulSoup
import time
import random
import os
import sys

from csv_atomic_writer import atomic_csv_writer
from scraper_utils import get_scraper_logger

logger = get_scraper_logger("paruvendu")

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', 'annonces_lyon_paruvendu.csv')
base_url = "https://www.paruvendu.fr/immobilier/recherche/location/lyon/?rechpv=1&tt=5&tbApp=1&tbDup=1&tbChb=1&tbLof=1&tbAtl=1&tbPla=1&tbMai=1&tbVil=1&tbCha=1&tbPro=1&tbHot=1&tbMou=1&tbFer=1&nbp0=99&pa=FR&lol=0&ray=50&codeINSEE=69000,"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# Sélecteurs avec fallbacks ordonnés par stabilité
CARD_SELECTORS = [
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

if __name__ == '__main__':
    logger.info("Lancement du Scraper ParuVendu (Mode Rapide)...")

    liens_vus = set()
    erreurs = 0
    page_num = 1
    continuer = True

    with atomic_csv_writer(OUTPUT_PATH, ['Titre', 'Prix', 'Lien']) as writer:
        while continuer:
            url_page = base_url if page_num == 1 else f"{base_url}&p={page_num}"
            logger.info("Analyse de la page %s", page_num)

            try:
                response = requests.get(url_page, headers=headers, timeout=15)
                if response.status_code != 200:
                    logger.error("Erreur de réponse HTTP : %s", response.status_code)
                    break
            except Exception as e:
                logger.error("Erreur connexion : %s", e)
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
                break

            compteur_page = 0
            for annonce in annonces:
                try:
                    titre_elem = find_bs4(annonce, TITRE_SELECTORS)
                    prix_elem = find_bs4(annonce, PRIX_SELECTORS)

                    if not titre_elem:
                        continue

                    titre = " ".join(titre_elem.text.split())
                    prix = prix_elem.text.strip() if prix_elem else "N/C"
                    lien_partiel = titre_elem.get('href') if titre_elem.name == 'a' else None
                    lien = f"https://www.paruvendu.fr{lien_partiel}" if lien_partiel else "Pas de lien"

                    if lien in liens_vus or lien == "Pas de lien":
                        continue

                    writer.writerow([titre, prix, lien])
                    liens_vus.add(lien)
                    compteur_page += 1
                    logger.info("Annonce trouvée : %s -- %s", titre, prix)

                except Exception as exc:
                    erreurs += 1
                    logger.warning("Erreur lors du parsing d'une annonce : %s", exc)
                    continue

            logger.info("Page %s terminée : %s annonces ajoutées.", page_num, compteur_page)

            if compteur_page == 0:
                logger.info("Plus de nouvelles annonces disponibles.")
                continuer = False
            else:
                page_num += 1
                time.sleep(random.uniform(1.5, 3))

    if len(liens_vus) == 0:
        logger.error("0 annonce trouvée pour ParuVendu. Le site a peut-être changé de structure.")
        sys.exit(1)

    logger.info(
        "Run terminé : %s trouvées, %s nouvelles, %s erreurs. Fichier : %s",
        len(liens_vus), len(liens_vus), erreurs, OUTPUT_PATH
    )
