import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import csv
import os

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
        print("   ⬇️ Suite chargée...")

if __name__ == '__main__':
    print("🥷 Lancement du mode Furtif pour PAP...")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 60)

    liens_vus = set()

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Lieu', 'Prix', 'Détails', 'Lien'])

        page_num = 1
        continuer = True

        while continuer:
            url = BASE_URL.format(page_num)
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")
            driver.get(url)

            if page_num == 1:
                print("⏳ Attente automatique du chargement des annonces...")
                card_found = False
                for sel in CARD_SELECTORS:
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                        print(f"✅ Annonces détectées ({sel})")
                        card_found = True
                        break
                    except Exception:
                        continue
                if not card_found:
                    print("❌ Impossible de détecter les annonces. Structure inconnue.")
                    break

            print("🔄 Défilement automatique...")
            scroll_to_bottom(driver)
            print("✅ Page entièrement chargée.")
            time.sleep(2)

            annonces = []
            for sel in CARD_SELECTORS:
                annonces = driver.find_elements(By.CSS_SELECTOR, sel)
                if annonces:
                    break

            if not annonces:
                print("🛑 Aucune annonce trouvée.")
                break

            print(f"📊 {len(annonces)} annonces détectées.")
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

                    print(f"🏠 {lieu} | {details} -- 💰 {prix}")
                    writer.writerow([lieu, prix, details, lien])
                    liens_vus.add(lien)
                    compteur += 1

                except Exception:
                    continue

            print(f"✅ Page {page_num} terminée : {compteur} annonces ajoutées.")

            if compteur == 0:
                print("🏁 Plus de nouvelles annonces.")
                continuer = False
            else:
                page_num += 1
                time.sleep(random.uniform(2, 4))

    print(f"\n✨ Terminé ! {len(liens_vus)} annonces sauvegardées dans {OUTPUT_PATH}")
    driver.quit()
