import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import os

# Configuration des chemins et URL
OUTPUT_PATH = "backend/data/annonces_lyon_paruvendu.csv"
base_url = "https://www.paruvendu.fr/immobilier/recherche/location/lyon/?rechpv=1&tt=5&tbApp=1&tbDup=1&tbChb=1&tbLof=1&tbAtl=1&tbPla=1&tbMai=1&tbVil=1&tbCha=1&tbPro=1&tbHot=1&tbMou=1&tbFer=1&nbp0=99&pa=FR&lol=0&ray=50&codeINSEE=69000,"

# Headers pour imiter un navigateur et éviter le blocage
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

if __name__ == '__main__':
    print("🦁 Lancement du Scraper ParuVendu (Mode Rapide)...")
    
    # Création du dossier de destination s'il n'existe pas
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    liens_vus = set()
    page_num = 1
    continuer = True

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Titre', 'Prix', 'Lien'])

        while continuer:
            # Gestion de l'URL pour la pagination
            url_page = base_url if page_num == 1 else f"{base_url}&p={page_num}"
            
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")
            
            try:
                # On utilise r (alias de requests) comme tu l'as spécifié dans tes préférences
                import requests as r
                response = r.get(url_page, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    print(f"🛑 Erreur de réponse : {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"❌ Erreur connexion : {e}")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            annonces = soup.find_all("article", class_="blocAnnonce")
            
            if not annonces:
                print("❌ Aucune annonce trouvée (fin des résultats).")
                break

            compteur_page = 0
            for annonce in annonces:
                try:
                    # Récupération des éléments
                    titre_element = annonce.find("a", class_="popinphoto_liste_titre")
                    prix_element = annonce.find("div", class_="popinphoto_liste_prix")

                    if titre_element and prix_element:
                        # Nettoyage des données
                        titre = " ".join(titre_element.text.split())
                        prix = prix_element.text.strip()
                        
                        # Récupération du lien
                        lien_partiel = titre_element.get('href')
                        lien_complet = f"https://www.paruvendu.fr{lien_partiel}" if lien_partiel else "Pas de lien"
                        
                        # Vérification de l'unicité
                        if lien_complet in liens_vus or lien_complet == "Pas de lien":
                            continue
                        
                        # Écriture
                        writer.writerow([titre, prix, lien_complet])
                        liens_vus.add(lien_complet)
                        compteur_page += 1
                        print(f"🏠 {titre} -- 💰 {prix}")
                        
                except Exception:
                    continue
            
            print(f"✅ Page {page_num} terminée : {compteur_page} annonces ajoutées.")

            # Condition d'arrêt : si on n'a plus de nouvelles annonces sur cette page
            if compteur_page == 0:
                print("🏁 Plus de nouvelles annonces disponibles.")
                continuer = False
            else:
                page_num += 1
                # Petite pause pour être poli avec le serveur
                time.sleep(random.uniform(1.5, 3))

    print(f"\n✨ Terminé ! Total : {len(liens_vus)} annonces sauvegardées dans {OUTPUT_PATH}")