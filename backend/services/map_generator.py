import folium
from folium.features import DivIcon
import json
import os
import pandas as pd

# --- CONFIGURATION COULEURS (Retour aux standards TCL) ---
COLORS = {
    'Vice': '#e74c3c',          # Rouge standard
    'Gentrification': '#3b82f6', # Bleu standard
    'Nuisance': '#f59e0b',       # Orange standard
    'Superstition': '#9333ea',   # Violet standard
    'Defaut': '#64748b'          # Gris
}

# --- LISTE COMPLÈTE DU MÉTRO LYONNAIS ---
LYON_STATIONS = [
    # === LIGNE A (ROUGE TCL) ===
    {"nom": "Perrache", "lat": 45.74846, "lon": 4.82664, "c": "#e9003a"},
    {"nom": "Ampère - Victor Hugo", "lat": 45.75333, "lon": 4.82962, "c": "#e9003a"},
    {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322, "c": "#e9003a"},
    {"nom": "Cordeliers", "lat": 45.7634, "lon": 4.8358, "c": "#e9003a"},
    {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "c": "#e9003a"},
    {"nom": "Foch", "lat": 45.7696, "lon": 4.8432, "c": "#e9003a"},
    {"nom": "Masséna", "lat": 45.7712, "lon": 4.8525, "c": "#e9003a"},
    {"nom": "Charpennes", "lat": 45.7710, "lon": 4.8636, "c": "#e9003a"},
    {"nom": "République", "lat": 45.7705, "lon": 4.8765, "c": "#e9003a"},
    {"nom": "Gratte-Ciel", "lat": 45.7694, "lon": 4.8856, "c": "#e9003a"},
    {"nom": "Flachet", "lat": 45.7667, "lon": 4.8932, "c": "#e9003a"},
    {"nom": "Cusset", "lat": 45.7637, "lon": 4.9042, "c": "#e9003a"},
    {"nom": "Laurent Bonnevay", "lat": 45.7621, "lon": 4.9198, "c": "#e9003a"},
    {"nom": "Vaulx-en-Velin La Soie", "lat": 45.7607, "lon": 4.9298, "c": "#e9003a"},

    # === LIGNE B (BLEU TCL) ===
    {"nom": "Charpennes", "lat": 45.7710, "lon": 4.8636, "c": "#0073ba"},
    {"nom": "Brotteaux", "lat": 45.7663, "lon": 4.8587, "c": "#0073ba"},
    {"nom": "Part-Dieu", "lat": 45.7601, "lon": 4.8590, "c": "#0073ba"},
    {"nom": "Place Guichard", "lat": 45.7578, "lon": 4.8512, "c": "#0073ba"},
    {"nom": "Saxe-Gambetta", "lat": 45.7516, "lon": 4.8486, "c": "#0073ba"},
    {"nom": "Jean Macé", "lat": 45.7456, "lon": 4.8432, "c": "#0073ba"},
    {"nom": "Jean Jaurès", "lat": 45.7380, "lon": 4.8365, "c": "#0073ba"},
    {"nom": "Debourg", "lat": 45.7315, "lon": 4.8335, "c": "#0073ba"},
    {"nom": "Stade de Gerland", "lat": 45.7234, "lon": 4.8305, "c": "#0073ba"},
    {"nom": "Gare d'Oullins", "lat": 45.7161, "lon": 4.8138, "c": "#0073ba"},
    {"nom": "Oullins Centre", "lat": 45.7139, "lon": 4.8115, "c": "#0073ba"},
    {"nom": "St-Genis Hôp. Sud", "lat": 45.6946, "lon": 4.7968, "c": "#0073ba"},

    # === LIGNE C (ORANGE TCL) ===
    {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "c": "#f78e1e"},
    {"nom": "Croix-Paquet", "lat": 45.7702, "lon": 4.8351, "c": "#f78e1e"},
    {"nom": "Croix-Rousse", "lat": 45.7745, "lon": 4.8315, "c": "#f78e1e"},
    {"nom": "Hénon", "lat": 45.7795, "lon": 4.8291, "c": "#f78e1e"},
    {"nom": "Cuire", "lat": 45.7852, "lon": 4.8338, "c": "#f78e1e"},

    # === LIGNE D (VERT TCL) ===
    {"nom": "Gare de Vaise", "lat": 45.7797, "lon": 4.8051, "c": "#009e49"},
    {"nom": "Valmy", "lat": 45.7735, "lon": 4.8055, "c": "#009e49"},
    {"nom": "Gorge de Loup", "lat": 45.7656, "lon": 4.8058, "c": "#009e49"},
    {"nom": "Vieux Lyon", "lat": 45.7598, "lon": 4.8268, "c": "#009e49"},
    {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322, "c": "#009e49"},
    {"nom": "Guillotière", "lat": 45.7548, "lon": 4.8415, "c": "#009e49"},
    {"nom": "Saxe-Gambetta", "lat": 45.7516, "lon": 4.8486, "c": "#009e49"},
    {"nom": "Garibaldi", "lat": 45.7485, "lon": 4.8565, "c": "#009e49"},
    {"nom": "Sans Souci", "lat": 45.7465, "lon": 4.8655, "c": "#009e49"},
    {"nom": "Monplaisir - Lumière", "lat": 45.7450, "lon": 4.8725, "c": "#009e49"},
    {"nom": "Grange Blanche", "lat": 45.7434, "lon": 4.8763, "c": "#009e49"},
    {"nom": "Laënnec", "lat": 45.7385, "lon": 4.8825, "c": "#009e49"},
    {"nom": "Mermoz-Pinel", "lat": 45.7315, "lon": 4.8885, "c": "#009e49"},
    {"nom": "Parilly", "lat": 45.7195, "lon": 4.8925, "c": "#009e49"},
    {"nom": "Gare de Vénissieux", "lat": 45.7047, "lon": 4.8879, "c": "#009e49"},

    # === FUNICULAIRES ===
    {"nom": "Vieux Lyon (F)", "lat": 45.7598, "lon": 4.8268, "c": "#555555"},
    {"nom": "Minimes", "lat": 45.7563, "lon": 4.8225, "c": "#555555"},
    {"nom": "St-Just", "lat": 45.7554, "lon": 4.8163, "c": "#555555"},
    {"nom": "Fourvière", "lat": 45.7623, "lon": 4.8220, "c": "#555555"},
]

class MapGenerator:
    def __init__(self, static_dir, data_dir):
        self.static_dir = static_dir
        self.metro_json_path = os.path.join(data_dir, "metro_lyon.json")

    def get_category_data(self, row):
        # 1. Nettoyage
        text = (str(row['categorie_cavalier']) + " " + str(row['nom_lieu'])).lower()
       
        # 2. Logique de Tri
        cat = 'Defaut'
        if any(x in text for x in ['nuisance', 'disco', 'boite', 'bruit', 'ecole', 'lycee', 'stade', 'usine']):
            cat = 'Nuisance'
        elif any(x in text for x in ['vice', 'sex', 'bar', 'pub', 'club', 'casino', 'tabac', 'alcool']):
            cat = 'Vice'
        elif any(x in text for x in ['superstition', 'cimet', 'eglise', 'mort', 'hopital', 'culte', 'funeraire']):
            cat = 'Superstition'
        elif any(x in text for x in ['gentrification', 'bio', 'yoga', 'brunch', 'theat', 'concept', 'bobo', 'createur']):
            cat = 'Gentrification'

        if cat == 'Nuisance': return 'Nuisance (Bruit/Jeux)', COLORS['Nuisance']
        if cat == 'Vice': return 'Vice (Sexe/Bar)', COLORS['Vice']
        if cat == 'Gentrification': return 'Gentrification (Bio)', COLORS['Gentrification']
        if cat == 'Superstition': return 'Superstition (Mort/Culte)', COLORS['Superstition']
        return 'Autres Lieux', COLORS['Defaut']

    def generate(self, data_loader):
        print("🗺️  Génération de la carte (Style Sobre & Complet)...")
        df_immo = data_loader.df_immo
        df_cav = data_loader.df_cav
       
        start_lat, start_lon = 45.7577, 4.8322
        if not df_immo.empty:
            start_lat, start_lon = df_immo['latitude'].mean(), df_immo['longitude'].mean()

        m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='CartoDB dark_matter', prefer_canvas=True)

        # 1. IMMOBILIER (Points Verts avec tooltip ET popup détaillé)
        if not df_immo.empty:
            folium.GeoJson(
                self.df_to_geojson(df_immo.head(300), ['type', 'surface', 'prix', 'code_postal'], '#2ecc71'),
                name="Offres Immobilières",
                marker=folium.CircleMarker(radius=3, fill=True, color='#2ecc71', fill_opacity=0.6, weight=0),
                tooltip=folium.GeoJsonTooltip(
                    fields=['prix', 'type'],
                    aliases=['Prix :', 'Type :']
                ),
                popup=folium.GeoJsonPopup(
                    fields=['type', 'surface', 'prix', 'code_postal'],
                    aliases=['Type :', 'Surface :', 'Prix :', 'Code Postal :'],
                    localize=True,
                    style='background-color: rgba(30, 41, 59, 0.95); color: #e2e8f0; font-family: sans-serif; padding: 10px; border-radius: 6px;'
                )
            ).add_to(m)

        # 2. MÉTRO (DESIGN DISCRET MAIS LISIBLE)
        metro_group = folium.FeatureGroup(name="Réseau Métro (API)")
       
        if os.path.exists(self.metro_json_path):
            try:
                with open(self.metro_json_path, 'r') as f: metro_data = json.load(f)
                folium.GeoJson(
                    metro_data,
                    name="Lignes",
                    style_function=lambda x: {'color': '#555', 'weight': 2, 'opacity': 0.3}
                ).add_to(metro_group)
            except: pass

        for s in LYON_STATIONS:
            # STYLE : Petit rond, pas de halo, couleur officielle
            icon_html = f"""
            <div style="
                background-color: {s['c']};
                width: 14px; /* Beaucoup plus petit (avant 20px) */
                height: 14px;
                border-radius: 50%;
                border: 1.5px solid white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.5); /* Ombre légère, pas de néon */
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-family: Arial, sans-serif;
                font-weight: bold;
                font-size: 8px; /* Tout petit M */
                cursor: pointer;
            ">M</div>
            """
           
            folium.Marker(
                location=[s['lat'], s['lon']],
                icon=DivIcon(html=icon_html, icon_size=(14, 14), icon_anchor=(7, 7)),
                tooltip=f"{s['nom']}" # On garde le survol que tu aimes
            ).add_to(metro_group)
       
        metro_group.add_to(m)

        # 3. CAVALIERS (Retour aux points classiques propres)
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
                        # Cercle propre, petite bordure blanche pour détacher du fond noir
                        marker=folium.CircleMarker(radius=4, fill=True, fill_opacity=0.8, weight=1, color='#ffffff'),
                        style_function=lambda x: {'fillColor': x['properties']['color'], 'color': '#ffffff', 'weight': 1, 'opacity': 0.5},
                        tooltip=folium.GeoJsonTooltip(fields=['nom', 'cat'], aliases=['Lieu :', 'Type :'])
                    ).add_to(m)

        # 4. DARK UI (Tooltip et Popup sombres mais propres)
        folium.LayerControl(position='topleft', collapsed=False).add_to(m)
        hack_script = """
        <style>
            .leaflet-control-layers { display: none !important; }
           
            /* Tooltip Sombre Minimaliste */
            .leaflet-tooltip {
                background-color: rgba(30, 41, 59, 0.95) !important;
                border: 1px solid rgba(255,255,255,0.1);
                color: #e2e8f0;
                font-family: sans-serif;
                font-weight: 500;
                font-size: 12px;
                padding: 4px 8px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
                border-radius: 4px;
            }
            .leaflet-tooltip-top:before { border-top-color: rgba(30, 41, 59, 0.95); }
            .leaflet-tooltip-bottom:before { border-bottom-color: rgba(30, 41, 59, 0.95); }
            .leaflet-tooltip-left:before { border-left-color: rgba(30, 41, 59, 0.95); }
            .leaflet-tooltip-right:before { border-right-color: rgba(30, 41, 59, 0.95); }
            
            /* Popup Sombre pour les annonces immobilières */
            .leaflet-popup-content-wrapper {
                background-color: rgba(30, 41, 59, 0.95) !important;
                border: 1px solid rgba(255,255,255,0.15);
                color: #e2e8f0;
                border-radius: 6px;
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.5);
            }
            .leaflet-popup-content {
                font-family: sans-serif;
                font-size: 13px;
                line-height: 1.6;
                margin: 12px;
                color: #e2e8f0;
            }
            .leaflet-popup-tip {
                background-color: rgba(30, 41, 59, 0.95) !important;
                border: 1px solid rgba(255,255,255,0.15);
            }
            .leaflet-popup-close-button {
                color: #e2e8f0 !important;
                font-size: 18px;
            }
            .leaflet-popup-close-button:hover {
                color: #ffffff !important;
            }
        </style>
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
        print(f"✅ Carte générée (Mode Clean & Complet) !")

    def df_to_geojson(self, df, props, color):
        features = []
        for _, row in df.iterrows():
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row['longitude'], row['latitude']]},
                "properties": {k: str(row[k]) for k in props}
            })
        return {"type": "FeatureCollection", "features": features}
