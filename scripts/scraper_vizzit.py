import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import csv
import os

OUTPUT_PATH = "../backend/data/annonces_lyon_vizzit.csv"
SEARCH_URL = "https://www.vizzit.fr/fr/properties/{}?searchQuery=lg-fr-cn-fr-type-rentals-hab_appartement-on-hab_house-on-city_id-city_34209,city_34210,city_34211,city_34212,city_34213,city_34214,city_34215,city_34216,city_34217-tf_ids-235728"

def get_driver():
    options = uc.ChromeOptions()
    # ⚡ OPTIMISATION : Désactiver le chargement des images pour aller plus vite
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    driver = uc.Chrome(options=options)
    return driver

if __name__ == '__main__':
    print("🚀 Lancement du scraper Vizzit Optimisé (Mode Rapide)...")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    driver = get_driver()
    wait = WebDriverWait(driver, 10) # Attente plus nerveuse

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Lieu', 'Prix', 'Details', 'Description_A_Propos', 'Lien'])

        page_num = 1
        while True:
            driver.get(SEARCH_URL.format(page_num))

            if page_num == 1:
                input("👉 Valide les cookies puis appuie sur [ENTRÉE]...")
            
            try:
                # Attente du premier bloc d'annonce
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.item__content-area")))
                blocs = driver.find_elements(By.CSS_SELECTOR, "div.item__content-area")
            except:
                break

            annonces_data = []
            for b in blocs:
                try:
                    prix = b.find_element(By.CSS_SELECTOR, "div.display").text.strip()
                    lieu = b.find_element(By.CSS_SELECTOR, "p.item__location").text.strip()
                    details = " - ".join([d.text.strip() for d in b.find_elements(By.CSS_SELECTOR, "span.detail__item")])
                    lien = b.find_element(By.CSS_SELECTOR, "a.item__link").get_attribute("href")
                    annonces_data.append({'lieu': lieu, 'prix': prix, 'details': details, 'lien': lien})
                except:
                    continue

            for info in annonces_data:
                try:
                    driver.get(info['lien'])
                    
                    # ⚡ On attend juste que le texte soit présent (pas besoin qu'il soit "visible" si on ne charge pas les images)
                    desc_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.description__text")))
                    description = desc_elem.text.strip()

                    writer.writerow([info['lieu'], info['prix'], info['details'], description, info['lien']])
                    print(f"✅ {info['lieu']} récupéré.")
                    
                    # Pause ultra-courte mais variable pour rester "humain"
                    time.sleep(random.uniform(0.8, 1.5))
                    
                    driver.back()
                    # On réduit le temps de battement après le retour
                    time.sleep(0.5)

                except Exception:
                    driver.get(SEARCH_URL.format(page_num))
                    continue
            
            page_num += 1

    driver.quit()