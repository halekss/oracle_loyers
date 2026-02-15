import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import csv
import os

# Configuration des chemins et URL
OUTPUT_PATH = "backend/data/annonces_lyon_seloger.csv"
base_url = "https://www.seloger.com/classified-search?distributionTypes=Rent&estateTypes=House,Apartment&locations=AD08FR28808"

if __name__ == '__main__':
    
    print("🥷 Lancement du mode Furtif Automatique pour SeLoger...")
    
    # Création du dossier de destination s'il n'existe pas
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    options = uc.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    # Utilisation de ta version spécifique de Chrome
    driver = uc.Chrome(options=options, version_main=144)

    liens_vus = set()

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Titre', 'Prix', 'Lieu', 'Infos', 'Lien'])

        page_num = 1
        continuer = True

        while continuer:
            # Gestion de l'URL pour la pagination
            url = base_url if page_num == 1 else f"{base_url}&page={page_num}"
            
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")
            driver.get(url)

            # --- DÉTECTION DU CAPTCHA / COOKIES ---
            if page_num == 1:
                print("⏳ En attente de la validation du Captcha ou des Cookies...")
                try:
                    # On attend que le lien d'une annonce apparaisse (preuve que le Captcha est passé)
                    WebDriverWait(driver, 120).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='card-mfe-covering-link-testid']"))
                    )
                    print("✅ Page accessible détectée.")
                except Exception:
                    print("❌ Temps d'attente dépassé (Captcha non résolu ?).")
                    break
            else:
                # Pause plus longue pour SeLoger (très sensible)
                time.sleep(random.uniform(5, 8))

            # --- RÉCUPÉRATION DES ANNONCES ---
            try:
                # On utilise l'attribut data-testid qui est le plus stable sur SeLoger
                annonces = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='card-mfe-covering-link-testid']")
                
                if not annonces:
                    print("🛑 Aucune annonce trouvée sur cette page.")
                    break

                compteur_page = 0
                for annonce in annonces:
                    try:
                        # 1. LIEN
                        lien = annonce.get_attribute("href")
                        
                        if not lien or lien in liens_vus:
                            continue

                        # 2. EXTRACTION VIA L'ATTRIBUT TITLE
                        # Le format de SeLoger dans "title" est souvent : "Type - Lieu - Prix - Infos"
                        full_title = annonce.get_attribute("title")
                        
                        if not full_title:
                            continue

                        parts = full_title.split(' - ')
                        
                        # Découpage intelligent
                        titre = parts[0].strip() if len(parts) > 0 else "Inconnu"
                        lieu = parts[1].strip() if len(parts) > 1 else "Lyon"
                        
                        # Recherche du prix (cherche le symbole €)
                        prix = "N/C"
                        infos_liste = []
                        for p in parts[2:]:
                            if "€" in p:
                                prix = p.strip()
                            else:
                                infos_liste.append(p.strip())
                        
                        infos = " - ".join(infos_liste)

                        # Sauvegarde
                        writer.writerow([titre, prix, lieu, infos, lien])
                        liens_vus.add(lien)
                        compteur_page += 1
                        print(f"🏠 {titre} ({lieu}) -- 💰 {prix}")

                    except Exception:
                        continue
                
                print(f"📊 Page {page_num} terminée : {compteur_page} nouvelles annonces.")

                # Condition d'arrêt
                if compteur_page == 0:
                    print("🏁 Plus de nouvelles annonces uniques.")
                    continuer = False
                else:
                    page_num += 1
                    
            except Exception as e:
                print(f"❌ Erreur critique sur la page : {e}")
                break

    print(f"\n✨ Scraping SeLoger terminé ! Fichier : {OUTPUT_PATH}")
    driver.quit()