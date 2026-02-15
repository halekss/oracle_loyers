import folium
import pandas as pd
import os
import random
import json

# --- 1. CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR) 
DATA_DIR = os.path.join(BACKEND_DIR, 'data') 
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'public', 'data')
OUTPUT_HTML = os.path.join(FRONTEND_DATA_DIR, 'map_pings_lyon_calques.html')

IMMO_CSV = os.path.join(DATA_DIR, 'master_immo_final.csv')
POI_CSV = os.path.join(DATA_DIR, 'cavaliers_lyon.csv')
METRO_JSON = os.path.join(DATA_DIR, 'metro_lyon.json')

# --- 2. DATA & COULEURS ---
COLORS = {
    'Vice': '#e74c3c', 'Gentrification': '#3b82f6', 
    'Nuisance': '#f59e0b', 'Superstition': '#9333ea', 
    'Immo': '#22c55e'
}

METRO_COLORS = {
    'A': '#e9003a', 'B': '#0073ba', 
    'C': '#f78e1e', 'D': '#009e49', 
    'F1': '#888888', 'F2': '#888888'
}

# --- 3. CHARGEMENT DONNEES ---
# A. Immo
try:
    if os.path.exists(IMMO_CSV):
        df_immo = pd.read_csv(IMMO_CSV, sep=None, engine='python')
        df_immo.columns = df_immo.columns.str.strip().str.lower()
        for col in ['latitude', 'longitude']:
            if col in df_immo.columns: df_immo[col] = pd.to_numeric(df_immo[col], errors='coerce')
    else: df_immo = pd.DataFrame()
except: df_immo = pd.DataFrame()

# B. Cavaliers
df_poi = pd.DataFrame()
try:
    if os.path.exists(POI_CSV):
        df_poi = pd.read_csv(POI_CSV, sep=None, engine='python')
        df_poi.columns = df_poi.columns.str.strip().str.lower()
        if 'categorie_cavalier' in df_poi.columns: df_poi['type'] = df_poi['categorie_cavalier']
        elif 'type_osm' in df_poi.columns: df_poi['type'] = df_poi['type_osm']
        if 'nom_lieu' in df_poi.columns: df_poi['nom'] = df_poi['nom_lieu']
        for col in ['latitude', 'longitude']:
            if col in df_poi.columns:
                df_poi[col] = df_poi[col].astype(str).str.replace(',', '.', regex=False)
                df_poi[col] = pd.to_numeric(df_poi[col], errors='coerce')
except: pass

# --- 4. CARTE ---
print("🛑 GENERATION CARTE (METRO LIGNES AUTO)...")
m = folium.Map(location=[45.7640, 4.8357], zoom_start=13, tiles='CartoDB dark_matter', zoom_control=False)

# --- CREATION DES GROUPES ---
fg_studio = folium.FeatureGroup(name='Immo Studio/T1', show=True)
fg_t2 = folium.FeatureGroup(name='Immo T2', show=True)
fg_t3 = folium.FeatureGroup(name='Immo T3', show=True)
fg_t4 = folium.FeatureGroup(name='Immo Grand (T4+)', show=True)

# Groupe Métro Unifié
fg_metro = folium.FeatureGroup(name='Metro', show=True)

fg_vice = folium.FeatureGroup(name='Vice', show=True)
fg_gentri = folium.FeatureGroup(name='Gentrification', show=False)
fg_nuisance = folium.FeatureGroup(name='Nuisance', show=False)
fg_superstition = folium.FeatureGroup(name='Superstition', show=False)

# --- 5. GENERATION POINTS IMMO ---
for _, row in df_immo.iterrows():
    if pd.notnull(row.get('latitude')) and pd.notnull(row.get('longitude')):
        lat = row['latitude'] + random.uniform(-0.0001, 0.0001)
        lon = row['longitude'] + random.uniform(-0.0001, 0.0001)
        
        type_local = str(row.get('type_local', '')).strip()
        prix = str(row.get('prix', '?')).replace('.0', '')
        
        txt_popup = f"""
        <div style='font-family:sans-serif; min-width:140px;'>
            <h4 style='margin:0 0 5px 0; color:#22c55e; border-bottom:1px solid #334155; padding-bottom:3px;'>{type_local}</h4>
            <div style='font-size:15px; font-weight:bold; margin-bottom:5px;'>{prix} €</div>
            <div style='color:#94a3b8; font-size:12px;'>{row.get('quartier', 'Lyon')}</div>
        </div>
        """
        
        target_group = None
        if type_local == 'Studio/T1': target_group = fg_studio
        elif type_local == 'T2': target_group = fg_t2
        elif type_local == 'T3': target_group = fg_t3
        elif type_local == 'Grand (T4+)': target_group = fg_t4
        
        if target_group:
            folium.CircleMarker(
                [lat, lon], radius=5, color=COLORS['Immo'], weight=1, fill=True, fill_color=COLORS['Immo'], fill_opacity=0.8,
                popup=folium.Popup(txt_popup, max_width=300, className='oracle-popup')
            ).add_to(target_group)

# --- 6. GESTION DU MÉTRO VIA JSON (LIGNES + STATIONS) ---
if os.path.exists(METRO_JSON):
    try:
        with open(METRO_JSON, 'r', encoding='utf-8') as f:
            metro_data = json.load(f)
        
        # Dictionnaire pour stocker les coordonnées par ligne (ex: {'A': [[lat,lon], [lat,lon]...]})
        stations_by_line = {}

        # 1. DESSINER LES STATIONS (ICONES) ET MEMORISER LES POSITIONS
        count_stations = 0
        for feature in metro_data['features']:
            if feature['geometry']['type'] == 'Point':
                # Données
                props = feature['properties']
                coords = feature['geometry']['coordinates']
                lon, lat = coords[0], coords[1]
                
                nom_station = props.get('nom', 'Station')
                ligne = props.get('ligne', '?')
                
                # Sauvegarde pour le tracé de la ligne
                if ligne not in stations_by_line:
                    stations_by_line[ligne] = []
                stations_by_line[ligne].append([lat, lon])

                # Style
                color = METRO_COLORS.get(ligne, '#888888')
                popup_txt = f"<b>Station {nom_station}</b><br>Ligne {ligne}"
                
                # Icone HTML
                icon_html = f"""
                <div style="
                    width: 24px; height: 24px;
                    background: white; border-radius: 50%;
                    display: flex; align-items: center; justify-content: center;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.5);
                    border: 2px solid white;
                ">
                    <div style="
                        width: 18px; height: 18px;
                        background: {color}; border-radius: 50%;
                        display: flex; align-items: center; justify-content: center;
                        font-family: sans-serif; font-weight: bold; font-size: 10px; color: white;
                    ">{ligne}</div>
                </div>
                """
                
                folium.Marker(
                    [lat, lon],
                    icon=folium.DivIcon(html=icon_html, icon_size=(24, 24), icon_anchor=(12, 12)),
                    popup=folium.Popup(popup_txt, max_width=200, className='oracle-popup')
                ).add_to(fg_metro)
                count_stations += 1
        
        # 2. DESSINER LES LIGNES EN RELIANT LES POINTS
        # Si le fichier JSON est bien ordonné, cela reliera les stations dans l'ordre
        for ligne, coords in stations_by_line.items():
            if len(coords) > 1:
                folium.PolyLine(
                    locations=coords,
                    color=METRO_COLORS.get(ligne, '#888888'),
                    weight=4,
                    opacity=0.6,
                    smooth_factor=1.5 # Adoucit un peu les angles
                ).add_to(fg_metro)

        print(f"🚇 Métro chargé : {len(stations_by_line)} lignes tracées, {count_stations} stations.")

    except Exception as e:
        print(f"⚠️ Erreur lors du traitement de metro_lyon.json : {e}")

# --- 7. CAVALIERS ---
mapping_simple = {'vice': (fg_vice, COLORS['Vice']), 'gentrification': (fg_gentri, COLORS['Gentrification']), 'nuisance': (fg_nuisance, COLORS['Nuisance']), 'superstition': (fg_superstition, COLORS['Superstition'])}
if 'type' in df_poi.columns:
    for _, row in df_poi.iterrows():
        raw_type = str(row.get('type', '')).lower().strip()
        target_config = None
        for key, config in mapping_simple.items():
            if key in raw_type:
                target_config = config
                break
        if target_config and pd.notnull(row.get('latitude')):
            group, color_hex = target_config
            
            # Nettoyage Type (ex: "Vice - Bar" -> "Bar")
            if ' - ' in raw_type:
                clean_type = raw_type.split(' - ')[-1].title()
            else:
                clean_type = raw_type.title()

            txt_popup = f"""
            <div style='font-size: 13px; line-height: 1.4;'>
                <b style='font-size: 15px; color: #f8fafc;'>{row.get('nom', clean_type)}</b><br>
                <span style='color: {color_hex}; font-weight: bold;'>{clean_type}</span>
            </div>
            """
            
            folium.CircleMarker(
                [row['latitude'], row['longitude']], radius=5, color=color_hex, weight=1, fill=True, fill_color=color_hex, fill_opacity=0.8,
                popup=folium.Popup(txt_popup, max_width=200, className='oracle-popup')
            ).add_to(group)

# --- 8. RENDU ---
fg_studio.add_to(m)
fg_t2.add_to(m)
fg_t3.add_to(m)
fg_t4.add_to(m)
fg_metro.add_to(m) # Groupe Unique
fg_vice.add_to(m)
fg_gentri.add_to(m)
fg_nuisance.add_to(m)
fg_superstition.add_to(m)
folium.LayerControl(collapsed=False).add_to(m)

html = m.get_root().render()

# --- 9. HACK CSS/JS (JUSTE POPUPS + CONTROLE CALQUES) ---
hack = """
<style>
    .leaflet-control-layers { display: none !important; }

    /* STYLE POPUP DARK */
    .leaflet-popup-content-wrapper, .leaflet-popup-tip {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
        border-radius: 12px !important;
    }
    .leaflet-popup-close-button { color: #94a3b8 !important; }
    .leaflet-popup-close-button:hover { color: #f8fafc !important; }
    .leaflet-interactive { cursor: pointer !important; }
</style>

<script>
window.addEventListener("message", function(e) {
    if(e.data.type==='TOGGLE_LAYER'){
        var labels=document.getElementsByTagName('label');
        for(var i=0;i<labels.length;i++){
            var labelText = labels[i].textContent.trim();
            if(labelText === e.data.name || labelText.includes(e.data.name)){
               var box=labels[i].querySelector('input');
               if(box && box.checked!==e.data.show) box.click();
            }
        }
    }
});
</script>
</body>
"""

html = html.replace('</body>', hack)

if not os.path.exists(FRONTEND_DATA_DIR):
    os.makedirs(FRONTEND_DATA_DIR)

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"🎉 TERMINÉ : {OUTPUT_HTML} (Métro : Lignes reliées automatiquement)")