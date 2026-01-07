import requests
from bs4 import BeautifulSoup
import time
import random
import csv 

base_url = "https://www.paruvendu.fr/immobilier/recherche/location/lyon/?rechpv=1&tt=5&tbApp=1&tbDup=1&tbChb=1&tbLof=1&tbAtl=1&tbPla=1&tbMai=1&tbVil=1&tbCha=1&tbPro=1&tbHot=1&tbMou=1&tbFer=1&nbp0=99&pa=FR&lol=0&ray=50&codeINSEE=69000,&listeCarte=1"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

signatures_deja_vues = []

print("🦁 Lancement du Scraper avec sauvegarde CSV...")

# Nom du fichier mis à jour
with open('annonces_lyon_paruvendu.csv', 'w', newline='', encoding='utf-8-sig') as csvfile:
    writer = csv.writer(csvfile)
    
    # Ajout de la colonne 'Lien'
    writer.writerow(['Titre', 'Prix', 'Lien'])

    # Boucle FOR de 1 à 50 comme dans ton code original
    for page_num in range(1, 50):
        
        if page_num == 1:
            url_page = base_url
        else:
            url_page = f"{base_url}&p={page_num}"
        
        print(f"\n--- 📄 Page {page_num} ---")
        
        try:
            response = requests.get(url_page, headers=headers, timeout=10)
        except Exception as e:
            print(f"❌ Erreur connexion : {e}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        annonces = soup.find_all("article", class_="blocAnnonce")
        
        if len(annonces) == 0:
            print("❌ Aucune annonce trouvée (page vide).")
            break

        # Sécurité anti-boucle (Ton code original)
        premier_titre = annonces[0].find("a", class_="popinphoto_liste_titre")
        signature_actuelle = premier_titre.text.strip() if premier_titre else "inconnu"

        if signature_actuelle in signatures_deja_vues:
            print("🛑 STOP : On tourne en rond (retour page 1 détecté).")
            break
        
        signatures_deja_vues.append(signature_actuelle)
        
        compteur = 0
        for annonce in annonces:
            # On récupère les éléments
            titre_element = annonce.find("a", class_="popinphoto_liste_titre")
            prix_element = annonce.find("div", class_="popinphoto_liste_prix")

            if titre_element and prix_element:
                titre = " ".join(titre_element.text.split())
                prix = prix_element.text.strip()
                
                # --- RECUPERATION DU LIEN ---
                # Le lien est dans l'attribut href de la balise titre_element
                lien_partiel = titre_element.get('href')
                if lien_partiel:
                    lien_complet = f"https://www.paruvendu.fr{lien_partiel}"
                else:
                    lien_complet = "Pas de lien"
                
                # Affichage console
                print(f"🏠 {titre} -- 💰 {prix}")
                
                # Ecriture avec le lien
                writer.writerow([titre, prix, lien_complet])
                
                compteur += 1
                
        print(f"✅ {compteur} annonces sauvegardées sur cette page.")
        
        time.sleep(random.uniform(1, 3))

print("👋 Fin du travail. Le fichier 'annonces_lyon_paruvendu.csv' est prêt !")