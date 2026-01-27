def generate_folium_map():
    """Génère la carte HTML avec Logos Métro (CSS), Lignes, et Immo."""
    print("🗺️ Génération de la carte interactive avec Logos Métro...")
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
        print(f"❌ Erreur map : {e}")