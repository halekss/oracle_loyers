import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import random
import csv
import re

# URL de base
base_url = "https://www.orpi.com/recherche/rent?transaction=rent&resultUrl=&realEstateTypes%5B0%5D=maison&realEstateTypes%5B1%5D=appartement&locations%5B0%5D%5Bvalue%5D=lyon&locations%5B0%5D%5Blabel%5D=Lyon&locations%5B0%5D%5Blatitude%5D=45.758&locations%5B0%5D%5Blongitude%5D=4.83494&agency=&minSurface=&maxSurface=&minLotSurface=&maxLotSurface=&minStoryLocation=&maxStoryLocation=&newBuild=&oldBuild=&lifeAnnuity=&minPrice=&maxPrice=&sort=date-down&layoutType=list&recentlySold=false&searchRange="

if __name__ == '__main__':
    
    print("🥷 Lancement du mode 'Ascenseur' pour ORPI...")
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)

    print("🌍 Ouverture d'Orpi...")
    
    with open('annonces_lyon_orpi.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Titre_Lieu', 'Prix', 'Infos', 'Lien'])

        # Boucle sur les pages
        for page_num in range(1, 6):
            
            if page_num == 1:
                url = base_url
            else:
                url = f"{base_url}&page={page_num}"
            
            print(f"\n--- 📄 Chargement Page {page_num} ---")
            driver.get(url)

            # Pause cookies page 1
            if page_num == 1:
                print("\n" + "="*50)
                print("✋ ACTION REQUISE :")
                print("1. Accepte les cookies.")
                print("2. Reviens ici.")
                input("👉 Appuie sur [ENTRÉE] pour démarrer...")
                print("="*50 + "\n")
            else:
                time.sleep(random.uniform(3, 5))

            try:
                # On cible les liens overlays
                overlay_links = driver.find_elements(By.CSS_SELECTOR, "a[class*='c-overlay__link']")
                
                if not overlay_links:
                    print("❌ Pas d'annonces trouvées.")
                    break
                
                print(f"📊 {len(overlay_links)} annonces détectées.")

                compteur = 0
                for link in overlay_links:
                    try:
                        href = link.get_attribute("href")
                        
                        # --- L'ASCENSEUR ---
                        # On commence par l'élément lui-même
                        current_element = link
                        found_text = ""
                        
                        # On monte jusqu'à 5 niveaux maximum pour trouver le conteneur principal
                        for level in range(5):
                            # On récupère le parent
                            current_element = current_element.find_element(By.XPATH, "./..")
                            # On utilise textContent (plus puissant que innerText pour le texte caché)
                            text = current_element.get_attribute("textContent")
                            
                            # Si on trouve un symbole Euro, c'est qu'on est au bon étage !
                            if "€" in text:
                                found_text = text
                                # print(f"   -> Trouvé au niveau {level+1} !") # Debug
                                break
                        
                        # Si après 5 étages on a rien, on passe
                        if not found_text:
                            continue

                        # --- EXTRACTION ---
                        # Nettoyage des sauts de ligne multiples
                        clean_text = re.sub(r'\s+', ' ', found_text).strip()
                        
                        # 1. PRIX (Regex : cherche chiffres + €)
                        prix = "N/C"
                        match = re.search(r'(\d[\d\s]*€)', clean_text)
                        if match:
                            prix = match.group(1).strip()
                        
                        # 2. TITRE & INFOS
                        # On essaie d'être malin : le titre est souvent au début
                        # On enlève le prix du texte pour voir ce qu'il reste
                        reste = clean_text.replace(prix, "")
                        
                        # On coupe pour avoir Titre / Infos
                        # Orpi met souvent : "Appartement Lyon 3e ... détails"
                        # On va tout mettre dans Titre_Lieu pour l'instant, on triera avec Pandas
                        titre = reste.strip()[:100] # On garde les 100 premiers caractères comme titre/lieu
                        infos = reste.strip()[100:] # Le reste en infos

                        if prix == "N/C":
                            continue

                        print(f"🏠 {titre}... -- 💰 {prix}")
                        writer.writerow([titre, prix, infos, href])
                        compteur += 1

                    except Exception as e:
                        continue
                
                print(f"✅ {compteur} annonces sauvegardées.")

            except Exception as e:
                print(f"❌ Erreur page : {e}")

    print("👋 Terminé !")