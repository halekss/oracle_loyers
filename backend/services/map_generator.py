import folium
from folium.features import DivIcon
import json
import os
import pandas as pd

# --- CONFIGURATION COULEURS ---
COLORS = {
    'Vice': '#e74c3c',          # Rouge
    'Gentrification': '#3498db', # Bleu
    'Nuisance': '#f39c12',       # Orange
    'Superstition': '#9b59b6',   # Violet
    'Defaut': '#95a5a6'          # Gris
}

# --- STATIONS MÉTRO (Avec leurs couleurs officielles) ---
LYON_STATIONS = [
    # Ligne A (Rouge #e9003a)
    {"nom": "Perrache", "lat": 45.7485, "lon": 4.8266, "c": "#e9003a"},
    {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322, "c": "#e9003a"},
    {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "c": "#e9003a"},
    {"nom": "Cordeliers", "lat": 45.7634, "lon": 4.8358, "c": "#e9003a"},
    {"nom": "Masséna", "lat": 45.7712, "lon": 4.8525, "c": "#e9003a"},
    {"nom": "Charpennes", "lat": 45.7710, "lon": 4.8636, "c": "#e9003a"},
    {"nom": "Vaulx-en-Velin La Soie", "lat": 45.7607, "lon": 4.9298, "c": "#e9003a"},
    
    # Ligne B (Bleu #0073ba)
    {"nom": "Part-Dieu", "lat": 45.7601, "lon": 4.8590, "c": "#0073ba"},
    {"nom": "Brotteaux", "lat": 45.7663, "lon": 4.8587, "c": "#0073ba"},
    {"nom": "Place Guichard", "lat": 45.7578, "lon": 4.8512, "c": "#0073ba"},
    {"nom": "Saxe-Gambetta", "lat": 45.7516, "lon": 4.8486, "c": "#0073ba"},
    {"nom": "Jean Macé", "lat": 45.7456, "lon": 4.8432, "c": "#0073ba"},
    {"nom": "Stade Gerland", "lat": 45.7234, "lon": 4.8305, "c": "#0073ba"},
    {"nom": "Gare d'Oullins", "lat": 45.7161, "lon": 4.8138, "c": "#0073ba"},
    
    # Ligne C (Orange #f78e1e)
    {"nom": "Croix-Rousse", "lat": 45.7745, "lon": 4.8315, "c": "#f78e1e"},
    {"nom": "Cuire", "lat": 45.7852, "lon": 4.8338, "c": "#f78e1e"},
    
    # Ligne D (Vert #009e49)
    {"nom": "Gare de Vaise", "lat": 45.7797, "lon": 4.8051, "c": "#009e49"},
    {"nom": "Valmy", "lat": 45.7735, "lon": 4.8055, "c": "#009e49"},
    {"nom": "Vieux Lyon", "lat": 45.7598, "lon": 4.8268, "c": "#009e49"},
    {"nom": "Guillotière", "lat": 45.7548, "lon": 4.8415, "c": "#009e49"},
    {"nom": "Grange Blanche", "lat": 45.7434, "lon": 4.8763, "c": "#009e49"},
    {"nom": "Gare de Vénissieux", "lat": 45.7047, "lon": 4.8879, "c": "#009e49"},
    
    # Funiculaires (Vert Foncé)
    {"nom": "Fourvière", "lat": 45.7623, "lon": 4.8220, "c": "#387a00"},
    {"nom": "St-Just", "lat": 45.7554, "lon": 4.8163, "c": "#387a00"},
]

class MapGenerator:
    def __init__(self, static_dir, data_dir):
        self.static_dir = static_dir
        self.metro_json_path = os.path.join(data_dir, "metro_lyon.json")

    def get_category_data(self, row):
        # 1. Nettoyage
        text = (str(row['categorie_cavalier']) + " " + str(row['nom_lieu'])).lower()
        
        # 2. Logique de Tri (Mots Clés Indestructibles)
        cat = 'Defaut'
        if any(x in text for x in ['nuisance', 'disco', 'boite', 'bruit', 'ecole', 'lycee', 'stade', 'usine']):
            cat = 'Nuisance'
        elif any(x in text for x in ['vice', 'sex', 'bar', 'pub', 'club', 'casino', 'tabac', 'alcool']):
            cat = 'Vice'
        elif any(x in text for x in ['superstition', 'cimet', 'eglise', 'mort', 'hopital', 'culte', 'funeraire']):
            cat = 'Superstition'
        elif any(x in text for x in ['gentrification', 'bio', 'yoga', 'brunch', 'theat', 'concept', 'bobo']):
            cat = 'Gentrification'

        if cat == 'Nuisance': return 'Nuisance (Bruit/Jeux)', COLORS['Nuisance']
        if cat == 'Vice': return 'Vice (Sexe/Bar)', COLORS['Vice']
        if cat == 'Gentrification': return 'Gentrification (Bio)', COLORS['Gentrification']
        if cat == 'Superstition': return 'Superstition (Mort/Culte)', COLORS['Superstition']
        return 'Autres Lieux', COLORS['Defaut']

    def generate(self, data_loader):
        print("🗺️  Génération de la carte (Design Métro Iconique)...")
        df_immo = data_loader.df_immo
        df_cav = data_loader.df_cav
        
        start_lat, start_lon = 45.7577, 4.8322 # Bellecour par défaut
        if not df_immo.empty:
            start_lat, start_lon = df_immo['latitude'].mean(), df_immo['longitude'].mean()

        m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='CartoDB dark_matter', prefer_canvas=True)

        # 1. IMMOBILIER (Points Verts)
        if not df_immo.empty:
            folium.GeoJson(
                self.df_to_geojson(df_immo.head(200), ['prix'], '#2ecc71'), # Limité à 200 pour perf
                name="Offres Immobilières",
                marker=folium.CircleMarker(radius=3, fill=True, color='#2ecc71', fill_opacity=0.7, weight=0),
                popup=folium.GeoJsonPopup(fields=['prix'])
            ).add_to(m)

        # 2. MÉTRO (AVEC ICONES "M")
        metro_group = folium.FeatureGroup(name="Réseau Métro (API)")
        
        # A. Tracé des lignes (si dispo)
        if os.path.exists(self.metro_json_path):
            try:
                with open(self.metro_json_path, 'r') as f: metro_data = json.load(f)
                folium.GeoJson(
                    metro_data, 
                    name="Lignes", 
                    style_function=lambda x: {'color': '#666', 'weight': 2, 'opacity': 0.5}
                ).add_to(metro_group)
            except: pass

        # B. Les Stations (Design CSS)
        for s in LYON_STATIONS:
            # Création du logo en CSS pur
            icon_html = f"""
            <div style="
                background-color: {s['c']};
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid white;
                box-shadow: 0 0 5px rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-family: Arial, sans-serif;
                font-weight: 900;
                font-size: 11px;
            ">M</div>
            """
            
            folium.Marker(
                location=[s['lat'], s['lon']],
                icon=DivIcon(
                    html=icon_html,
                    icon_size=(24, 24),
                    icon_anchor=(12, 12) # Centré
                ),
                popup=f"Métro : {s['nom']}"
            ).add_to(metro_group)
        
        metro_group.add_to(m)

        # 3. CAVALIERS (Trieur Blindé)
        layers = {'Nuisance (Bruit/Jeux)': [], 'Vice (Sexe/Bar)': [], 'Gentrification (Bio)': [], 'Superstition (Mort/Culte)': [], 'Autres Lieux': []}

        if not df_cav.empty:
            for _, row in df_cav.iterrows():
                if pd.isna(row['latitude']): continue
                cat_name, color = self.get_category_data(row)
                
                feature = {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(row['longitude']), float(row['latitude'])]},
                    "properties": {"nom": str(row['nom_lieu']), "cat": str(row['categorie_cavalier']), "color": color}
                }
                if cat_name in layers: layers[cat_name].append(feature)

            for layer_name, features in layers.items():
                if features:
                    folium.GeoJson(
                        {"type": "FeatureCollection", "features": features},
                        name=layer_name,
                        marker=folium.CircleMarker(radius=4, fill=True, fill_opacity=0.8, weight=0),
                        style_function=lambda x: {'fillColor': x['properties']['color'], 'color': x['properties']['color']},
                        popup=folium.GeoJsonPopup(fields=['nom', 'cat'])
                    ).add_to(m)

        # 4. HACK SLIDERS
        folium.LayerControl(position='topleft', collapsed=False).add_to(m)
        hack_script = """
        <style>.leaflet-control-layers { display: none !important; }</style>
        <script>
            window.addEventListener("message", function(event) {
                if (event.data.type === 'TOGGLE_LAYER') {
                    var normalize = str => str.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase();
                    var target = normalize(event.data.name);
                    var labels = document.querySelectorAll('.leaflet-control-layers-selector + span');
                    labels.forEach(function(label) {
                        var labelText = normalize(label.innerText.trim());
                        if (labelText.includes(target) || target.includes(labelText)) {
                            var cb = label.previousElementSibling;
                            if (cb.checked !== event.data.show) cb.click();
                        }
                    });
                }
            });
        </script>
        """
        m.get_root().html.add_child(folium.Element(hack_script))

        output_path = os.path.join(self.static_dir, "map_lyon.html")
        m.save(output_path)
        print(f"✅ Carte générée avec icônes Métro !")

    def df_to_geojson(self, df, props, color):
        features = []
        for _, row in df.iterrows():
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row['longitude'], row['latitude']]},
                "properties": {k: str(row[k]) for k in props}
            })
        return {"type": "FeatureCollection", "features": features}