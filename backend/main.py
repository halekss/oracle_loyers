from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
import re
import requests
import folium
from folium.features import DivIcon
import json

app = FastAPI()

# --- CONFIG ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

BASE_DIR = "/app/data"
DATA_PATH = os.path.join(BASE_DIR, "master_immo_final.csv")
CAVALIERS_PATH = os.path.join(BASE_DIR, "cavaliers_lyon.csv")

# --- CACHE GLOBAL ---
df = pd.DataFrame()
metro_lines_geojson = None

# --- 1. API GRAND LYON (LIGNES) ---
def fetch_tcl_data():
    global metro_lines_geojson
    print("📡 Connexion API Grand Lyon (Tracé Lignes)...")
    # On récupère le tracé des lignes de métro/funiculaire
    url = "https://data.grandlyon.com/geoserver/sytral/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=tcl_sytral.tcllignemf&outputFormat=application/json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            metro_lines_geojson = r.json()
            print("✅ Tracé Métro chargé.")
    except Exception as e:
        print(f"⚠️ Erreur API : {e}")

# --- 2. UTILITAIRES ---
def guess_room_count_smart(row):
    text = (str(row.get('titre', '')) + " " + str(row.get('description', ''))).lower()
    surface = float(row.get('surface', 0))
    if "studio" in text: return 1
    match_t = re.search(r'\b[tf](\d+)\b', text)
    if match_t: return int(match_t.group(1))
    if surface < 35: return 1
    if surface < 55: return 2
    if surface < 78: return 3
    if surface < 98: return 4
    return 5

# --- 3. GÉNÉRATION DE LA CARTE ---
def generate_folium_map():
    print("🗺️ Génération carte (Classification Renforcée + Métro Complet)...")
    try:
        start_lat, start_lon = 45.7640, 4.8357
        if not df.empty:
             start_lat = df['latitude'].mean()
             start_lon = df['longitude'].mean()

        m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='CartoDB dark_matter')

        # --- Calques (Noms simplifiés pour correspondance JS) ---
        layers = {
            'MetroLines': folium.FeatureGroup(name="MetroLines"),
            'MetroStations': folium.FeatureGroup(name="MetroStations"),
            'Vice': folium.FeatureGroup(name="Vice"),
            'Gentrification': folium.FeatureGroup(name="Gentrification"),
            'Nuisance': folium.FeatureGroup(name="Nuisance"),
            'Superstition': folium.FeatureGroup(name="Superstition"),
            'Immo': folium.FeatureGroup(name="Immo")
        }

        # --- A. TRACÉ MÉTRO (API) ---
        if metro_lines_geojson:
            def style_metro(f):
                code = str(f.get('properties', {})).upper()
                c = '#666'; w=3
                # Couleurs officielles TCL
                if "'A'" in code or ": A" in code: c='#e9003a'; w=4
                elif "'B'" in code or ": B" in code: c='#0073ba'; w=4
                elif "'C'" in code or ": C" in code: c='#f78e1e'; w=4
                elif "'D'" in code or ": D" in code: c='#009e49'; w=4
                return {'color': c, 'weight': w, 'opacity': 0.8}
            try:
                folium.GeoJson(metro_lines_geojson, name="Tracé", style_function=style_metro).add_to(layers['MetroLines'])
            except: pass

        # --- B. STATIONS MÉTRO (LISTE COMPLÈTE) ---
        all_stations = [
            # A (Rouge)
            {"nom": "Perrache", "lat": 45.7485, "lon": 4.8266, "c": "#e9003a"},
            {"nom": "Ampère", "lat": 45.7532, "lon": 4.8289, "c": "#e9003a"},
            {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322, "c": "#e9003a"},
            {"nom": "Cordeliers", "lat": 45.7634, "lon": 4.8356, "c": "#e9003a"},
            {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335, "c": "#e9003a"},
            {"nom": "Foch", "lat": 45.7696, "lon": 4.8427, "c": "#e9003a"},
            {"nom": "Masséna", "lat": 45.7712, "lon": 4.8524, "c": "#e9003a"},
            {"nom": "Charpennes", "lat": 45.7710, "lon": 4.8636, "c": "#e9003a"},
            {"nom": "République", "lat": 45.7711, "lon": 4.8763, "c": "#e9003a"},
            {"nom": "Gratte-Ciel", "lat": 45.7693, "lon": 4.8860, "c": "#e9003a"},
            {"nom": "Flachet", "lat": 45.7663, "lon": 4.8967, "c": "#e9003a"},
            {"nom": "Cusset", "lat": 45.7612, "lon": 4.9083, "c": "#e9003a"},
            {"nom": "L. Bonnevay", "lat": 45.7608, "lon": 4.9198, "c": "#e9003a"},
            {"nom": "Vaulx-en-Velin La Soie", "lat": 45.7607, "lon": 4.9298, "c": "#e9003a"},
            # B (Bleu)
            {"nom": "Brotteaux", "lat": 45.7663, "lon": 4.8601, "c": "#0073ba"},
            {"nom": "Part-Dieu", "lat": 45.7601, "lon": 4.8590, "c": "#0073ba"},
            {"nom": "Place Guichard", "lat": 45.7569, "lon": 4.8510, "c": "#0073ba"},
            {"nom": "Saxe-Gambetta", "lat": 45.7516, "lon": 4.8486, "c": "#0073ba"},
            {"nom": "Jean Macé", "lat": 45.7445, "lon": 4.8428, "c": "#0073ba"},
            {"nom": "Jean Jaurès", "lat": 45.7368, "lon": 4.8377, "c": "#0073ba"},
            {"nom": "Debourg", "lat": 45.7303, "lon": 4.8337, "c": "#0073ba"},
            {"nom": "Stade de Gerland", "lat": 45.7235, "lon": 4.8317, "c": "#0073ba"},
            {"nom": "Gare d'Oullins", "lat": 45.7161, "lon": 4.8138, "c": "#0073ba"},
            # C (Orange)
            {"nom": "Croix-Paquet", "lat": 45.7710, "lon": 4.8354, "c": "#f78e1e"},
            {"nom": "Croix-Rousse", "lat": 45.7745, "lon": 4.8315, "c": "#f78e1e"},
            {"nom": "Hénon", "lat": 45.7797, "lon": 4.8282, "c": "#f78e1e"},
            {"nom": "Cuire", "lat": 45.7852, "lon": 4.8338, "c": "#f78e1e"},
            # D (Vert)
            {"nom": "Gare de Vaise", "lat": 45.7797, "lon": 4.8051, "c": "#009e49"},
            {"nom": "Valmy", "lat": 45.7741, "lon": 4.8058, "c": "#009e49"},
            {"nom": "Gorge de Loup", "lat": 45.7656, "lon": 4.8021, "c": "#009e49"},
            {"nom": "Vieux Lyon", "lat": 45.7598, "lon": 4.8268, "c": "#009e49"},
            {"nom": "Guillotière", "lat": 45.7547, "lon": 4.8423, "c": "#009e49"},
            {"nom": "Garibaldi", "lat": 45.7505, "lon": 4.8580, "c": "#009e49"},
            {"nom": "Sans Souci", "lat": 45.7478, "lon": 4.8694, "c": "#009e49"},
            {"nom": "Monplaisir", "lat": 45.7454, "lon": 4.8787, "c": "#009e49"},
            {"nom": "Grange Blanche", "lat": 45.7434, "lon": 4.8763, "c": "#009e49"},
            {"nom": "Laennec", "lat": 45.7369, "lon": 4.8856, "c": "#009e49"},
            {"nom": "Mermoz-Pinel", "lat": 45.7291, "lon": 4.8953, "c": "#009e49"},
            {"nom": "Parilly", "lat": 45.7196, "lon": 4.8988, "c": "#009e49"},
            {"nom": "Gare de Vénissieux", "lat": 45.7047, "lon": 4.8879, "c": "#009e49"},
        ]
        
        for s in all_stations:
            icon = f"""<div style="background-color:{s['c']};color:white;width:16px;height:16px;border-radius:3px;border:1.5px solid white;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:10px;">M</div>"""
            folium.Marker(
                [s['lat'], s['lon']], 
                icon=DivIcon(html=icon, icon_size=(16,16)), 
                popup=f"<b>{s['nom']}</b>"
            ).add_to(layers['MetroStations'])

        # --- C. CLASSIFICATION CAVALIERS (CORRECTION VIOLET) ---
        if os.path.exists(CAVALIERS_PATH):
            df_cav = pd.read_csv(CAVALIERS_PATH)
            
            # 1. SUPERSTITION (Violet) - Liste enrichie pour ne rien rater
            KW_SUPERSTITION = [
                'cimetiere', 'cimetière', 'tombe', 'mort', 'funeraire', 
                'hopital', 'hôpital', 'clinique', 'ehpad', 'medical', 
                'eglise', 'église', 'cathedrale', 'temple', 'mosquee', 'synagogue', 
                'culte', 'chapelle', 'notre dame', 'dieu', 'croix'
            ]
            
            # 2. NUISANCE (Orange) - Aires de jeux incluses
            KW_NUISANCE = [
                'ecole', 'école', 'creche', 'crèche', 'college', 'lycee', 
                'aire de jeu', 'toboggan', 'skate', 'city stade', 'stade', 'piscine',
                'gare', 'train', 'metro', 'bus', 'tram', 'aeroport', 
                'usine', 'garage', 'essence', 'station service', 'pompier', 'police',
                'bruit', 'discotheque', 'boite de nuit', 'club'
            ]
            
            # 3. VICE (Rouge)
            KW_VICE = [
                'sex', 'strip', 'libertin', 'charme', 'sauna',
                'bar', 'pub', 'alcool', 'biere', 'vin', 
                'tabac', 'vape', 'cbd', 'chicha',
                'casino', 'pari', 'jeux', 
                'kebab', 'tacos', 'burger', 'fast food'
            ]
            
            for _, row in df_cav.iterrows():
                # On nettoie le texte pour la recherche
                txt = (str(row.get('categorie_cavalier', '')) + " " + str(row.get('nom_lieu', '')) + " " + str(row.get('type', ''))).lower()
                
                # IMPORTANT : L'ordre des 'if' détermine la couleur finale
                color = '#3498db'; group = 'Gentrification'; radius=4 # Bleu par défaut
                
                if any(k in txt for k in KW_SUPERSTITION): 
                    color='#9b59b6'; group='Superstition'; radius=5 # Violet
                elif any(k in txt for k in KW_NUISANCE): 
                    color='#f39c12'; group='Nuisance'; radius=5     # Orange
                elif any(k in txt for k in KW_VICE): 
                    color='#e74c3c'; group='Vice'; radius=5         # Rouge
                
                folium.CircleMarker(
                    [row['latitude'], row['longitude']], 
                    radius=radius, color=color, fill=True, fill_color=color, fill_opacity=0.7, weight=1, 
                    popup=f"<b>{row.get('nom_lieu', '?')}</b><br>{group}"
                ).add_to(layers[group])

        # --- D. IMMO ---
        if not df.empty:
            for _, row in df.head(200).iterrows():
                folium.CircleMarker([row['latitude'], row['longitude']], radius=3, color='#2ecc71', fill=True, fill_opacity=0.4, weight=0, popup=f"{row.get('prix')} €").add_to(layers['Immo'])

        for l in layers.values(): l.add_to(m)

        # --- E. MARIONNETTISTE (CONTROLES CACHÉS + SCRIPT) ---
        # 1. On ajoute le contrôle natif (pour que la fonctionnalité existe)
        folium.LayerControl(position='topright', collapsed=False).add_to(m)

        # 2. On le cache et on ajoute le pont JS
        hack_script = """
        <style>
            /* Cache la boîte blanche native */
            .leaflet-control-layers { display: none !important; }
        </style>
        <script>
            window.addEventListener("message", function(event) {
                var data = event.data;
                if (data.type === 'TOGGLE_LAYER') {
                    var targetName = data.name; 
                    var shouldShow = data.show;
                    
                    // On cherche dans le DOM de Leaflet la case à cocher correspondante
                    var labels = document.querySelectorAll('.leaflet-control-layers-selector + span');
                    labels.forEach(function(label) {
                        if (label.innerText.trim() === targetName) {
                            var checkbox = label.previousElementSibling;
                            if (checkbox.checked !== shouldShow) {
                                checkbox.click(); // Clic simulé
                            }
                        }
                    });
                }
            });
        </script>
        """
        m.get_root().html.add_child(folium.Element(hack_script))

        m.save(os.path.join(STATIC_DIR, "map_lyon.html"))
        print(f"✅ Carte générée (Superstition corrigée + Métro Full + Sliders).")

    except Exception as e:
        print(f"❌ Erreur map : {e}")

# --- LOAD ---
def load_all_data():
    global df
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        for c in ['latitude', 'longitude', 'prix', 'surface']:
            if c not in df.columns: df[c] = 0
        df = df.fillna(0)
        df['nb_pieces'] = df.apply(guess_room_count_smart, axis=1)
    fetch_tcl_data()
    generate_folium_map()

load_all_data()

# --- ROUTES ---
class ChatRequest(BaseModel):
    message: str
class AnalysisRequest(BaseModel):
    address: str
    lat: float
    lon: float
    filter_type: str = "all"

@app.post("/api/analyze/vice")
def analyze_vice(request: AnalysisRequest):
    return {"verdict": "Analyse OK", "stats": {}, "market_analysis": {}, "top_annonces": []}

@app.post("/api/chat")
async def chat_with_oracle(request: ChatRequest):
    LM_STUDIO_URL = "http://host.docker.internal:1234/v1/chat/completions"
    payload = {
        "model": "mistralai/mistral-7b-instruct-v0.3",
        "messages": [{"role": "system", "content": "Tu es l'Oracle."}, {"role": "user", "content": request.message}]
    }
    try:
        r = requests.post(LM_STUDIO_URL, json=payload, timeout=45)
        r.raise_for_status()
        return {"response": r.json()['choices'][0]['message']['content']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))