from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import sys

from scraper_utils import get_chrome_driver, find_first, atomic_csv_writer, retry_with_backoff

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

@retry_with_backoff(max_retries=3, backoff_seconds=2)
def load_page(driver, url):
    driver.get(url)

if __name__ == '__main__':
    print("🥷 Lancement du mode Furtif Automatique pour Century 21...")

    driver = get_chrome_driver()

    liens_vus = set()

    with atomic_csv_writer(OUTPUT_PATH, ['Titre', 'Prix', 'Lieu_Surface', 'Lien']) as writer:
        page_num = 1
        continuer = True

        while continuer:
            url = base_url.format(page_num)
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")
            load_page(driver, url)

            if page_num == 1:
                print("⏳ En attente de la validation des cookies...")
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, CARD_SELECTOR))
                    )
                    print("✅ Validation détectée, démarrage du scraping.")
                except Exception:
                    print("❌ Temps d'attente dépassé.")
                    break
            else:
                time.sleep(random.uniform(2, 4))

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            annonces = driver.find_elements(By.CSS_SELECTOR, CARD_SELECTOR)
            if not annonces:
                print("🛑 Aucun bloc trouvé. Fin de la recherche.")
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
                    print(f"🏠 {titre} - {prix}")
                except Exception:
                    continue

            print(f"📊 Page {page_num} terminée : {compteur_nouveaux} annonces ajoutées.")

            if compteur_nouveaux == 0:
                print("🏁 Fin des nouvelles annonces.")
                continuer = False
            else:
                page_num += 1

    driver.quit()

    if len(liens_vus) == 0:
        print(f"❌ ERREUR : 0 annonce trouvée pour Century 21. Le site a peut-être changé de structure.")
        sys.exit(1)

    print(f"\n✨ Travail terminé ! {len(liens_vus)} annonces collectées dans : {OUTPUT_PATH}")
