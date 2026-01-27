# backend/services/map_generator.py
import folium
from folium.features import DivIcon
import os
from core.constants import COLORS, ALL_STATIONS, KEYWORDS

class MapGenerator:
    def __init__(self, static_dir):
        self.static_dir = static_dir

    def generate(self, data_loader):
        print("🗺️ Map: Génération de la carte...")
        
        # 1. CENTRE DE LA CARTE
        start_lat, start_lon = 45.7640, 4.8357
        if not data_loader.df_immo.empty:
             start_lat = data_loader.df_immo['latitude'].mean()
             start_lon = data_loader.df_immo['longitude'].mean()

        m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='CartoDB dark_matter')

        # 2. CALQUES
        layers = {
            'MetroLines': folium.FeatureGroup(name="🚇 Lignes Métro (API)"),
            'MetroStations': folium.FeatureGroup(name="🛑 Stations Métro"),
            'Vice': folium.FeatureGroup(name="🔴 Vice (Sexe/Bar/Junk)"),
            'Gentrification': folium.FeatureGroup(name="🔵 Gentrification (Bio/Yoga)"),
            'Nuisance': folium.FeatureGroup(name="🟠 Nuisance (Bruit/Jeux)"),
            'Superstition': folium.FeatureGroup(name="🟣 Superstition (Mort/Culte)"),
            'Immo': folium.FeatureGroup(name="🏠 Immobilier")
        }

        # 3. REMPLISSAGE - MÉTRO LIGNES
        if data_loader.metro_geojson:
            def style_metro(f):
                code = str(f.get('properties', {})).upper()
                c, w = '#666', 3
                if "'A'" in code or ": A" in code: c, w = COLORS['A'], 4
                elif "'B'" in code or ": B" in code: c, w = COLORS['B'], 4
                elif "'C'" in code or ": C" in code: c, w = COLORS['C'], 4
                elif "'D'" in code or ": D" in code: c, w = COLORS['D'], 4
                return {'color': c, 'weight': w, 'opacity': 0.8}
            try:
                folium.GeoJson(data_loader.metro_geojson, name="Tracé", style_function=style_metro).add_to(layers['MetroLines'])
            except: pass

        # 4. REMPLISSAGE - MÉTRO STATIONS
        for s in ALL_STATIONS:
            icon = f"""<div style="background-color:{s['c']};color:white;width:16px;height:16px;border-radius:3px;border:1.5px solid white;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:10px;">M</div>"""
            folium.Marker(
                [s['lat'], s['lon']], 
                icon=DivIcon(html=icon, icon_size=(16,16)), 
                popup=f"<b>{s['nom']}</b>"
            ).add_to(layers['MetroStations'])

        # 5. REMPLISSAGE - CAVALIERS (CLASSIFICATION)
        if not data_loader.df_cav.empty:
            for _, row in data_loader.df_cav.iterrows():
                txt = (str(row.get('categorie_cavalier', '')) + " " + str(row.get('nom_lieu', '')) + " " + str(row.get('type', ''))).lower()
                
                c, g, r = COLORS['GENTRIFICATION'], 'Gentrification', 4
                
                if any(k in txt for k in KEYWORDS['SUPERSTITION']): c, g, r = COLORS['SUPERSTITION'], 'Superstition', 5
                elif any(k in txt for k in KEYWORDS['NUISANCE']): c, g, r = COLORS['NUISANCE'], 'Nuisance', 5
                elif any(k in txt for k in KEYWORDS['VICE']): c, g, r = COLORS['VICE'], 'Vice', 5
                
                folium.CircleMarker(
                    [row['latitude'], row['longitude']], 
                    radius=r, color=c, fill=True, fill_color=c, fill_opacity=0.7, weight=1, 
                    popup=f"<b>{row.get('nom_lieu', '?')}</b><br>{g}"
                ).add_to(layers[g])

        # 6. REMPLISSAGE - IMMO
        if not data_loader.df_immo.empty:
            for _, row in data_loader.df_immo.head(200).iterrows():
                folium.CircleMarker(
                    [row['latitude'], row['longitude']], 
                    radius=3, color=COLORS['IMMO'], fill=True, fill_opacity=0.4, weight=0, 
                    popup=f"{row.get('prix')} €"
                ).add_to(layers['Immo'])

        # 7. FINALISATION
        for l in layers.values(): l.add_to(m)

        # LE SCRIPT MARIONNETTISTE (React -> Checkbox caché)
        folium.LayerControl(position='topleft', collapsed=False).add_to(m)
        hack_script = """
        <style> .leaflet-control-layers { display: none !important; } </style>
        <script>
            window.addEventListener("message", function(event) {
                if (event.data.type === 'TOGGLE_LAYER') {
                    var targetName = event.data.name; 
                    var shouldShow = event.data.show;
                    var labels = document.querySelectorAll('.leaflet-control-layers-selector + span');
                    labels.forEach(function(label) {
                        if (label.innerText.includes(targetName)) {
                            var checkbox = label.previousElementSibling;
                            if (checkbox.checked !== shouldShow) checkbox.click();
                        }
                    });
                }
            });
        </script>
        """
        m.get_root().html.add_child(folium.Element(hack_script))

        output_path = os.path.join(self.static_dir, "map_lyon.html")
        m.save(output_path)
        print(f"✅ Map: Carte générée dans {output_path}")