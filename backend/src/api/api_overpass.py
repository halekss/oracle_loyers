import requests
import pandas as pd
import time

def get_cavaliers_data(city_name="Lyon"):
    """
    Récupère la liste complète des lieux (Lat/Lon/Nom) pour chaque catégorie
    en utilisant plusieurs serveurs pour éviter les crashs (504/429).
    """
    
    # 1. Définition des tags (Les 4 Cavaliers)
    tags_cavaliers = {
        # --- VICE ---
        "Vice - Kebab": ("cuisine", "kebab"),
        "Vice - Bar": ("amenity", "bar"),
        "Vice - Tabac": ("shop", "tobacco"),
        "Vice - Sex-shop": ("love", "shop"),
        "Vice - Casino": ("amenity", "casino"),
        
        # --- GENTRIFICATION ---
        "Gentrification - Bio": ("shop", "organic"),
        "Gentrification - Salle Sport": ("leisure", "fitness_centre"),
        "Gentrification - Yoga": ("sport", "yoga"),
        "Gentrification - Crèche": ("amenity", "childcare"),
        "Gentrification - Épicerie Fine": ("shop", "deli"),
        "Gentrification - Torréfacteur": ("shop", "coffee"),
        
        # --- NUISANCE ---
        "Nuisance - École": ("amenity", "school"),
        "Nuisance - Aire de jeux": ("leisure", "playground"),
        "Nuisance - Salle de Concert": ("amenity", "music_venue"),
        "Nuisance - Discothèque": ("amenity", "nightclub"),
        
        # --- SUPERSTITION ---
        "Superstition - Pompes Funèbres": ("shop", "funeral_directors"),
        "Superstition - Cimetière": ("landuse", "cemetery")
    }

    # 2. Liste de serveurs robustes (Ordre de préférence)
    serveurs = [
        "https://overpass-api.de/api/interpreter",       # Serveur Principal (Souvent le plus solide)
        "https://overpass.kumi.systems/api/interpreter", # Serveur de secours très performant
        "https://api.openstreetmap.fr/oapi/interpreter"  # Serveur FR (Celui qui plante actuellement)
    ]

    all_data = []
    print(f"🚀 Démarrage de l'extraction massive pour {city_name}...")
    
    for category, (key, value) in tags_cavaliers.items():
        print(f"\n🔎 Recherche : {category}...", end=" ")
        
        # On augmente le timeout à 180s (3 minutes) pour les grosses requêtes
        query = f"""
        [out:json][timeout:180];
        area["name"="{city_name}"]["admin_level"="8"]->.searchArea;
        (
          node["{key}"="{value}"](area.searchArea);
          way["{key}"="{value}"](area.searchArea);
          relation["{key}"="{value}"](area.searchArea);
        );
        out center tags;
        """
        
        success = False
        
        # Boucle de tentative sur les différents serveurs
        for url in serveurs:
            if success: break # Si on a réussi, on sort de la boucle serveurs
            
            try:
                # print(f"(Tentative sur {url})...", end="") 
                r = requests.get(url, params={'data': query}, headers={'User-Agent': 'OracleLoyers/Extracteur'}, timeout=190)
                
                if r.status_code == 200:
                    data = r.json().get('elements', [])
                    count = 0
                    
                    for item in data:
                        lat, lon = None, None
                        if 'lat' in item:
                            lat, lon = item['lat'], item['lon']
                        elif 'center' in item:
                            lat, lon = item['center']['lat'], item['center']['lon']
                        
                        if lat and lon:
                            name = item.get('tags', {}).get('name', 'Inconnu')
                            all_data.append({
                                'categorie_cavalier': category,
                                'type_osm': value,
                                'nom_lieu': name,
                                'latitude': lat,
                                'longitude': lon
                            })
                            count += 1
                    
                    print(f"✅ {count} lieux trouvés.")
                    success = True
                    time.sleep(1) # Petite pause bien méritée
                
                elif r.status_code == 429:
                    print(f"⚠️ (429 Trop rapide)", end=" ")
                    time.sleep(2)
                
                elif r.status_code == 504:
                    print(f"⚠️ (504 Timeout)", end=" ")
                    # On ne fait rien, la boucle passera au serveur suivant
            
            except Exception as e:
                print(f"⚠️ (Erreur connexion)", end=" ")

        if not success:
            print("❌ ÉCHEC sur tous les serveurs.")

    # Export Final
    if all_data:
        df = pd.DataFrame(all_data)
        filename = f"cavaliers_{city_name.lower()}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n🎉 SUCCÈS ! Fichier généré : {filename} ({len(df)} lignes)")
    else:
        print("\n⚠️ Aucune donnée récupérée. Essayez de relancer dans 5 minutes.")

if __name__ == "__main__":
    get_cavaliers_data("Lyon")