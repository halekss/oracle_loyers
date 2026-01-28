import folium
import pandas as pd
import os
import json

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Fichiers
IMMO_CSV = os.path.join(DATA_DIR, 'master_immo_final.csv')
POI_CSV = os.path.join(DATA_DIR, 'cavaliers_lyon.csv')
METRO_JSON = os.path.join(DATA_DIR, 'metro_lyon.json')
OUTPUT_HTML = os.path.join(DATA_DIR, 'map_pings_lyon_calques.html')

print("🛑 DEBUT GENERATION CARTE...")

# 1. Chargement IMMO
try:
    df_immo = pd.read_csv(IMMO_CSV)
    print(f"✅ IMMO : {len(df_immo)} annonces chargées.")
except Exception as e:
    print(f"❌ IMMO ERREUR : {e}")
    df_immo = pd.DataFrame()

# 2. Chargement CAVALIERS (POI)
try:
    df_poi = pd.read_csv(POI_CSV)
    
    # Harmonisation des noms de colonnes (type vs type_local)
    if 'type' not in df_poi.columns and 'type_local' in df_poi.columns:
        df_poi['type'] = df_poi['type_local']
    
    # DEBUG : Affiche les types trouvés pour être sûr qu'on a les bons noms
    types_trouves = df_poi['type'].unique().tolist() if 'type' in df_poi.columns else []
    print(f"✅ CAVALIERS : {len(df_poi)} lieux chargés.")
    print(f"ℹ️ Types trouvés dans le CSV : {types_trouves[:10]} ...") 
    
except Exception as e:
    print(f"❌ CAVALIERS ERREUR : {e}")
    print(f"⚠️ Vérifie que {POI_CSV} existe bien !")
    df_poi = pd.DataFrame()

# 3. Création de la Carte
m = folium.Map(
    location=[45.7640, 4.8357], 
    zoom_start=13, 
    tiles='CartoDB dark_matter', 
    zoom_control=False # On cache le zoom
)

# 4. Création des Groupes (Noms EXACTS pour React)
fg_immo = folium.FeatureGroup(name='Immo', show=True)
fg_metro = folium.FeatureGroup(name='Metro', show=True)
fg_vice = folium.FeatureGroup(name='Vice', show=True)
fg_gentri = folium.FeatureGroup(name='Gentrification', show=False)
fg_nuisance = folium.FeatureGroup(name='Nuisance', show=False)
fg_superstition = folium.FeatureGroup(name='Superstition', show=False)

# --- A. IMMO (POINTS SIMPLES - PAS DE CLUSTER) ---
print("👉 Ajout des points Immo...")
for _, row in df_immo.iterrows():
    if pd.notnull(row.get('latitude')) and pd.notnull(row.get('longitude')):
        # Popup simple
        popup_txt = f"{row.get('type_local', 'Bien')} - {row.get('prix', '?')} €"
        
        # On utilise CircleMarker pour des points légers et SANS CLUSTER
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=3,               # Taille du point
            color='#22c55e',        # Contour Vert
            fill=True,
            fill_color='#22c55e',   # Remplissage Vert
            fill_opacity=0.8,
            popup=folium.Popup(popup_txt, max_width=200)
        ).add_to(fg_immo) # Ajout direct au groupe (pas de cluster)

# --- B. MÉTRO ---
if os.path.exists(METRO_JSON):
    print("👉 Ajout du Métro...")
    try:
        # 1. CENTRE ET FOND DE CARTE
        start_lat, start_lon = 45.7640, 4.8357
        if not df.empty:
            start_lat = df['latitude'].mean()
            start_lon = df['longitude'].mean()

        m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='CartoDB dark_matter')

        # --- 2. DÉFINITION DES HUBS MÉTRO (Pour les Logos) ---
        # Ces points auront le logo "M" stylisé
        metro_hubs = [
            {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322, "lines": "A/D", "color": "#e9003a"}, # Rouge
            {"nom": "Part-Dieu", "lat": 45.7601, "lon": 4.8590, "lines": "B", "color": "#0073ba"},   # Bleu
            {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "lines": "A/C", "color": "#e9003a"},
            {"nom": "Perrache", "lat": 45.7485, "lon": 4.8266, "lines": "A", "color": "#e9003a"},
            {"nom": "Charpennes", "lat": 45.7710, "lon": 4.8636, "lines": "A/B", "color": "#0073ba"},
            {"nom": "Gare de Vaise", "lat": 45.7797, "lon": 4.8051, "lines": "D", "color": "#009e49"}, # Vert
            {"nom": "Gare de Vénissieux", "lat": 45.7047, "lon": 4.8879, "lines": "D", "color": "#009e49"},
            {"nom": "Vieux Lyon", "lat": 45.7598, "lon": 4.8268, "lines": "D", "color": "#009e49"},
            {"nom": "Saxe-Gambetta", "lat": 45.7516, "lon": 4.8486, "lines": "B/D", "color": "#f78e1e"}, # Orange
            {"nom": "Grange Blanche", "lat": 45.7434, "lon": 4.8763, "lines": "D", "color": "#009e49"},
            {"nom": "Cuire", "lat": 45.7852, "lon": 4.8338, "lines": "C", "color": "#f78e1e"}
        ]

        # --- 3. CRÉATION DES CALQUES ---
        layers = {
            'MetroLines': folium.FeatureGroup(name="🚇 Lignes (Tracé)"),
            'MetroStations': folium.FeatureGroup(name="🛑 Stations (Logos)"),
            'Vice': folium.FeatureGroup(name="🔴 Vice (Bars, Nuit)"),
            'Gentrification': folium.FeatureGroup(name="🔵 Gentrification"),
            'Immo': folium.FeatureGroup(name="🏠 Immobilier (Top 200)")
        }

        # --- 4. AJOUT DES LOGOS "M" (DivIcon) ---
        for station in metro_hubs:
            # On crée un petit carré ou rond avec un "M" dedans en HTML pur
            # C'est plus robuste que de charger une image png
            html_icon = f"""
            <div style="
                background-color: {station['color']};
                color: white;
                width: 24px;
                height: 24px;
                border-radius: 4px;
                border: 2px solid white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: Arial, sans-serif;
                font-weight: 900;
                font-size: 14px;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
            ">M</div>
            """
            
            folium.Marker(
                location=[station['lat'], station['lon']],
                icon=folium.DivIcon(
                    html=html_icon,
                    icon_size=(24, 24),
                    icon_anchor=(12, 12) # Centre l'icône
                ),
                popup=f"<b>Métro {station['nom']}</b><br>Lignes: {station['lines']}",
                tooltip=station['nom']
            ).add_to(layers['MetroStations'])

        # --- 5. AJOUT DU TRACÉ GEOJSON (Si disponible) ---
        metro_json_path = os.path.join(BASE_DIR, "metro_lyon.json")
        
        def style_metro(feature):
            props = feature.get('properties', {})
            line_name = str(props.get('ligne', '')).upper()
            color = '#888888'
            if 'A' in line_name: color = '#e9003a'
            elif 'B' in line_name: color = '#0073ba'
            elif 'C' in line_name: color = '#f78e1e'
            elif 'D' in line_name: color = '#009e49'
            return {'color': color, 'weight': 4, 'opacity': 0.7}

        if os.path.exists(metro_json_path):
            try:
                folium.GeoJson(
                    metro_json_path,
                    name="Lignes TCL",
                    style_function=style_metro
                ).add_to(layers['MetroLines'])
            except Exception as e:
                print(f"⚠️ Erreur GeoJSON: {e}")

        # --- 6. AJOUT CAVALIERS (Vice vs Gentrification) ---
        if os.path.exists(CAVALIERS_PATH):
            df_cav = pd.read_csv(CAVALIERS_PATH)
            for _, row in df_cav.iterrows():
                cat = str(row.get('categorie_cavalier', 'Autre')).lower()
                
                # Style par défaut
                color = '#95a5a6'
                radius = 4
                group_key = 'Gentrification'
                
                if any(x in cat for x in ['vice', 'sex', 'bar', 'club', 'night']):
                    color = '#e74c3c' # Rouge néon
                    group_key = 'Vice'
                    radius = 5
                elif any(x in cat for x in ['gentrification', 'bio', 'yoga', 'concept']):
                    color = '#3498db' # Bleu futuriste
                    group_key = 'Gentrification'

                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=radius,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    weight=1,
                    popup=f"<b>{row.get('nom_lieu', '?')}</b><br>{cat}"
                ).add_to(layers[group_key])

        # --- 7. AJOUT IMMOBILIER (Vert Matrix) ---
        if not df.empty:
            for _, row in df.head(200).iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=3,
                    color='#2ecc71',
                    fill=True,
                    fill_opacity=0.5,
                    weight=0,
                    popup=f"{row.get('prix')} €<br>{row.get('surface')} m²"
                ).add_to(layers['Immo'])

        # --- 8. FINALISATION ---
        for layer in layers.values():
            layer.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        
        output_path = os.path.join(STATIC_DIR, "map_lyon.html")
        m.save(output_path)
        print(f"✅ Carte générée avec LOGOS MÉTRO : http://localhost:8000/static/map_lyon.html")

    except Exception as e:
        print(f"⚠️ Erreur JSON Métro : {e}")

# --- C. CAVALIERS (POIs) ---
print("👉 Ajout des Cavaliers...")

# Configuration des couleurs et icones
# Clé = le contenu de la colonne 'type' dans ton CSV (en minuscule)
mapping = {
    # VICE (Rouge)
    'bar': (fg_vice, 'red', 'beer'),
    'sex-shop': (fg_vice, 'red', 'heart'),
    'casino': (fg_vice, 'red', 'star'),
    'tabac': (fg_vice, 'red', 'fire'),
    'cbd_shop': (fg_vice, 'red', 'leaf'),
    
    # GENTRIFICATION (Bleu)
    'salle_sport': (fg_gentri, 'blue', 'heartbeat'),
    'yoga': (fg_gentri, 'blue', 'leaf'),
    'crèche': (fg_gentri, 'blue', 'child'),
    'épicerie_fine': (fg_gentri, 'blue', 'shopping-cart'),
    'torréfacteur': (fg_gentri, 'blue', 'coffee'),
    'atelier_vélo': (fg_gentri, 'blue', 'bicycle'),
    'fleuriste': (fg_gentri, 'blue', 'leaf'),
    'concept store': (fg_gentri, 'blue', 'star'),

    # NUISANCE (Orange)
    'école': (fg_nuisance, 'orange', 'book'),
    'aire de jeux': (fg_nuisance, 'orange', 'futbol-o'), # Attention aux espaces
    'aire_de_jeux': (fg_nuisance, 'orange', 'futbol-o'),
    'salle de concert': (fg_nuisance, 'orange', 'music'),
    'discothèque': (fg_nuisance, 'orange', 'glass'),
    'station service': (fg_nuisance, 'orange', 'car'),
    'station_service': (fg_nuisance, 'orange', 'car'),

    # SUPERSTITION (Violet)
    'pompes funèbres': (fg_superstition, 'purple', 'plus'),
    'pompes_funèbres': (fg_superstition, 'purple', 'plus'),
    'cimetière': (fg_superstition, 'purple', 'plus-square'),
    'lieu de culte': (fg_superstition, 'purple', 'bell'),
    'église': (fg_superstition, 'purple', 'bell'),
}

count_added = 0
for _, row in df_poi.iterrows():
    # Nettoyage du type (minuscule, sans espace inutile)
    raw_type = str(row.get('type', '')).lower().strip()
    
    if raw_type in mapping and pd.notnull(row.get('latitude')):
        group, color, icon_name = mapping[raw_type]
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"<b>{row.get('nom', raw_type)}</b>",
            icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
        ).add_to(group)
        count_added += 1

print(f"✅ {count_added} points d'intérêts placés.")

# --- 5. FINALISATION (HACK JS) ---
fg_immo.add_to(m)
fg_metro.add_to(m)
fg_vice.add_to(m)
fg_gentri.add_to(m)
fg_nuisance.add_to(m)
fg_superstition.add_to(m)

# Ajout du contrôle natif (pour que le JS puisse cliquer dessus)
folium.LayerControl(collapsed=False).add_to(m)

html = m.get_root().render()

# CSS pour cacher le menu blanc + JS pour écouter React
hack_code = """
<style>
    /* On cache le menu moche de Folium */
    .leaflet-control-layers { display: none !important; }
</style>
<script>
    console.log("🗺️ Carte Oracle chargée. Écoute des messages React...");
    window.addEventListener("message", function(e) {
        if (e.data.type === 'TOGGLE_LAYER') {
            console.log("Message reçu pour : " + e.data.name + " -> " + e.data.show);
            var labels = document.getElementsByTagName('label');
            for (var i=0; i<labels.length; i++) {
                // On cherche le label qui contient le nom (ex: "Vice")
                if (labels[i].textContent.trim().includes(e.data.name)) {
                    var box = labels[i].querySelector('input');
                    // Si l'état de la checkbox est différent de l'ordre reçu, on clique
                    if (box && box.checked !== e.data.show) {
                        box.click();
                    }
                    break;
                }
            }
        }
    });
</script>
</body>
"""

html = html.replace('</body>', hack_code)

# Suppression de l'ancien fichier avant écriture (pour être sûr !)
if os.path.exists(OUTPUT_HTML):
    os.remove(OUTPUT_HTML)

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"🎉 TERMINÉ : Carte générée dans {OUTPUT_HTML}")