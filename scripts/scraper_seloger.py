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
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', 'annonces_lyon_seloger.csv')
base_url = "https://www.seloger.com/classified-search?distributionTypes=Rent&estateTypes=House,Apartment&locations=AD08FR28808"

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

if __name__ == '__main__':
    print("🥷 Lancement du mode Furtif Automatique pour SeLoger...")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    driver = uc.Chrome(options=options)

    liens_vus = set()

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Titre', 'Prix', 'Lieu', 'Infos', 'Lien'])

        page_num = 1
        continuer = True

        while continuer:
            url = base_url if page_num == 1 else f"{base_url}&page={page_num}"
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")
            driver.get(url)

            if page_num == 1:
                print("⏳ En attente de la validation du Captcha ou des Cookies...")
                card_found = False
                for sel in CARD_SELECTORS:
                    try:
                        WebDriverWait(driver, 120).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        print(f"✅ Page accessible ({sel})")
                        card_found = True
                        break
                    except Exception:
                        continue
                if not card_found:
                    print("❌ Aucune carte détectée. Captcha non résolu ou structure changée.")
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
                print("🛑 Aucune annonce trouvée sur cette page.")
                break

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

                    writer.writerow([titre, prix, lieu, infos, lien])
                    liens_vus.add(lien)
                    compteur_page += 1
                    print(f"🏠 {titre} ({lieu}) -- 💰 {prix}")

                except Exception:
                    continue

            print(f"📊 Page {page_num} terminée : {compteur_page} nouvelles annonces.")

            if compteur_page == 0:
                print("🏁 Plus de nouvelles annonces uniques.")
                continuer = False
            else:
                page_num += 1

    print(f"\n✨ Scraping SeLoger terminé ! Fichier : {OUTPUT_PATH}")
    driver.quit()
