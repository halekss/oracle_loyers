import requests
import pandas as pd
import time

# 1. Vos données brutes
# Je sépare l'adresse et le nom pour faciliter la recherche
lieux = [
    {"adresse": "17 Rue Docteur Bouchut", "nom": "Passage du Désir"},
    {"adresse": "16 Rue Constantine", "nom": "espaceplaisir"},
    {"adresse": "17 Rue René Leynaud", "nom": "Love Shop (Dé)boutonné(e)s"},
    {"adresse": "15 Rue Tupin", "nom": "espaceplaisir"},
    {"adresse": "27 Rue Lanterne", "nom": "La Lanterne Loveshop"}
]

def geocode_adresse(adresse, ville="Lyon"):
    """
    Interroge l'API Adresse de data.gouv.fr
    """
    url = "https://api-adresse.data.gouv.fr/search/"
    # On construit la requête : Adresse + Ville pour préciser
    query = f"{adresse} {ville}"
    
    params = {
        "q": query,
        "limit": 1 # On veut juste le meilleur résultat
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['features']:
                # L'API renvoie du GeoJSON [longitude, latitude]
                coords = data['features'][0]['geometry']['coordinates']
                score = data['features'][0]['properties']['score']
                
                # On inverse pour avoir le format classique (Lat, Lon)
                return {
                    "latitude": coords[1],
                    "longitude": coords[0],
                    "score_confiance": score
                }
    except Exception as e:
        print(f"Erreur pour {adresse}: {e}")
    
    return None

# 2. Exécution
resultats = []
print("🚀 Récupération des coordonnées...")

for lieu in lieux:
    geo = geocode_adresse(lieu["adresse"])
    
    if geo:
        print(f"✅ Trouvé : {lieu['nom']}")
        item = {
            "Nom": lieu["nom"],
            "Adresse": lieu["adresse"],
            "Latitude": geo["latitude"],
            "Longitude": geo["longitude"],
            "Score": geo["score_confiance"]
        }
        resultats.append(item)
    else:
        print(f"❌ Non trouvé : {lieu['adresse']}")
    
    # Petite pause pour être poli avec l'API
    time.sleep(0.2)

# 3. Affichage et Export
df = pd.DataFrame(resultats)

print("\n--- RÉSULTATS ---")
print(df[['Nom', 'Latitude', 'Longitude']])

# Si vous voulez un CSV pour Fusionner avec vos autres données
# df.to_csv("coordonnees_sexshops_lyon.csv", index=False)