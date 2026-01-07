import requests
import time  # Indispensable pour faire des pauses entre les requêtes

def geocode_adresse(adresse):
    """
    Convertit une adresse postale en coordonnées GPS (Latitude, Longitude)
    [cite_start]via l'API Adresse du gouvernement français[cite: 16].
    """
    url = "https://api-adresse.data.gouv.fr/search/"
    params = {
        'q': adresse,
        'limit': 1
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['features']:
                coords = data['features'][0]['geometry']['coordinates']
                # L'API renvoie [Lon, Lat], on veut (Lat, Lon)
                return coords[1], coords[0]
    except Exception as e:
        print(f"❌ Erreur Geocoding : {e}")
    
    return None, None

def compter_poi_proche(lat, lon, rayon, cle, valeur):
    """
    [cite_start]Interroge l'API Overpass (OpenStreetMap) pour compter des points d'intérêts[cite: 8].
    Gère les erreurs 504 (Timeout) et ajoute une identité (User-Agent).
    """
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # On ajoute [timeout:25] pour dire au serveur qu'on est patient
    query = f"""
    [out:json][timeout:50];
    (
      node["{cle}"="{valeur}"](around:{rayon}, {lat}, {lon});
      way["{cle}"="{valeur}"](around:{rayon}, {lat}, {lon});
    );
    out body;
    """
    
    # Carte de visite obligatoire pour ne pas être bloqué
    headers = {
        'User-Agent': 'OracleLoyers/1.0 (etudiant_data_project@gmail.com)' 
    }
    
    try:
        response = requests.get(overpass_url, params={'data': query}, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return len(data['elements'])
        elif response.status_code == 504:
            print(f"⚠️ Timeout serveur pour '{valeur}' (Le serveur est surchargé)")
            return 0
        elif response.status_code == 429:
            print(f"⚠️ Trop de requêtes (429). Attendez un peu.")
            return 0
        else:
            print(f"⚠️ Erreur HTTP {response.status_code} pour {valeur}")
            return 0
            
    except Exception as e:
        print(f"❌ Erreur connexion Overpass : {e}")
        return 0

# ==========================================
# 🏁 ZONE DE TEST DU SCRIPT
# ==========================================

# Adresse cible (ex: Rue Puits Gaillot à Lyon, vue sur votre capture)
adresse_test = "7 Rue Puits Gaillot, 69001 Lyon"

print(f"🔍 1. Géocodage de l'adresse : {adresse_test}")
lat, lon = geocode_adresse(adresse_test)

if lat and lon:
    print(f"📍 Coordonnées trouvées : {lat}, {lon}")
    print("-" * 40)
    print("🔍 2. Recherche des 4 Cavaliers (avec pauses de sécurité)...")
    
    # --- 1. CAVALIER VICE (Kebab & Sex-shop) ---
    # [cite_start]Kebab (Cuisine = Kebab) [cite: 67]
    nb_kebabs = compter_poi_proche(lat, lon, 600, "cuisine", "kebab")
    time.sleep(2) # Pause de 2 secondes pour éviter l'erreur 504/429
    
    # [cite_start]Sex-shop (Shop = Adult) [cite: 69]
    nb_sexshops = compter_poi_proche(lat, lon, 1000, "shop", "adult")
    time.sleep(2) 

    # --- 2. CAVALIER GENTRIFICATION (Bio) ---
    # [cite_start]Magasin Bio (Shop = Organic) [cite: 63]
    nb_bio = compter_poi_proche(lat, lon, 600, "shop", "organic")
    time.sleep(2)

    # --- 3. CAVALIER SUPERSTITION (Funéraire) ---
    # [cite_start]Pompes Funèbres (Shop = Funeral_directors) [cite: 77]
    nb_funeraire = compter_poi_proche(lat, lon, 1000, "shop", "funeral_directors")

    # --- RÉSULTATS ---
    print("\n📊 RÉSULTATS DE L'ORACLE :")
    print(f"   🥙 Kebabs (300m) : {nb_kebabs}")
    print(f"   🔞 Sex-shops (500m) : {nb_sexshops}")
    print(f"   🥗 Magasins Bio (300m) : {nb_bio}")
    print(f"   ⚰️ Pompes Funèbres (500m) : {nb_funeraire}")
    
    # Petite logique simple pour tester l'analyse
    if nb_kebabs > 2 and nb_sexshops > 0:
        print("\n🔮 Prédiction : Quartier festif ou 'Zone Vice'.")
    elif nb_bio > 1:
        print("\n🔮 Prédiction : Quartier 'Bobo' (Gentrification élevée).")
    else:
        print("\n🔮 Prédiction : Quartier neutre.")

else:
    print("❌ Impossible de trouver les coordonnées de cette adresse.")