import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import csv
import re
import os

# Configuration des chemins et URL
OUTPUT_PATH = "backend/data/annonces_lyon_orpi.csv"
# On prépare l'URL pour la pagination (Orpi utilise souvent un paramètre de tri ou de recherche)
base_url = "https://www.orpi.com/recherche/rent?transaction=rent&locations%5B0%5D%5Bvalue%5D=lyon&sort=date-down&layoutType=list&page={}"

if __name__ == '__main__':
    
    print("🥷 Lancement du mode 'Ascenseur' Automatique pour ORPI...")
    
    # Création du dossier de destination s'il n'existe pas
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    options = uc.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    # Utilisation de ta version spécifique de Chrome
    driver = uc.Chrome(options=options, version_main=144)

    liens_vus = set()

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Titre_Lieu', 'Prix', 'Infos', 'Lien'])

        page_num = 1
        continuer = True

        while continuer:
            url = base_url.format(page_num)
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")
            driver.get(url)

            # --- DÉTECTION AUTOMATIQUE (Cookies) ---
            if page_num == 1:
                print("⏳ En attente de la validation des cookies sur Orpi...")
                try:
                    # On attend que les cartes d'annonces soient présentes
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article.c-overlay"))
                    )
                    print("✅ Accès détecté.")
                except Exception:
                    print("❌ Temps d'attente dépassé ou structure de page différente.")
                    break
            else:
                time.sleep(random.uniform(3, 6))

            # --- DÉFILEMENT ---
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # --- RÉCUPÉRATION DES ANNONCES ---
            # Le sélecteur 'article' avec la classe c-overlay est courant chez Orpi
            annonces = driver.find_elements(By.CSS_SELECTOR, "article.c-overlay")
            
            if not annonces:
                print("🛑 Aucune annonce trouvée sur cette page.")
                break

            compteur_nouveaux = 0
            for annonce in annonces:
                try:
                    # Extraction du lien pour l'unicité
                    try:
                        lien_elem = annonce.find_element(By.TAG_NAME, "a")
                        href = lien_elem.get_attribute("href")
                    except:
                        continue

                    if href in liens_vus:
                        continue

                    # Texte brut de l'annonce pour le traitement
                    clean_text = annonce.text.replace('\n', ' ').strip()
                    
                    # 1. PRIX (Regex pour chercher les chiffres + €)
                    prix = "N/C"
                    match = re.search(r'(\d[\d\s]*€)', clean_text)
                    if match:
                        prix = match.group(1).strip()
                    
                    # 2. TITRE & INFOS
                    # On simplifie pour rester sur un code lisible
                    reste = clean_text.replace(prix, "").strip()
                    titre = reste[:100] # Les 100 premiers caractères
                    infos = reste[100:] # Le reste
                    
                    if prix != "N/C":
                        writer.writerow([titre, prix, infos, href])
                        liens_vus.add(href)
                        compteur_nouveaux += 1
                        print(f"🏠 {titre[:50]}... -- 💰 {prix}")

                except Exception:
                    continue

            print(f"📊 Page {page_num} terminée : {compteur_nouveaux} annonces ajoutées.")

            # Condition d'arrêt
            if compteur_nouveaux == 0:
                print("🏁 Fin des nouvelles annonces.")
                continuer = False
            else:
                page_num += 1

    print(f"\n✨ Terminé ! Fichier sauvegardé dans : {OUTPUT_PATH}")
    driver.quit()