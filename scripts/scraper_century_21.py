import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import random
import csv

# URL de ta recherche Century 21 (Lyon)
url = "https://www.century21.fr/annonces/f/location-maison-appartement/v-lyon/"

if __name__ == '__main__':
    
    print("🥷 Lancement du mode Furtif pour Century 21...")
    
    options = uc.ChromeOptions()
    # On ajoute une option pour ignorer les erreurs de certificats qui arrivent parfois
    options.add_argument('--ignore-certificate-errors')
    driver = uc.Chrome(options=options)

    print("🌍 Ouverture du site...")
    driver.get(url)

    # --- PAUSE HUMAINE (Cookies) ---
    print("\n" + "="*50)
    print("✋ ACTION REQUISE :")
    print("1. Valide les cookies sur la fenêtre Chrome.")
    print("2. Reviens ici.")
    input("👉 Appuie sur la touche [ENTRÉE] pour lancer le défilement et le scraping...")
    print("="*50 + "\n")

    with open('annonces_lyon_century21.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Titre', 'Prix', 'Lieu_Surface', 'Lien'])

        # --- AUTO-SCROLL ---
        print("🔄 Début du défilement automatique...")
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 4))
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                print("🛑 Bas de page atteint.")
                break
            last_height = new_height
            print("   ⬇️ Chargement de la suite...")
        
        print("✅ Page chargée. Analyse des données...")
        time.sleep(2)

        # --- SCRAPING ---
        try:
            # On cible le conteneur global de chaque annonce
            # Basé sur ton image image_1a960c.png, le bloc contient "c-the-property-thumbnail-with-content"
            annonces = driver.find_elements(By.CSS_SELECTOR, "div[class*='c-the-property-thumbnail-with-content']")
            
            print(f"📊 {len(annonces)} annonces détectées.")

            compteur = 0
            for annonce in annonces:
                try:
                    # 1. TITRE (ex: "Appartement F1 à louer")
                    # Basé sur image_1a9951.png -> c-text-theme-heading-3
                    try:
                        titre = annonce.find_element(By.CSS_SELECTOR, "[class*='c-text-theme-heading-3']").text.strip()
                    except:
                        titre = "Titre Inconnu"

                    # 2. PRIX
                    # Basé sur image_1a998e.png -> c-text-theme-heading-1
                    try:
                        # On nettoie le texte pour virer les "par mois..." si besoin
                        prix_brut = annonce.find_element(By.CSS_SELECTOR, "[class*='c-text-theme-heading-1']").text
                        prix = prix_brut.replace('\n', ' ').strip()
                    except:
                        prix = "N/C"

                    # 3. LIEU & SURFACE
                    # Basé sur image_1a990a.png -> c-text-theme-heading-4
                    try:
                        infos = annonce.find_element(By.CSS_SELECTOR, "[class*='c-text-theme-heading-4']").text.replace('\n', ' ').strip()
                    except:
                        infos = ""

                    # 4. LIEN
                    # Le lien est généralement sur le titre ou un bouton "Voir le détail"
                    try:
                        lien_elem = annonce.find_element(By.TAG_NAME, "a")
                        lien = lien_elem.get_attribute("href")
                    except:
                        lien = "Pas de lien"

                    # --- FILTRE & DEBUG ---
                    # Parfois Century 21 met des blocs "Vendu" ou des pubs qui n'ont pas de prix
                    if prix == "N/C" and titre == "Titre Inconnu":
                        continue

                    print(f"🏠 {titre} | {infos} -- 💰 {prix}")
                    writer.writerow([titre, prix, infos, lien])
                    compteur += 1

                except Exception as e:
                    # Si une annonce spécifique pose problème, on l'ignore
                    continue

            print(f"✅ Terminé ! {compteur} annonces sauvegardées.")

        except Exception as e:
            print(f"❌ Erreur lors du scraping : {e}")

    # driver.quit() # Décommente si tu veux fermer automatiquement