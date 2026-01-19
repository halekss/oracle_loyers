import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import random
import csv
import re

# URL de base (Page 1)
base_url = "https://www.seloger.com/classified-search?distributionTypes=Rent&estateTypes=House,Apartment&locations=AD08FR28808"

if __name__ == '__main__':
    
    print("🥷 Lancement du mode Furtif pour SeLoger...")
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)

    print("🌍 Ouverture de SeLoger...")
    
    with open('annonces_lyon_seloger.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Titre', 'Prix', 'Lieu', 'Infos', 'Lien'])

        # On tente de scraper les 3 premières pages
        for page_num in range(1, 10):
            
            # Gestion de l'URL
            if page_num == 1:
                url = base_url
            else:
                url = f"{base_url}&page={page_num}"
            
            print(f"\n--- 📄 Chargement Page {page_num} ---")
            driver.get(url)

            # --- PAUSE HUMAINE (Page 1) ---
            if page_num == 1:
                print("\n" + "="*50)
                print("✋ ACTION REQUISE :")
                print("1. Résous le Captcha (Datadome) si présent.")
                print("2. Accepte les cookies.")
                print("3. Reviens ici.")
                input("👉 Appuie sur [ENTRÉE] une fois la liste affichée...")
                print("="*50 + "\n")
            else:
                time.sleep(random.uniform(4, 7))

            try:
                # --- CIBLAGE VIA DATA-TESTID ---
                # On utilise l'attribut solide vu sur ta capture
                annonces = driver.find_elements(By.CSS_SELECTOR, "a[data-testid='card-mfe-covering-link-testid']")
                
                if not annonces:
                    print("❌ Pas d'annonces trouvées (Captcha probable ?).")
                    break
                
                print(f"📊 {len(annonces)} annonces détectées.")

                compteur = 0
                for annonce in annonces:
                    try:
                        # 1. LIEN
                        lien = annonce.get_attribute("href")
                        
                        # 2. TOUT EST DANS LE TITRE !
                        # Format attendu : "Type - Lieu - Prix - Infos"
                        full_title = annonce.get_attribute("title")
                        
                        if not full_title:
                            continue

                        # On découpe le titre en morceaux en utilisant le séparateur " - "
                        parts = full_title.split(' - ')
                        
                        # Initialisation par défaut
                        titre = parts[0].strip() # "Appartement à louer"
                        lieu = "Inconnu"
                        prix = "N/C"
                        infos = ""

                        # On essaie de remplir intelligemment selon le nombre de morceaux
                        if len(parts) >= 3:
                            lieu = parts[1].strip() # "Lyon 7ème"
                            
                            # Le prix est souvent en 3ème position, on vérifie s'il y a un "€"
                            partie_3 = parts[2].strip()
                            if "€" in partie_3:
                                prix = partie_3
                                # Le reste, c'est les détails (Surface, Pièces...)
                                if len(parts) > 3:
                                    infos = " - ".join(parts[3:])
                            else:
                                # Parfois l'ordre change, on cherche le morceau avec "€"
                                for p in parts:
                                    if "€" in p:
                                        prix = p.strip()
                                    elif p != titre and p != lieu:
                                        infos += p + " "
                        
                        else:
                            # Si le format est bizarre, on met tout dans infos
                            infos = full_title

                        print(f"🏠 {titre} ({lieu}) -- 💰 {prix}")
                        writer.writerow([titre, prix, lieu, infos, lien])
                        compteur += 1

                    except Exception as e:
                        # print(f"Bug sur une annonce : {e}")
                        continue
                
                print(f"✅ {compteur} annonces sauvegardées sur cette page.")

            except Exception as e:
                print(f"❌ Erreur globale sur la page : {e}")

    print("👋 Scraping SeLoger terminé !")