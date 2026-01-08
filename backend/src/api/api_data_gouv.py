import requests
import time

def geocode_adresse(adresse):
    """
    Convertit une adresse en coordonnées GPS via l'API Adresse.
    """
    url = "https://api-adresse.data.gouv.fr/search/"
    params = {'q': adresse, 'limit': 1}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['features']:
                coords = data['features'][0]['geometry']['coordinates']
                return coords[1], coords[0] # Renvoie (Lat, Lon)
    except Exception as e:
        print(f"❌ Erreur Geocoding : {e}")
    return None, None

def compter_poi_proche(lat, lon, rayon, cle, valeur):
    """
    Compte les POI en essayant plusieurs serveurs différents (Redondance).
    """
    # LISTE DES SERVEURS DISPONIBLES (Si l'un plante, on tente l'autre)
    serveurs = [
        "https://overpass.openstreetmap.fr/api/interpreter", # Serveur FR (souvent rapide)
        "https://overpass-api.de/api/interpreter",           # Serveur Principal (Allemand)
        "https://overpass.kumi.systems/api/interpreter"      # Serveur de secours
    ]
    
    query = f"""
    [out:json][timeout:60];
    (
      node["{cle}"="{valeur}"](around:{rayon}, {lat}, {lon});
      way["{cle}"="{valeur}"](around:{rayon}, {lat}, {lon});
      relation["{cle}"="{valeur}"](around:{rayon}, {lat}, {lon});
    );
    out body;
    """
    
    headers = {'User-Agent': 'OracleLoyers/1.0 (etudiant_projet_lyon@gmail.com)'}
    
    # On boucle sur chaque serveur de la liste
    for url in serveurs:
        try:
            # print(f"   ...Tentative sur {url}...") # Décommentez pour voir quel serveur est utilisé
            response = requests.get(url, params={'data': query}, headers=headers, timeout=65)
            
            if response.status_code == 200:
                return len(response.json()['elements']) # SUCCÈS !
            
            elif response.status_code == 429:
                print(f"   ⚠️ Serveur surchargé (429). On change de serveur...")
                time.sleep(2)
                continue # On passe au serveur suivant
                
            elif response.status_code == 504:
                print(f"   ⚠️ Timeout (504). On change de serveur...")
                continue
                
        except Exception as e:
            print(f"   ⚠️ Erreur connexion ({e}). On change de serveur...")
            continue
            
    print(f"❌ ÉCHEC TOTAL : Aucun serveur n'a répondu pour '{valeur}'.")
    return 0

# ==========================================
# 🏁 ZONE DE TEST (Oracle des Loyers)
# ==========================================

adresse_test = "7 Rue Puits Gaillot, 69001 Lyon"

print(f"🔍 1. Géocodage de : {adresse_test}")
lat, lon = geocode_adresse(adresse_test)

if lat and lon:
    print(f"📍 Coordonnées : {lat}, {lon}")
    print("-" * 60)
    
    R = 500
    print(f"🔍 2. Lancement de l'Analyse '4 Cavaliers' (Rayon {R}m)...")
    print("⏳ Interrogation multi-serveurs en cours...")

    # --- 1. CAVALIER VICE ---
    nb_kebabs = compter_poi_proche(lat, lon, R, "cuisine", "kebab")
    nb_bars = compter_poi_proche(lat, lon, R, "amenity", "bar")
    nb_tabacs = compter_poi_proche(lat, lon, R, "shop", "tobacco")
    nb_sexshops = compter_poi_proche(lat, lon, R, "shop", "adult")

    # --- 2. CAVALIER GENTRIFICATION ---
    nb_bio = compter_poi_proche(lat, lon, R, "shop", "organic")
    nb_sport = compter_poi_proche(lat, lon, R, "leisure", "fitness_centre")
    nb_yoga = compter_poi_proche(lat, lon, R, "sport", "yoga")
    nb_creches = compter_poi_proche(lat, lon, R, "amenity", "childcare")

    # --- 3. CAVALIER NUISANCE ---
    nb_ecoles = compter_poi_proche(lat, lon, R, "amenity", "school")
    nb_jeux = compter_poi_proche(lat, lon, R, "leisure", "playground")

    # --- 4. CAVALIER SUPERSTITION ---
    nb_funeraire = compter_poi_proche(lat, lon, R, "shop", "funeral_directors")
    nb_cimetieres = compter_poi_proche(lat, lon, R, "landuse", "cemetery")

    # --- AFFICHAGE DU RAPPORT ---
    print(f"\n📊 RAPPORT DE L'ORACLE (Rayon {R}m) :")
    print(f"😈 VICE           : {nb_kebabs} Kebabs | {nb_bars} Bars | {nb_tabacs} Tabacs | {nb_sexshops} Sex-shops")
    print(f"🥑 GENTRIFICATION : {nb_bio} Bio | {nb_sport} Salles Sport | {nb_yoga} Yoga | {nb_creches} Crèches")
    print(f"📢 NUISANCE       : {nb_ecoles} Écoles | {nb_jeux} Aires de jeux")
    print(f"👻 SUPERSTITION   : {nb_funeraire} Pompes Funèbres | {nb_cimetieres} Cimetières")

    # Calculs
    score_bobo = nb_bio + nb_yoga + nb_creches + nb_sport
    score_vice = nb_bars + nb_kebabs + nb_sexshops + nb_tabacs
    score_morbide = nb_funeraire + nb_cimetieres
    
    print("\n🔮 CONCLUSION PRELIMINAIRE :")
    if score_morbide > 0:
        print("   -> 👻 Zone Superstitieuse : Présence de la mort à proximité.")
    
    if score_vice > score_bobo * 1.5:
        print("   -> 🍺 Quartier Populaire/Festif (Risque sonore élevé).")
    elif score_bobo > score_vice:
        print("   -> 🥑 Quartier Gentrifié/Familial (Loyer élevé).")
    else:
        print("   -> ⚖️ Quartier Équilibré (Mixité sociale).")

else:
    print("❌ Adresse introuvable.")