import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import csv
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', 'annonces_lyon_vizzit.csv')
SEARCH_URL = "https://www.vizzit.fr/fr/properties/{}?searchQuery=lg-fr-cn-fr-type-rentals-hab_appartement-on-hab_house-on-city_id-city_34209,city_34210,city_34211,city_34212,city_34213,city_34214,city_34215,city_34216,city_34217-tf_ids-235728"

CARD_SELECTORS = [
    "div.item__content-area",
    "div[class*='item__content']",
    "article[class*='item']",
    "div[class*='property-card']",
]
LIEN_SELECTORS = ["a.item__link", "a[class*='item__link']", "a[class*='property-link']", "a"]
PRIX_SELECTORS = ["div.display", "div[class*='display']", "[class*='price']", "[class*='prix']"]
LIEU_SELECTORS = ["p.item__location", "p[class*='location']", "[class*='location']", "[class*='lieu']"]
DETAIL_SELECTORS = ["span.detail__item", "span[class*='detail']", "[class*='feature']"]
DESC_SELECTORS = ["p.description__text", "p[class*='description']", "div[class*='description']", "[class*='desc']"]

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

def get_driver():
    options = uc.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    return uc.Chrome(options=options)

if __name__ == '__main__':
    print("🚀 Lancement du scraper Vizzit Automatique...")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    driver = get_driver()
    wait = WebDriverWait(driver, 15)

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Lieu', 'Prix', 'Details', 'Description', 'Lien'])

        page_num = 1
        liens_vus = set()
        continuer = True

        while continuer:
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")
            driver.get(SEARCH_URL.format(page_num))

            if page_num == 1:
                print("⏳ En attente de la validation des cookies sur Vizzit...")
                card_found = False
                for sel in CARD_SELECTORS:
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                        print(f"✅ Accès détecté ({sel})")
                        card_found = True
                        break
                    except Exception:
                        continue
                if not card_found:
                    print("❌ Aucune carte détectée.")
                    break

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            blocs = []
            for sel in CARD_SELECTORS:
                blocs = driver.find_elements(By.CSS_SELECTOR, sel)
                if blocs:
                    break

            if not blocs:
                print("🛑 Fin des résultats.")
                break

            annonces_a_visiter = []
            for b in blocs:
                try:
                    lien = find_attr(b, LIEN_SELECTORS, "href")
                    if not lien or lien in liens_vus:
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
                except Exception:
                    continue

            compteur_page = 0
            for info in annonces_a_visiter:
                try:
                    driver.get(info['lien'])
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

                    writer.writerow([info['lieu'], info['prix'], info['details'], description, info['lien']])
                    liens_vus.add(info['lien'])
                    compteur_page += 1
                    print(f"🏠 {info['lieu']} récupéré.")
                    time.sleep(random.uniform(1, 2))

                except Exception:
                    driver.get(SEARCH_URL.format(page_num))
                    continue

            print(f"📊 Page {page_num} terminée : {compteur_page} annonces sauvegardées.")

            if compteur_page == 0:
                continuer = False
            else:
                page_num += 1

    print(f"\n✨ Scraping Vizzit terminé ! Fichier : {OUTPUT_PATH}")
    driver.quit()
