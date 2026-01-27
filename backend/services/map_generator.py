import folium
from folium.features import DivIcon
import json
import os
import pandas as pd

# --- LISTE STATIONS (Complète) ---
LYON_STATIONS = [
    # A (Rouge)
    {"nom": "Perrache", "lat": 45.7485, "lon": 4.8266, "c": "#e9003a"},
    {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322, "c": "#e9003a"},
    {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "c": "#e9003a"},
    {"nom": "Charpennes", "lat": 45.7710, "lon": 4.8636, "c": "#e9003a"},
    {"nom": "Vaulx-en-Velin La Soie", "lat": 45.7607, "lon": 4.9298, "c": "#e9003a"},
    # B (Bleu)
    {"nom": "Part-Dieu", "lat": 45.7601, "lon": 4.8590, "c": "#0073ba"},
    {"nom": "Saxe-Gambetta", "lat": 45.7516, "lon": 4.8486, "c": "#0073ba"},
    {"nom": "Gare d'Oullins", "lat": 45.7161, "lon": 4.8138, "c": "#0073ba"},
    {"nom": "Oullins Centre", "lat": 45.7139, "lon": 4.8115, "c": "#0073ba"},
    {"nom": "St-Genis Hôp. Sud", "lat": 45.6946, "lon": 4.7968, "c": "#0073ba"},
    # C (Orange)
    {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "c": "#f78e1e"},
    {"nom": "Croix-Rousse", "lat": 45.7745, "lon": 4.8315, "c": "#f78e1e"},
    {"nom": "Cuire", "lat": 45.7852, "lon": 4.8338, "c": "#f78e1e"},
    # D (Vert)
    {"nom": "Gare de Vaise", "lat": 45.7797, "lon": 4.8051, "c": "#009e49"},
    {"nom": "Vieux Lyon", "lat": 45.7598, "lon": 4.8268, "c": "#009e49"},
    {"nom": "Grange Blanche", "lat": 45.7434, "lon": 4.8763, "c": "#009e49"},
    {"nom": "Gare de Vénissieux", "lat": 45.7047, "lon": 4.8879, "c": "#009e49"},
    # Funiculaires (Vert Foncé)
    {"nom": "Vieux Lyon (F)", "lat": 45.7598, "lon": 4.8268, "c": "#387a00"},
    {"nom": "Fourvière", "lat": 45.7623, "lon": 4.8220, "c": "#387a00"},
    {"nom": "St-Just", "lat": 45.7554, "lon": 4.8163, "c": "#387a00"},
]

class MapGenerator:
    def __init__(self, static_dir, data_dir):
        self.static_dir = static_dir
        self.metro_json_path = os.path.join(data_dir, "metro_lyon.json")

    def df_to_geojson(self, dataframe, properties_cols, force_color=None):
        features = []
        for _, row in dataframe.iterrows():
            if pd.notnull(row['longitude']) and pd.notnull(row['latitude']):
                props = {col: str(row[col]) for col in properties_cols if col in dataframe.columns}
                if force_color: props['marker_color'] = force_color
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(row['longitude']), float(row['latitude'])]
                    },
                    "properties": props
                })
        return {"type": "FeatureCollection", "features": features}

    def generate(self, data_loader):
        print("🗺️  Génération de la carte (Architecture Modulaire)...")
        
        df_immo = data_loader.df_immo
        df_cav = data_loader.df_cav
        
        start_lat, start_lon = 45.7640, 4.8357
        if not df_immo.empty:
            start_lat, start_lon = df_immo['latitude'].mean(), df_immo['longitude'].mean()

        m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='CartoDB dark_matter', prefer_canvas=True)

        # 1. IMMOBILIER
        if not df_immo.empty:
            immo_json = self.df_to_geojson(df_immo.head(3000), ['prix', 'surface'], force_color='#2ecc71')
            folium.GeoJson(
                immo_json,
                name="Offres Immobilières",
                marker=folium.CircleMarker(radius=3, fill=True, fill_opacity=0.6, weight=0),
                style_function=lambda x: {'fillColor': x['properties']['marker_color'], 'color': x['properties']['marker_color']},
                popup=folium.GeoJsonPopup(fields=['prix', 'surface'], aliases=['Prix', 'Surface'])
            ).add_to(m)

        # 2. MÉTRO (Groupe Unique : Tracé + Stations)
        metro_group = folium.FeatureGroup(name="Réseau Métro (API)")

        # A. Tracés
        if os.path.exists(self.metro_json_path):
            try:
                with open(self.metro_json_path, 'r') as f: metro_data = json.load(f)
                def style_metro(f):
                    line = str(f.get('properties', {}).get('ligne', '') or f.get('properties', {}).get('code_ligne', '')).upper()
                    c = '#555'
                    if 'A' in line: c='#e9003a'
                    elif 'B' in line: c='#0073ba'
                    elif 'C' in line: c='#f78e1e'
                    elif 'D' in line: c='#009e49'
                    elif 'F' in line: c='#387a00'
                    return {'color': c, 'weight': 4, 'opacity': 0.8}
                folium.GeoJson(metro_data, name="Lignes", style_function=style_metro).add_to(metro_group)
            except Exception as e:
                print(f"⚠️ Erreur chargement JSON Métro: {e}")

        # B. Stations (Icônes M)
        for s in LYON_STATIONS:
            icon_html = f"""<div style="background-color: {s['c']}; color: white; width: 16px; height: 16px; border-radius: 4px; border: 1.5px solid white; display: flex; align-items: center; justify-content: center; font-family: Arial; font-weight: bold; font-size: 10px;">M</div>"""
            folium.Marker(
                location=[s['lat'], s['lon']],
                icon=DivIcon(html=icon_html, icon_size=(16,16), icon_anchor=(8,8)),
                popup=f"Arrêt : {s['nom']}"
            ).add_to(metro_group)
        
        metro_group.add_to(m)

        # 3. CAVALIERS
        if not df_cav.empty:
            # Création colonne recherche
            df_cav['search_text'] = (df_cav['nom_lieu'].fillna('') + ' ' + df_cav['categorie_cavalier'].fillna('')).str.lower()
            
            groups = {
                'Vice': {'keys': ['vice', 'sex', 'bar', 'club', 'tabac', 'night', 'casino', 'pub', 'alcool'], 'color': '#e74c3c'},
                'Gentrification': {'keys': ['gentrification', 'bio', 'yoga', 'concept', 'bobo', 'vegan', 'café', 'brunch'], 'color': '#3498db'},
                'Nuisance': {'keys': ['ecole', 'école', 'bruit', 'gare', 'usine', 'travaux', 'jeu', 'pompier', 'stade'], 'color': '#f39c12'},
                'Superstition': {'keys': ['cimetiere', 'mort', 'eglise', 'hopital', 'culte', 'pompes', 'mosquée', 'clinique'], 'color': '#9b59b6'}
            }
            
            processed_indices = set()
            for name, config in groups.items():
                mask = df_cav['search_text'].apply(lambda x: any(k in x for k in config['keys']))
                sub_df = df_cav[mask]
                if not sub_df.empty:
                    processed_indices.update(sub_df.index)
                    geo_data = self.df_to_geojson(sub_df, ['nom_lieu', 'categorie_cavalier'], force_color=config['color'])
                    
                    # Noms Frontend
                    layer_name = name
                    if name == "Vice": layer_name = "Vice (Sexe/Bar)"
                    elif name == "Gentrification": layer_name = "Gentrification (Bio)"
                    elif name == "Nuisance": layer_name = "Nuisance (Bruit/Jeux)"
                    elif name == "Superstition": layer_name = "Superstition (Mort/Culte)"

                    folium.GeoJson(
                        geo_data,
                        name=layer_name,
                        marker=folium.CircleMarker(radius=4, fill=True, fill_opacity=0.8, weight=0),
                        style_function=lambda x: {'fillColor': x['properties']['marker_color'], 'color': x['properties']['marker_color']},
                        popup=folium.GeoJsonPopup(fields=['nom_lieu', 'categorie_cavalier'])
                    ).add_to(m)

            # Autres
            remaining = df_cav.drop(processed_indices)
            if not remaining.empty:
                folium.GeoJson(
                    self.df_to_geojson(remaining, ['nom_lieu', 'categorie_cavalier'], force_color='#95a5a6'),
                    name="Autres Lieux",
                    marker=folium.CircleMarker(radius=3, fill=True, fill_opacity=0.5, weight=0),
                    style_function=lambda x: {'fillColor': x['properties']['marker_color'], 'color': x['properties']['marker_color']},
                    popup=folium.GeoJsonPopup(fields=['nom_lieu', 'categorie_cavalier'])
                ).add_to(m)

        # 4. SCRIPT HACK (Gestion Sliders avec Normalisation)
        folium.LayerControl(position='topleft', collapsed=False).add_to(m)
        hack_script = """
        <style>.leaflet-control-layers { display: none !important; }</style>
        <script>
            window.addEventListener("message", function(event) {
                if (event.data.type === 'TOGGLE_LAYER') {
                    // Normalisation : minuscules et sans accents pour comparaison robuste
                    var normalize = str => str.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase();
                    var target = normalize(event.data.name);
                    
                    var labels = document.querySelectorAll('.leaflet-control-layers-selector + span');
                    labels.forEach(function(label) {
                        var labelText = normalize(label.innerText.trim());
                        
                        // Si le nom du label contient le nom cible (ex: "vice" dans "vice (sexe)") -> CLICK
                        if (labelText.includes(target) || target.includes(labelText)) {
                            var cb = label.previousElementSibling;
                            // On clique seulement si l'état actuel est différent de l'ordre reçu
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
        print(f"✅ Carte générée dans {output_path}")