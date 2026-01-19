import requests
import pandas as pd
import time
import os

# 1. Vos données manuelles
lieux_a_ajouter = [
    {"adresse": "17 Rue Docteur Bouchut", "nom": "Passage du Désir"},
    {"adresse": "16 Rue Constantine", "nom": "espaceplaisir"},
    {"adresse": "17 Rue René Leynaud", "nom": "Love Shop (Dé)boutonné(e)s"},
    {"adresse": "15 Rue Tupin", "nom": "espaceplaisir"},
    {"adresse": "27 Rue Lanterne", "nom": "La Lanterne Loveshop"}
]

FILENAME = "cavaliers_lyon.csv"  # Le nom de votre fichier existant

def geocode_adresse(adresse, ville="Lyon"):
    url = "https://api-adresse.data.gouv.fr/search/"
    params = {"q": f"{adresse} {ville}", "limit": 1}
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200 and r.json()['features']:
            coords = r.json()['features'][0]['geometry']['coordinates']
            return coords[1], coords[0] # (Lat, Lon)
    except Exception:
        pass
    return None, None

# 2. Récupération des coordonnées
nouveaux_items = []
print("🚀 Géocodage en cours...")

for lieu in lieux_a_ajouter:
    lat, lon = geocode_adresse(lieu["adresse"])
    
    if lat and lon:
        item = {
            "categorie_cavalier": "Vice - Sex-shop",
            "type_osm": "manual_add",
            "nom_lieu": lieu["nom"],
            "latitude": lat,
            "longitude": lon
        }
        nouveaux_items.append(item)
        print(f"✅ Ajouté : {lieu['nom']}")
    else:
        print(f"❌ Échec : {lieu['nom']}")
    time.sleep(0.2)

# 3. Fusion et Sauvegarde (Format CSV)
if nouveaux_items:
    df_nouveaux = pd.DataFrame(nouveaux_items)
    
    if os.path.exists(FILENAME):
        # Si le fichier existe, on le charge
        print(f"\n📂 Chargement de '{FILENAME}'...")
        df_existant = pd.read_csv(FILENAME)
        
        # On ajoute les nouveaux (concaténation)
        df_final = pd.concat([df_existant, df_nouveaux], ignore_index=True)
    else:
        # Sinon on crée un nouveau
        df_final = df_nouveaux

    # On sauvegarde en écrasant l'ancien
    df_final.to_csv(FILENAME, index=False, encoding='utf-8-sig')
    print(f"🎉 Terminé ! Fichier mis à jour avec {len(df_final)} lignes au total.")
else:
    print("Aucune donnée à ajouter.")