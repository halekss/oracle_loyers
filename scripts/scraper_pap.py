import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import random
import csv

# L'URL de ta recherche PAP
url = "https://www.pap.fr/annonce/locations-appartement-lyon-69-g43590-a-partir-du-2-pieces"

if __name__ == '__main__':
    
    print("🥷 Lancement du mode Furtif pour PAP...")
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)

    print("🌍 Ouverture de PAP.fr...")
    driver.get(url)

    # --- PAUSE HUMAINE ---
    print("\n" + "="*50)
    print("✋ ACTION REQUISE :")
    print("1. Valide les cookies sur la fenêtre Chrome.")
    print("2. Reviens ici.")
    input("👉 Appuie sur la touche [ENTRÉE] pour lancer le défilement et le scraping...")
    print("="*50 + "\n")

    with open('annonces_lyon_pap.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Lieu', 'Prix', 'Détails', 'Lien'])

        # --- AUTO-SCROLL ---
        print("🔄 Début du défilement automatique pour charger toutes les annonces...")
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 4))
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                print("🛑 Bas de page atteint.")
                break
                
            last_height = new_height
            print("   ⬇️ Suite chargée...")
        
        print("✅ Page entièrement chargée. Analyse en cours...")
        time.sleep(2)

        # --- SCRAPING ---
        try:
            annonces = driver.find_elements(By.CSS_SELECTOR, "div[class*='search-list-item']")
            print(f"📊 {len(annonces)} annonces détectées au total.")

            compteur = 0
            for annonce in annonces:
                try:
                    # 1. LIEU
                    try:
                        lieu = annonce.find_element(By.CLASS_NAME, "h1").text.strip()
                    except:
                        lieu = "Lieu Inconnu"

                    # 2. PRIX
                    try:
                        prix = annonce.find_element(By.CLASS_NAME, "item-price").text.strip()
                    except:
                        prix = "N/C"

                    # 3. DETAILS
                    try:
                        details = annonce.find_element(By.CLASS_NAME, "item-tags").text.replace('\n', ' - ')
                    except:
                        details = ""

                    # 4. LIEN
                    try:
                        lien_elem = annonce.find_element(By.TAG_NAME, "a")
                        lien = lien_elem.get_attribute("href")
                    except:
                        lien = "Pas de lien"

                    if lieu == "Lieu Inconnu" and prix == "N/C":
                        continue

                    print(f"🏠 {lieu} | {details} -- 💰 {prix}")
                    writer.writerow([lieu, prix, details, lien])
                    compteur += 1
                    
                except:
                    continue

            print(f"✅ Terminé ! {compteur} annonces sauvegardées.")

        except Exception as e:
            print(f"❌ Erreur lors du scraping : {e}")

    # driver.quit()