import requests as r
import pandas as pd
import time
import os

def get_cavaliers_data(city_name="Lyon"):
    """
    Récupère la liste complète des lieux pour chaque catégorie
    et fusionne avec le fichier existant sans écraser les données précédentes.
    """
    
    # 1. Définition des tags
    tags_cavaliers = {
        # --- VICE ---
        "Vice - Kebab": ("cuisine", "kebab"),
        "Vice - Bar": ("amenity", "bar"),
        "Vice - Tabac": ("shop", "tobacco"),
        "Vice - Sex-shop": ("shop", "adult"), 
        "Vice - Casino": ("amenity", "casino"),
        "Vice - CBD Shop": ("shop", "cannabis"), 
        
        # --- GENTRIFICATION ---
        "Gentrification - Bio": ("shop", "organic"),
        "Gentrification - Salle Sport": ("leisure", "fitness_centre"),
        "Gentrification - Yoga": ("sport", "yoga"),
        "Gentrification - Crèche": ("amenity", "childcare"),
        "Gentrification - Épicerie Fine": ("shop", "deli"),
        "Gentrification - Torréfacteur": ("shop", "coffee"),
        "Gentrification - Atelier Vélo": ("shop", "bicycle"), 
        "Gentrification - Fleuriste": ("shop", "florist"),    
        
        # --- NUISANCE ---
        "Nuisance - École": ("amenity", "school"),
        "Nuisance - Aire de jeux": ("leisure", "playground"),
        "Nuisance - Salle de Concert": ("amenity", "music_venue"),
        "Nuisance - Discothèque": ("amenity", "nightclub"),
        "Nuisance - Station Service": ("amenity", "fuel"),    
        
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
    
    # --- BOUCLE D'EXTRACTION ---
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
                reponse = r.get(url, params={'data': query}, headers={'User-Agent': 'OracleLoyers/Extracteur'}, timeout=190)
                
                if reponse.status_code == 200:
                    data = reponse.json().get('elements', [])
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
                
                elif reponse.status_code == 429:
                    print(f"⚠️ (429)", end=" ")
                    time.sleep(2)
                elif reponse.status_code == 504:
                    print(f"⚠️ (504)", end=" ")
            
            except Exception as e:
                print(f"⚠️ (Err)", end=" ")

        if not success:
            print("❌ ÉCHEC.")

    # --- GESTION DU CHEMIN ET EXPORT ---
    # Récupération du chemin absolu du script actuel
    dossier_script = os.path.dirname(os.path.abspath(__file__))
    # Remonter d'un niveau pour atteindre le dossier 'backend'
    dossier_backend = os.path.dirname(dossier_script)
    # Cibler le dossier 'data'
    dossier_data = os.path.join(dossier_backend, "data")
    
    # Créer le dossier 'data' s'il n'existe pas encore
    os.makedirs(dossier_data, exist_ok=True)
    
    # Création du chemin complet pour le fichier CSV
    nom_fichier = f"cavaliers_{city_name.lower()}.csv"
    chemin_complet = os.path.join(dossier_data, nom_fichier)
    
    if all_data:
        df_new = pd.DataFrame(all_data)
        
        if os.path.exists(chemin_complet):
            print(f"\n\n📂 Le fichier '{chemin_complet}' existe déjà. Fusion en cours...")
            try:
                df_old = pd.read_csv(chemin_complet)
                
                df_combined = pd.concat([df_old, df_new])
                
                len_before = len(df_combined)
                df_combined.drop_duplicates(subset=['latitude', 'longitude', 'type_osm'], keep='last', inplace=True)
                len_after = len(df_combined)
                
                print(f"♻️ Doublons supprimés : {len_before - len_after}")
                
                df_combined.to_csv(chemin_complet, index=False, encoding='utf-8-sig')
                print(f"🎉 SUCCÈS ! Fichier mis à jour : {len_after} lignes au total dans {chemin_complet}")
                
            except Exception as e:
                print(f"❌ Erreur lors de la fusion : {e}")
                chemin_secours = os.path.join(dossier_data, f"new_{nom_fichier}")
                df_new.to_csv(chemin_secours, index=False, encoding='utf-8-sig')
                print(f"⚠️ Les nouvelles données ont été sauvées dans '{chemin_secours}' par sécurité.")
        else:
            df_new.to_csv(chemin_complet, index=False, encoding='utf-8-sig')
            print(f"\n🎉 SUCCÈS ! Fichier créé : {chemin_complet} ({len(df_new)} lignes)")
            
    else:
        print("\n⚠️ Aucune nouvelle donnée récupérée.")

if __name__ == "__main__":
    get_cavaliers_data("Lyon")