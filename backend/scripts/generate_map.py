import folium
import pandas as pd
import os
import random
import json

# --- 1. CONFIGURATION DES CHEMINS (Adaptée pour Docker/Airflow) ---
# On définit les bases par rapport à l'emplacement du script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Dans Docker Airflow, ce sera /opt/airflow/backend
BACKEND_DIR = SCRIPT_DIR 
DATA_DIR = os.path.join(BACKEND_DIR, 'data')

# On remonte d'un niveau pour trouver le frontend
# En local : ORACLE_LOYERS/frontend
# Dans Docker : /opt/airflow/frontend
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'public', 'data')
OUTPUT_HTML = os.path.join(FRONTEND_DATA_DIR, 'map_pings_lyon_calques.html')

IMMO_CSV = os.path.join(DATA_DIR, 'master_immo_final.csv')
POI_CSV = os.path.join(DATA_DIR, 'cavaliers_lyon.csv')
METRO_JSON = os.path.join(DATA_DIR, 'metro_lyon.json')

def main():
    print("🛑 DEBUT GENERATION CARTE...")
    print(f"📂 Lecture des données dans : {DATA_DIR}")
    print(f"🎯 Cible de sortie : {OUTPUT_HTML}")

    # --- 2. CONFIGURATION COULEURS & DATA ---
    COLORS = {
        'Vice': '#e74c3c',           
        'Gentrification': '#3b82f6', 
        'Nuisance': '#f39c12',       
        'Superstition': '#9b59b6',   
        'Autre': '#95a5a6'           
    }

    # --- 3. CHARGEMENT DES DONNÉES ---
    try:
        df_immo = pd.read_csv(IMMO_CSV)
        df_poi = pd.read_csv(POI_CSV)
        with open(METRO_JSON, 'r', encoding='utf-8') as f:
            metro_data = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lors de la lecture des fichiers : {e}")
        return

    # --- 4. INITIALISATION CARTE ---
    m = folium.Map(
        location=[45.75, 4.85],
        zoom_start=13,
        tiles="cartodbpositron",
        control_scale=True
    )

    # --- 5. CRÉATION DES GROUPES (LOGIQUE FILTRES) ---
    fg_immo = folium.FeatureGroup(name="Immo")
    fg_metro_lignes = folium.FeatureGroup(name="Metro Lignes")
    fg_metro_stations = folium.FeatureGroup(name="Metro Stations")
    fg_vice = folium.FeatureGroup(name="Vice")
    fg_gentri = folium.FeatureGroup(name="Gentrification")
    fg_nuisance = folium.FeatureGroup(name="Nuisance")
    fg_superstition = folium.FeatureGroup(name="Superstition")

    # --- 6. AJOUT DES POI (CAVALIERS) ---
    for _, row in df_poi.iterrows():
        cat_full = str(row['categorie_cavalier'])
        cat_short = cat_full.split(' - ')[0]
        color = COLORS.get(cat_short, COLORS['Autre'])
        
        target_group = fg_vice
        if cat_short == 'Gentrification': target_group = fg_gentri
        elif cat_short == 'Nuisance': target_group = fg_nuisance
        elif cat_short == 'Superstition': target_group = fg_superstition

        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(f"<b>{cat_full}</b><br>{row['nom_lieu']}", max_width=200)
        ).add_to(target_group)

    # --- 7. AJOUT DES METROS (LIGNES & STATIONS) ---
    for feature in metro_data['features']:
        geom = feature['geometry']
        props = feature['properties']
        color_raw = props.get('couleur', '128 128 128')
        hex_color = '#%02x%02x%02x' % tuple(map(int, color_raw.split()))

        if geom['type'] == 'MultiLineString':
            for line in geom['coordinates']:
                folium.PolyLine(
                    [[p[1], p[0]] for p in line],
                    color=hex_color, weight=4, opacity=0.8,
                    popup=f"Ligne {props.get('ligne', '?')}"
                ).add_to(fg_metro_lignes)
        
        # On simule des stations aux extrémités/points clés pour l'exemple
        folium.CircleMarker(
            location=[geom['coordinates'][0][0][1], geom['coordinates'][0][0][0]],
            radius=3, color='white', fill=True, fill_color=hex_color, weight=1, fill_opacity=1
        ).add_to(fg_metro_stations)

    # --- 8. AJOUT DES ANNONCES ---
    for _, row in df_immo.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=7,
            color='#2c3e50',
            fill=True,
            fill_color='#2c3e50',
            fill_opacity=0.9,
            weight=2,
            popup=folium.Popup(f"<b>{row['prix']}€</b><br>{row['type']}<br>{row['surface']}m²", max_width=200)
        ).add_to(fg_immo)

    # --- 9. ASSEMBLAGE ET SAUVEGARDE ---
    fg_immo.add_to(m)
    fg_metro_lignes.add_to(m)
    fg_metro_stations.add_to(m)
    fg_vice.add_to(m)
    fg_gentri.add_to(m)
    fg_nuisance.add_to(m)
    fg_superstition.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Hack JS pour le contrôle depuis React
    hack = """
    <style>.leaflet-control-layers {display:none!important;}</style>
    <script>
    window.addEventListener("message", function(e) {
        if(e.data.type==='TOGGLE_LAYER'){
            var labels=document.getElementsByTagName('label');
            for(var i=0;i<labels.length;i++){
                if(labels[i].textContent.trim().includes(e.data.name)){
                    labels[i].click();
                }
            }
        }
    });
    </script>
    """
    m.get_root().html.add_child(folium.Element(hack))

    # Création du dossier cible s'il n'existe pas
    os.makedirs(FRONTEND_DATA_DIR, exist_ok=True)
    
    # Sauvegarde physique du fichier
    m.save(OUTPUT_HTML)
    print(f"✅ CARTE GÉNÉRÉE AVEC SUCCÈS : {OUTPUT_HTML}")

# Bloc d'exécution
if __name__ == "__main__":
    main()
