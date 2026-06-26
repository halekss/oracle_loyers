import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import csv
import re
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', 'annonces_lyon_orpi.csv')
base_url = "https://www.orpi.com/recherche/rent?transaction=rent&locations%5B0%5D%5Bvalue%5D=lyon&sort=date-down&layoutType=list&page={}"

# Sélecteurs avec fallbacks ordonnés par stabilité
CARD_SELECTORS = ["article.c-overlay", "article[class*='overlay']", "article[class*='card']", "article"]
TITRE_SELECTORS = [
    "[class*='c-the-ad-of-program__title']",
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

if __name__ == '__main__':
    print("🥷 Lancement du mode 'Ascenseur' Automatique pour ORPI...")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    driver = uc.Chrome(options=options)

    liens_vus = set()

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Titre_Lieu', 'Prix', 'Infos', 'Lien'])

        page_num = 1
        continuer = True

        while continuer:
            url = base_url.format(page_num)
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")
            driver.get(url)

            if page_num == 1:
                print("⏳ En attente de la validation des cookies sur Orpi...")
                card_found = False
                for sel in CARD_SELECTORS:
                    try:
                        WebDriverWait(driver, 60).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        print(f"✅ Accès détecté avec sélecteur : {sel}")
                        card_found = True
                        break
                    except Exception:
                        continue
                if not card_found:
                    print("❌ Aucun sélecteur de carte ne correspond. Structure inconnue.")
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
                print("🛑 Aucune annonce trouvée sur cette page.")
                break

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

                    writer.writerow([titre, prix, infos, href])
                    liens_vus.add(href)
                    compteur_nouveaux += 1
                    print(f"🏠 {titre[:60]}... -- 💰 {prix}")

                except Exception:
                    continue

            print(f"📊 Page {page_num} terminée : {compteur_nouveaux} annonces ajoutées.")

            if compteur_nouveaux == 0:
                print("🏁 Fin des nouvelles annonces.")
                continuer = False
            else:
                page_num += 1

    print(f"\n✨ Terminé ! Fichier sauvegardé dans : {OUTPUT_PATH}")
    driver.quit()
