import folium
import pandas as pd
import os
import json
import random

# --- 1. CONFIGURATION DES CHEMINS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR) 
DATA_DIR = os.path.join(BACKEND_DIR, 'data') # Source (Backend)

# Cible : Frontend/public/data
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'public', 'data')
OUTPUT_HTML = os.path.join(FRONTEND_DATA_DIR, 'map_pings_lyon_calques.html')

# Fichiers Sources
IMMO_CSV = os.path.join(DATA_DIR, 'master_immo_final.csv')
POI_CSV = os.path.join(DATA_DIR, 'cavaliers_lyon.csv')
METRO_JSON = os.path.join(DATA_DIR, 'metro_lyon.json')

print("🛑 DEBUT GENERATION CARTE (MODE FILTRES SÉPARÉS)...")
print(f"📂 Source : {DATA_DIR}")

# --- 2. CONFIGURATION COULEURS & DATA ---
COLORS = {
    'Vice': '#e74c3c',           # Rouge
    'Gentrification': '#3b82f6', # Bleu
    'Nuisance': '#f59e0b',       # Orange
    'Superstition': '#9333ea',   # Violet
    'Immo': '#22c55e'            # Vert
}

# Données Stations Métro (En dur)
LYON_STATIONS = [
    {"nom": "Perrache", "lat": 45.74846, "lon": 4.82664, "c": "#e9003a", "ligne": "A"},
    {"nom": "Ampère - Victor Hugo", "lat": 45.75333, "lon": 4.82962, "c": "#e9003a", "ligne": "A"},
    {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322, "c": "#e9003a", "ligne": "A"},
    {"nom": "Cordeliers", "lat": 45.7634, "lon": 4.8358, "c": "#e9003a", "ligne": "A"},
    {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "c": "#e9003a", "ligne": "A"},
    {"nom": "Foch", "lat": 45.7696, "lon": 4.8443, "c": "#e9003a", "ligne": "A"},
    {"nom": "Masséna", "lat": 45.7708, "lon": 4.8509, "c": "#e9003a", "ligne": "A"},
    {"nom": "Charpennes", "lat": 45.7712, "lon": 4.8633, "c": "#e9003a", "ligne": "A"},
    {"nom": "Charpennes", "lat": 45.7712, "lon": 4.8633, "c": "#0073ba", "ligne": "B"},
    {"nom": "Part-Dieu", "lat": 45.7611, "lon": 4.8573, "c": "#0073ba", "ligne": "B"},
    {"nom": "Place Guichard", "lat": 45.7588, "lon": 4.8454, "c": "#0073ba", "ligne": "B"},
    {"nom": "Saxe - Gambetta", "lat": 45.7516, "lon": 4.8488, "c": "#0073ba", "ligne": "B"},
    {"nom": "Jean Macé", "lat": 45.7449, "lon": 4.8427, "c": "#0073ba", "ligne": "B"},
    {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "c": "#f78e1e", "ligne": "C"},
    {"nom": "Croix-Paquet", "lat": 45.7704, "lon": 4.8361, "c": "#f78e1e", "ligne": "C"},
    {"nom": "Croix-Rousse", "lat": 45.7744, "lon": 4.8315, "c": "#f78e1e", "ligne": "C"},
    {"nom": "Hénon", "lat": 45.7803, "lon": 4.8291, "c": "#f78e1e", "ligne": "C"},
    {"nom": "Cuire", "lat": 45.7852, "lon": 4.8339, "c": "#f78e1e", "ligne": "C"},
    {"nom": "Vieux Lyon", "lat": 45.7601, "lon": 4.8261, "c": "#009e49", "ligne": "D"},
    {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322, "c": "#009e49", "ligne": "D"},
    {"nom": "Guillotière", "lat": 45.7554, "lon": 4.8424, "c": "#009e49", "ligne": "D"},
    {"nom": "Saxe - Gambetta", "lat": 45.7516, "lon": 4.8488, "c": "#009e49", "ligne": "D"},
    {"nom": "Garibaldi", "lat": 45.7507, "lon": 4.8569, "c": "#009e49", "ligne": "D"},
    {"nom": "Sans Souci", "lat": 45.7479, "lon": 4.8638, "c": "#009e49", "ligne": "D"},
    {"nom": "Monplaisir - Lumière", "lat": 45.7456, "lon": 4.8723, "c": "#009e49", "ligne": "D"},
    {"nom": "Grange Blanche", "lat": 45.7434, "lon": 4.8778, "c": "#009e49", "ligne": "D"},
    {"nom": "Valmy", "lat": 45.7745, "lon": 4.8055, "c": "#009e49", "ligne": "D"},
    {"nom": "Gare de Vaise", "lat": 45.7797, "lon": 4.8037, "c": "#009e49", "ligne": "D"}
]

# --- 3. CHARGEMENT IMMO ---
try:
    if os.path.exists(IMMO_CSV):
        df_immo = pd.read_csv(IMMO_CSV, sep=None, engine='python')
        df_immo.columns = df_immo.columns.str.strip().str.lower()
        for col in ['latitude', 'longitude']:
            if col in df_immo.columns:
                df_immo[col] = pd.to_numeric(df_immo[col], errors='coerce')
        print(f"✅ IMMO : {len(df_immo)} annonces.")
    else:
        print("❌ IMMO INTROUVABLE")
        df_immo = pd.DataFrame()
except Exception as e:
    print(f"❌ ERREUR IMMO: {e}")
    df_immo = pd.DataFrame()

# --- 4. CHARGEMENT CAVALIERS (POI) ---
df_poi = pd.DataFrame()
try:
    if os.path.exists(POI_CSV):
        df_poi = pd.read_csv(POI_CSV, sep=None, engine='python')
        df_poi.columns = df_poi.columns.str.strip().str.lower()

        # Mapping Colonnes
        if 'categorie_cavalier' in df_poi.columns: df_poi['type'] = df_poi['categorie_cavalier']
        elif 'type_osm' in df_poi.columns: df_poi['type'] = df_poi['type_osm']
        elif 'type_local' in df_poi.columns: df_poi['type'] = df_poi['type_local']
        
        if 'nom_lieu' in df_poi.columns: df_poi['nom'] = df_poi['nom_lieu']
        
        # Nettoyage coordonnées
        for col in ['latitude', 'longitude']:
            if col in df_poi.columns:
                df_poi[col] = df_poi[col].astype(str).str.replace(',', '.', regex=False)
                df_poi[col] = pd.to_numeric(df_poi[col], errors='coerce')

        print(f"✅ CAVALIERS : {len(df_poi)} lieux.")
    else:
        print("❌ CAVALIERS INTROUVABLE")
except Exception as e:
    print(f"❌ ERREUR CAVALIERS: {e}")

# --- 5. INITIALISATION CARTE ---
m = folium.Map(location=[45.7640, 4.8357], zoom_start=13, tiles='CartoDB dark_matter', zoom_control=False)

# --- CREATION DES CALQUES (SEPARES) ---
fg_immo = folium.FeatureGroup(name='Immo', show=True)

# ICI : Séparation demandée
fg_metro_lignes = folium.FeatureGroup(name='Metro Lignes', show=True)
fg_metro_stations = folium.FeatureGroup(name='Metro Stations', show=True)

fg_vice = folium.FeatureGroup(name='Vice', show=True)
fg_gentri = folium.FeatureGroup(name='Gentrification', show=False)
fg_nuisance = folium.FeatureGroup(name='Nuisance', show=False)
fg_superstition = folium.FeatureGroup(name='Superstition', show=False)

# --- 6. PLACEMENT IMMO ---
count_immo = 0
for _, row in df_immo.iterrows():
    if pd.notnull(row.get('latitude')) and pd.notnull(row.get('longitude')):
        lat = row['latitude'] + random.uniform(-0.0001, 0.0001)
        lon = row['longitude'] + random.uniform(-0.0001, 0.0001)
        popup = f"{row.get('type_local','Bien')} - {row.get('prix','?')}€"
        
        folium.CircleMarker(
            [lat, lon], radius=3, color=COLORS['Immo'], fill=True, fill_color=COLORS['Immo'], fill_opacity=0.8, popup=popup
        ).add_to(fg_immo)
        count_immo += 1
print(f"👉 {count_immo} points IMMO placés.")

# --- 7. PLACEMENT MÉTRO ---

# A. Les Lignes (Dans fg_metro_lignes)
if os.path.exists(METRO_JSON):
    try:
        def style_metro(feature):
            line = str(feature['properties'].get('ligne', '')).upper()
            c = '#888'
            if 'A' in line: c='#e9003a'
            elif 'B' in line: c='#0073ba'
            elif 'C' in line: c='#f78e1e'
            elif 'D' in line: c='#009e49'
            return {'color': c, 'weight': 4, 'opacity': 0.7}
        folium.GeoJson(METRO_JSON, name="Metro Lignes", style_function=style_metro).add_to(fg_metro_lignes)
        print("👉 Lignes Métro tracées.")
    except Exception as e:
        print(f"⚠️ Erreur Lignes Métro: {e}")

# B. Les Stations (Dans fg_metro_stations)
count_stations = 0
for station in LYON_STATIONS:
    folium.CircleMarker(
        location=[station['lat'], station['lon']],
        radius=5,           
        color='white',      
        weight=2,
        fill=True,
        fill_color=station['c'],
        fill_opacity=1,
        popup=f"Métro {station['ligne']} - {station['nom']}"
    ).add_to(fg_metro_stations)
    count_stations += 1
print(f"👉 {count_stations} Stations Métro placées.")

# --- 8. PLACEMENT CAVALIERS ---
mapping_simple = {
    'vice': (fg_vice, COLORS['Vice']),
    'gentrification': (fg_gentri, COLORS['Gentrification']),
    'nuisance': (fg_nuisance, COLORS['Nuisance']),
    'superstition': (fg_superstition, COLORS['Superstition'])
}

count_poi = 0
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
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=3,               
                color=color_hex,        
                fill=True,
                fill_color=color_hex,
                fill_opacity=0.8,
                weight=1,               
                popup=row.get('nom', raw_type)
            ).add_to(group)
            count_poi += 1

print(f"👉 {count_poi} Cavaliers (Points) placés.")

# --- 9. FINALISATION ---
fg_immo.add_to(m)

# Ajout des DEUX groupes Métro séparément
fg_metro_lignes.add_to(m)
fg_metro_stations.add_to(m)

fg_vice.add_to(m)
fg_gentri.add_to(m)
fg_nuisance.add_to(m)
fg_superstition.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

html = m.get_root().render()

# Hack JS pour React
# Note: React enverra probablement "Metro" si tu ne changes pas ton frontend.
# Le script JS ci-dessous cherche un label qui *contient* le nom.
# Donc si React envoie "Metro", il trouvera "Metro Lignes" ET "Metro Stations".
# C'est parfait : le bouton unique contrôlera les deux en même temps pour l'instant,
# mais ils sont bien séparés dans la structure de la carte si tu veux affiner plus tard.
hack = """
<style>.leaflet-control-layers {display:none!important;}</style>
<script>
window.addEventListener("message", function(e) {
    if(e.data.type==='TOGGLE_LAYER'){
        var labels=document.getElementsByTagName('label');
        for(var i=0;i<labels.length;i++){
            if(labels[i].textContent.trim().includes(e.data.name)){
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

print(f"🎉 TERMINÉ : {OUTPUT_HTML}")