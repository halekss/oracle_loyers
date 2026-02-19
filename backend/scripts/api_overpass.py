import requests
import pandas as pd
import time
import os

def get_cavaliers_data(city_name="Lyon"):
    """
    Récupère la liste complète des lieux pour chaque catégorie
    et fusionne avec le fichier existant sans écraser les données précédentes.
    """
    
    # 1. Définition des tags (Mise à jour avec vos demandes)
    tags_cavaliers = {
        # --- VICE ---
        "Vice - Kebab": ("cuisine", "kebab"),
        "Vice - Bar": ("amenity", "bar"),
        "Vice - Tabac": ("shop", "tobacco"),
        "Vice - Sex-shop": ("shop", "adult"), # Corrigé (love=shop ne fonctionne pas sur OSM)
        "Vice - Casino": ("amenity", "casino"),
        "Vice - CBD Shop": ("shop", "cannabis"), # <-- AJOUT (Tag standard pour CBD en France)
        
        # --- GENTRIFICATION ---
        "Gentrification - Bio": ("shop", "organic"),
        "Gentrification - Salle Sport": ("leisure", "fitness_centre"),
        "Gentrification - Yoga": ("sport", "yoga"),
        "Gentrification - Crèche": ("amenity", "childcare"),
        "Gentrification - Épicerie Fine": ("shop", "deli"),
        "Gentrification - Torréfacteur": ("shop", "coffee"),
        "Gentrification - Atelier Vélo": ("shop", "bicycle"), # <-- AJOUT
        "Gentrification - Fleuriste": ("shop", "florist"),    # <-- AJOUT
        
        # --- NUISANCE ---
        "Nuisance - École": ("amenity", "school"),
        "Nuisance - Aire de jeux": ("leisure", "playground"),
        "Nuisance - Salle de Concert": ("amenity", "music_venue"),
        "Nuisance - Discothèque": ("amenity", "nightclub"),
        "Nuisance - Station Service": ("amenity", "fuel"),    # <-- AJOUT
        
        # --- SUPERSTITION ---
        "Superstition - Pompes Funèbres": ("shop", "funeral_directors"),
        "Superstition - Cimetière": ("landuse", "cemetery")
    }

    # 2. Liste de serveurs robustes
    serveurs = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://api.openstreetmap.fr/oapi/interpreter"
    ]

    all_data = []
    print(f"🚀 Démarrage de l'extraction massive pour {city_name}...")
    
    # --- BOUCLE D'EXTRACTION (inchangée) ---
    for category, (key, value) in tags_cavaliers.items():
        print(f"\n🔎 Recherche : {category}...", end=" ")
        
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
        
        for url in serveurs:
            if success: break
            
            try:
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
                    
                    print(f"✅ {count} lieux trouvés.", end="")
                    success = True
                    time.sleep(1)
                
                elif r.status_code == 429:
                    print(f"⚠️ (429)", end=" ")
                    time.sleep(2)
                elif r.status_code == 504:
                    print(f"⚠️ (504)", end=" ")
            
            except Exception as e:
                print(f"⚠️ (Err)", end=" ")

        if not success:
            print("❌ ÉCHEC.")

    # --- FUSION ET EXPORT ---
    filename = f"cavaliers_{city_name.lower()}.csv"
    
    if all_data:
        # 1. Création du DataFrame avec les nouvelles données
        df_new = pd.DataFrame(all_data)
        
        # 2. Vérification si le fichier existe déjà
        if os.path.exists(filename):
            print(f"\n\n📂 Le fichier '{filename}' existe déjà. Fusion en cours...")
            try:
                df_old = pd.read_csv(filename)
                
                # 3. Concaténation (Ancien + Nouveau)
                df_combined = pd.concat([df_old, df_new])
                
                # 4. Suppression des doublons
                # On considère un doublon si Latitude + Longitude + Catégorie sont identiques
                # On garde 'last' (la nouvelle version) au cas où le nom a changé
                len_before = len(df_combined)
                df_combined.drop_duplicates(subset=['latitude', 'longitude', 'type_osm'], keep='last', inplace=True)
                len_after = len(df_combined)
                
                print(f"♻️ Doublons supprimés : {len_before - len_after}")
                
                # Sauvegarde
                df_combined.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"🎉 SUCCÈS ! Fichier mis à jour : {len_after} lignes au total.")
                
            except Exception as e:
                print(f"❌ Erreur lors de la fusion : {e}")
                # Sauvegarde de secours si la fusion plante
                df_new.to_csv(f"new_{filename}", index=False, encoding='utf-8-sig')
                print(f"⚠️ Les nouvelles données ont été sauvées dans 'new_{filename}' par sécurité.")
        else:
            # Si le fichier n'existe pas, on le crée simplement
            df_new.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n🎉 SUCCÈS ! Fichier créé : {filename} ({len(df_new)} lignes)")
            
    else:
        print("\n⚠️ Aucune nouvelle donnée récupérée.")

if __name__ == "__main__":
    get_cavaliers_data("Lyon")