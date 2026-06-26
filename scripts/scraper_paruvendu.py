import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(script_dir, '..', 'backend', 'data', 'annonces_lyon_paruvendu.csv')
base_url = "https://www.paruvendu.fr/immobilier/recherche/location/lyon/?rechpv=1&tt=5&tbApp=1&tbDup=1&tbChb=1&tbLof=1&tbAtl=1&tbPla=1&tbMai=1&tbVil=1&tbCha=1&tbPro=1&tbHot=1&tbMou=1&tbFer=1&nbp0=99&pa=FR&lol=0&ray=50&codeINSEE=69000,"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# Sélecteurs avec fallbacks ordonnés par stabilité
CARD_SELECTORS = [
    ("article", {"class": "blocAnnonce"}),
    ("article", {"class_": lambda c: c and "annonce" in c.lower()}),
    ("div", {"class": "annonce"}),
    ("li", {"class_": lambda c: c and "annonce" in c.lower()}),
]
TITRE_SELECTORS = [
    ("a", {"class": "popinphoto_liste_titre"}),
    ("a", {"class_": lambda c: c and "titre" in c.lower()}),
    ("h2", {}),
    ("h3", {}),
]
PRIX_SELECTORS = [
    ("div", {"class": "popinphoto_liste_prix"}),
    ("span", {"class_": lambda c: c and "prix" in c.lower()}),
    ("div", {"class_": lambda c: c and "prix" in c.lower()}),
    ("span", {"class_": lambda c: c and "price" in c.lower()}),
]

def find_bs4(soup_elem, selectors):
    for tag, attrs in selectors:
        try:
            found = soup_elem.find(tag, attrs)
            if found:
                return found
        except Exception:
            continue
    return None

if __name__ == '__main__':
    print("🦁 Lancement du Scraper ParuVendu (Mode Rapide)...")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    liens_vus = set()
    page_num = 1
    continuer = True

    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Titre', 'Prix', 'Lien'])

        while continuer:
            url_page = base_url if page_num == 1 else f"{base_url}&p={page_num}"
            print(f"\n--- 📄 Analyse de la Page {page_num} ---")

            try:
                response = requests.get(url_page, headers=headers, timeout=15)
                if response.status_code != 200:
                    print(f"🛑 Erreur de réponse : {response.status_code}")
                    break
            except Exception as e:
                print(f"❌ Erreur connexion : {e}")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # Essai des sélecteurs de carte dans l'ordre
            annonces = []
            for tag, attrs in CARD_SELECTORS:
                annonces = soup.find_all(tag, attrs)
                if annonces:
                    break

            if not annonces:
                print("❌ Aucune annonce trouvée (fin des résultats).")
                break

            compteur_page = 0
            for annonce in annonces:
                try:
                    titre_elem = find_bs4(annonce, TITRE_SELECTORS)
                    prix_elem = find_bs4(annonce, PRIX_SELECTORS)

                    if not titre_elem:
                        continue

                    titre = " ".join(titre_elem.text.split())
                    prix = prix_elem.text.strip() if prix_elem else "N/C"
                    lien_partiel = titre_elem.get('href') if titre_elem.name == 'a' else None
                    lien = f"https://www.paruvendu.fr{lien_partiel}" if lien_partiel else "Pas de lien"

                    if lien in liens_vus or lien == "Pas de lien":
                        continue

                    writer.writerow([titre, prix, lien])
                    liens_vus.add(lien)
                    compteur_page += 1
                    print(f"🏠 {titre} -- 💰 {prix}")

                except Exception:
                    continue

            print(f"✅ Page {page_num} terminée : {compteur_page} annonces ajoutées.")

            if compteur_page == 0:
                print("🏁 Plus de nouvelles annonces disponibles.")
                continuer = False
            else:
                page_num += 1
                time.sleep(random.uniform(1.5, 3))

    print(f"\n✨ Terminé ! Total : {len(liens_vus)} annonces sauvegardées dans {OUTPUT_PATH}")
