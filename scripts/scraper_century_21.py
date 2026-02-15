import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import csv
import os

# Configuration des chemins et URL
OUTPUT_PATH = "backend/data/annonces_lyon_century21.csv"
base_url = "https://www.century21.fr/annonces/f/location-maison-appartement/v-lyon/page-{}/"

if __name__ == '__main__':
    
    print("🥷 Lancement du mode Furtif Automatique pour Century 21...")
    
    # Création du dossier de destination s'il n'existe pas
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    options = uc.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    # Utilisation de ta version spécifique de Chrome
    driver = uc.Chrome(options=options, version_main=144)

    liens_vus = set()

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Titre', 'Prix', 'Lieu_Surface', 'Lien'])

        page_num = 1
        continuer = True

        while continuer:
            url = base_url.format(page_num)
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")
            driver.get(url)

            # --- DÉTECTION AUTOMATIQUE (Cookies) ---
            if page_num == 1:
                print("⏳ En attente de la validation des cookies sur le navigateur...")
                try:
                    # Attend que les annonces soient présentes (signe que les cookies sont validés)
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='c-the-property-thumbnail-with-content']"))
                    )
                    print("✅ Validation détectée, démarrage du scraping.")
                except Exception:
                    print("❌ Temps d'attente dépassé. Assure-toi de valider les cookies.")
                    break
            else:
                time.sleep(random.uniform(2, 4))

            # --- DÉFILEMENT ---
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

            # --- RÉCUPÉRATION DES ANNONCES ---
            annonces = driver.find_elements(By.CSS_SELECTOR, "div[class*='c-the-property-thumbnail-with-content']")
            
            if not annonces:
                print("🛑 Aucun bloc trouvé. Fin de la recherche.")
                break

            compteur_nouveaux = 0
            for annonce in annonces:
                try:
                    # On vérifie le lien pour éviter les doublons
                    lien_elem = annonce.find_element(By.TAG_NAME, "a")
                    lien = lien_elem.get_attribute("href")

                    if lien in liens_vus:
                        continue
                    
                    try:
                        titre = annonce.find_element(By.CSS_SELECTOR, "[class*='c-text-theme-heading-3']").text.strip()
                        prix_brut = annonce.find_element(By.CSS_SELECTOR, "[class*='c-text-theme-heading-1']").text
                        prix = prix_brut.replace('\n', ' ').strip()
                        infos = annonce.find_element(By.CSS_SELECTOR, "[class*='c-text-theme-heading-4']").text.replace('\n', ' ').strip()
                        
                        writer.writerow([titre, prix, infos, lien])
                        liens_vus.add(lien)
                        compteur_nouveaux += 1
                        print(f"🏠 {titre} - {prix}")
                    except:
                        continue
                except:
                    continue

            print(f"📊 Page {page_num} terminée : {compteur_nouveaux} annonces ajoutées.")

            # Si on ne trouve plus rien de nouveau sur une page, on s'arrête
            if compteur_nouveaux == 0:
                print("🏁 Fin des nouvelles annonces.")
                continuer = False
            else:
                page_num += 1

    print(f"\n✨ Travail terminé ! Fichier créé dans : {OUTPUT_PATH}")
    driver.quit()