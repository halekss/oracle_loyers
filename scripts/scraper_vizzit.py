import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import csv
import os

# Configuration des chemins et URL
OUTPUT_PATH = "backend/data/annonces_lyon_vizzit.csv"
SEARCH_URL = "https://www.vizzit.fr/fr/properties/{}?searchQuery=lg-fr-cn-fr-type-rentals-hab_appartement-on-hab_house-on-city_id-city_34209,city_34210,city_34211,city_34212,city_34213,city_34214,city_34215,city_34216,city_34217-tf_ids-235728"

def get_driver():
    options = uc.ChromeOptions()
    # Optimisation : on ne charge pas les images pour gagner en vitesse
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    # Utilisation de ta version de Chrome
    driver = uc.Chrome(options=options, version_main=144)
    return driver

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

            # --- GESTION AUTOMATIQUE (Cookies) ---
            if page_num == 1:
                print("⏳ En attente de la validation des cookies sur Vizzit...")
                try:
                    # On attend que le premier bloc d'annonce apparaisse
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.item__content-area")))
                    print("✅ Accès détecté.")
                except:
                    print("❌ Temps d'attente dépassé.")
                    break
            
            # --- RÉCUPÉRATION DES BLOCS SUR LA PAGE ---
            try:
                blocs = driver.find_elements(By.CSS_SELECTOR, "div.item__content-area")
            except:
                break

            if not blocs:
                print("🛑 Fin des résultats.")
                break

            annonces_a_visiter = []
            for b in blocs:
                try:
                    lien = b.find_element(By.CSS_SELECTOR, "a.item__link").get_attribute("href")
                    if lien not in liens_vus:
                        prix = b.find_element(By.CSS_SELECTOR, "div.display").text.strip()
                        lieu = b.find_element(By.CSS_SELECTOR, "p.item__location").text.strip()
                        details = " - ".join([d.text.strip() for d in b.find_elements(By.CSS_SELECTOR, "span.detail__item")])
                        
                        annonces_a_visiter.append({
                            'lieu': lieu, 
                            'prix': prix, 
                            'details': details, 
                            'lien': lien
                        })
                except:
                    continue

            # --- VISITE DE CHAQUE ANNONCE POUR LA DESCRIPTION ---
            compteur_page = 0
            for info in annonces_a_visiter:
                try:
                    driver.get(info['lien'])
                    
                    # On attend la description spécifique à Vizzit
                    desc_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.description__text")))
                    description = desc_elem.text.strip().replace('\n', ' ')

                    writer.writerow([info['lieu'], info['prix'], info['details'], description, info['lien']])
                    liens_vus.add(info['lien'])
                    compteur_page += 1
                    print(f"🏠 {info['lieu']} récupéré.")
                    
                    time.sleep(random.uniform(1, 2))

                except Exception:
                    # En cas d'erreur, on revient à la liste pour la suite
                    driver.get(SEARCH_URL.format(page_num))
                    continue
            
            print(f"📊 Page {page_num} terminée : {compteur_page} annonces sauvegardées.")
            
            if compteur_page == 0:
                continuer = False
            else:
                page_num += 1

    print(f"\n✨ Scraping Vizzit terminé ! Fichier : {OUTPUT_PATH}")
    driver.quit()