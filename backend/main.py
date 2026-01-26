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

app = FastAPI()

# --- 0. CONFIGURATION CORS & STATIC ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Création du dossier static pour la carte si inexistant
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# On rend le dossier "static" accessible via http://localhost:8000/static
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- 1. CONFIGURATION DES DONNÉES ---
BASE_DIR = "/app/data"
DATA_PATH = os.path.join(BASE_DIR, "master_immo_final.csv")
CAVALIERS_PATH = os.path.join(BASE_DIR, "cavaliers_lyon.csv") # Pour la carte

# Mapping des fichiers de référence
REF_FILES = {
    "t1": "lyon_pred-app_t1_t2.csv",
    "t2": "lyon_pred-app_t1_t2.csv",
    "t3": "lyon_pred-app_t3.csv",
    "t4+": "lyon_pred-app_appartements.csv",
    "all": "lyon_pred-app_appartements.csv",
    "house": "lyon_pred-maison.csv"
}

df = pd.DataFrame()
ref_datasets = {}

# --- 2. FONCTIONS UTILITAIRES ---

def get_insee_from_zip(zip_code):
    """Convertit Code Postal -> Code INSEE."""
    zip_str = str(zip_code).strip()
    if zip_str.startswith("6900"):
        try:
            arrondissement = int(zip_str[-1])
            if 1 <= arrondissement <= 9:
                return f"6938{arrondissement}"
        except: pass
    if zip_str == "69100": return "69266" # Villeurbanne
    return zip_str

def guess_room_count_smart(row):
    """Devine le nombre de pièces (Texte > Surface)."""
    text = (str(row.get('titre', '')) + " " + str(row.get('description', ''))).lower()
    surface = float(row.get('surface', 0))
    
    if "studio" in text: return 1
    match_t = re.search(r'\b[tf](\d+)\b', text)
    if match_t: return int(match_t.group(1))
    match_p = re.search(r'(\d+)\s*(?:pièce|p\b)', text)
    if match_p: return int(match_p.group(1))
    
    if surface < 35: return 1
    if surface < 55: return 2
    if surface < 78: return 3
    if surface < 98: return 4
    return 5

# --- 3. GÉNÉRATION DE LA CARTE (FOLIUM) ---

def generate_folium_map():
    """Génère la carte HTML avec calques et la sauvegarde dans static/."""
    print("🗺️ Génération de la carte interactive...")
    try:
        # Centre par défaut sur Lyon
        start_lat, start_lon = 45.7640, 4.8357
        if not df.empty:
             start_lat = df['latitude'].mean()
             start_lon = df['longitude'].mean()

        m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='CartoDB dark_matter')

        # Création des groupes de calques
        layers = {
            'Vice': folium.FeatureGroup(name="🔴 Vice (Bars, Sex-shops...)"),
            'Gentrification': folium.FeatureGroup(name="🔵 Gentrification (Bio, Yoga...)"),
            'Immo': folium.FeatureGroup(name="🏠 Immobilier (Top 200)")
        }

        # 1. Ajout des Cavaliers (Lieux d'intérêt)
        if os.path.exists(CAVALIERS_PATH):
            df_cav = pd.read_csv(CAVALIERS_PATH)
            for _, row in df_cav.iterrows():
                cat = str(row.get('categorie_cavalier', 'Autre')).lower()
                
                # Logique de couleur
                color = '#95a5a6' # Gris par défaut
                group_key = 'Gentrification'
                
                if 'vice' in cat or 'sex' in cat or 'bar' in cat:
                    color = '#e74c3c' # Rouge
                    group_key = 'Vice'
                elif 'gentrification' in cat or 'bio' in cat or 'yoga' in cat:
                    color = '#3498db' # Bleu
                    group_key = 'Gentrification'

                popup_html = f"<b>{row.get('nom_lieu', '?')}</b><br>{cat}"
                
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=5,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    popup=folium.Popup(popup_html, max_width=200)
                ).add_to(layers[group_key])

        # 2. Ajout de l'Immobilier (Limité à 200 pour la perf)
        if not df.empty:
            for _, row in df.head(200).iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=3,
                    color='#2ecc71', # Vert
                    fill=True,
                    fill_opacity=0.6,
                    weight=0,
                    popup=f"{row.get('prix')} €<br>{row.get('surface')} m²"
                ).add_to(layers['Immo'])

        # Ajout des calques à la carte
        for layer in layers.values():
            layer.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        
        # Sauvegarde dans le dossier static servi par FastAPI
        output_path = os.path.join(STATIC_DIR, "map_lyon.html")
        m.save(output_path)
        print(f"✅ Carte générée : http://localhost:8000/static/map_lyon.html")

    except Exception as e:
        print(f"❌ Erreur map : {e}")

# --- 4. CHARGEMENT AU DÉMARRAGE ---

def load_all_data():
    global df, ref_datasets
    try:
        if os.path.exists(DATA_PATH):
            df = pd.read_csv(DATA_PATH)
            cols = ['latitude', 'longitude', 'prix', 'surface']
            for c in cols:
                if c not in df.columns: df[c] = 0
            df = df.fillna(0)
            df['nb_pieces'] = df.apply(guess_room_count_smart, axis=1)
            print(f"✅ Annonces chargées : {len(df)}")
            
            # Une fois les données chargées, on génère la carte
            generate_folium_map()
        else:
            print("⚠️ CSV Annonces introuvable.")
    except Exception as e:
        print(f"❌ Erreur Annonces : {e}")

    for key, filename in REF_FILES.items():
        path = os.path.join(BASE_DIR, filename)
        try:
            if os.path.exists(path):
                # Lecture CSV format français (;)
                ref_df = pd.read_csv(path, sep=';', dtype={'INSEE_C': str})
                if 'loypredm2' in ref_df.columns:
                    if ref_df['loypredm2'].dtype == 'object':
                        ref_df['price_ref'] = ref_df['loypredm2'].str.replace(',', '.').astype(float)
                    else:
                        ref_df['price_ref'] = ref_df['loypredm2']
                ref_datasets[key] = ref_df
                print(f"   👉 Réf chargée : {key}")
        except Exception as e:
            print(f"   ❌ Erreur Réf {key} : {e}")

load_all_data()

# --- 5. ROUTES API ---

class AnalysisRequest(BaseModel):
    address: str
    lat: float
    lon: float
    filter_type: str = "all"

class ChatRequest(BaseModel):
    message: str

@app.post("/api/analyze/vice")
def analyze_vice(request: AnalysisRequest):
    global df
    if df.empty: load_all_data()

    try:
        # 1. FILTRE TYPE
        temp_df = df.copy()
        if request.filter_type == "t1": temp_df = temp_df[temp_df['nb_pieces'] == 1]
        elif request.filter_type == "t2": temp_df = temp_df[temp_df['nb_pieces'] == 2]
        elif request.filter_type == "t3": temp_df = temp_df[temp_df['nb_pieces'] == 3]
        elif request.filter_type == "t4+": temp_df = temp_df[temp_df['nb_pieces'] >= 4]

        if temp_df.empty:
             return {"verdict": "Aucune offre", "stats": {"prix_moyen": 0}, "message": "Aucun bien de ce type."}

        # 2. DISTANCE (Rayon 500m)
        temp_df['dist'] = np.sqrt((temp_df['latitude'] - request.lat)**2 + (temp_df['longitude'] - request.lon)**2)
        RAYON_500M = 0.0045
        neighbors = temp_df[temp_df['dist'] <= RAYON_500M]
        
        if len(neighbors) < 3:
            neighbors = temp_df.sort_values('dist').head(5)

        if neighbors.empty:
             return {"verdict": "Désert", "stats": {"prix_moyen": 0}}

        # 3. STATISTIQUES
        prix_moyen = neighbors['prix'].mean()
        surface_moyenne = neighbors['surface'].mean()
        my_m2_avg = (neighbors['prix'] / neighbors['surface'].replace(0, 1)).mean()
        prix_min = neighbors['prix'].min()
        prix_max = neighbors['prix'].max()

        # 4. COMPARAISON MARCHÉ
        ref_price = 0
        market_label = "Pas de Réf."
        diff_pct = 0
        
        ref_key = request.filter_type if request.filter_type in ref_datasets else "all"
        current_ref_df = ref_datasets.get(ref_key)

        try:
            detected_zip = str(int(neighbors.iloc[0]['code_postal']))
            target_insee = get_insee_from_zip(detected_zip)
        except:
            target_insee = "69383"

        if current_ref_df is not None and not current_ref_df.empty:
            match_row = current_ref_df[current_ref_df['INSEE_C'] == target_insee]
            if not match_row.empty:
                ref_price = match_row.iloc[0]['price_ref']
                diff_pct = ((my_m2_avg - ref_price) / ref_price) * 100
                
                if diff_pct > 15: market_label = "Surchcoté 🚩"
                elif diff_pct > 5: market_label = "Un peu cher"
                elif diff_pct < -10: market_label = "Bonne Affaire 💎"
                else: market_label = "Prix Marché ✅"
        
        top_annonces = []
        for _, row in neighbors.iterrows():
            top_annonces.append({
                "titre": f"T{int(row['nb_pieces'])} - {row['surface']}m²",
                "prix": float(row['prix']),
                "surface": float(row['surface']),
                "lien": str(row.get('url', '#'))
            })

        return {
            "address": request.address,
            "coords": {"lat": request.lat, "lon": request.lon},
            "stats": {
                "prix_moyen": round(prix_moyen),
                "prix_min": round(prix_min),
                "prix_max": round(prix_max),
                "surface_moyenne": round(surface_moyenne),
                "prix_m2": round(my_m2_avg, 1),
                "nb_biens_analyse": len(neighbors)
            },
            "market_analysis": {
                "ref_price": round(ref_price, 1),
                "diff_percent": round(diff_pct, 1),
                "label": market_label
            },
            "verdict": market_label,
            "top_annonces": top_annonces
        }

    except Exception as e:
        print(f"❌ Erreur : {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_with_oracle(request: ChatRequest):
    """Route pour discuter avec l'Oracle via LM Studio."""
    
    # ⚠️ IMPORTANT : Si host.docker.internal ne marche pas,
    # remplace par ton IP locale (ex: http://192.168.1.45:1234...)
    LM_STUDIO_URL = "http://host.docker.internal:1234/v1/chat/completions"
    
    payload = {
        "model": "mistralai/mistral-7b-instruct-v0.3",
        "messages": [
            {
                "role": "system", 
                "content": "Tu es l'Oracle des loyers de Lyon. Expert immo, cynique, sombre et méprisant. Tu réponds en français."
            },
            {"role": "user", "content": request.message}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=45)
        response.raise_for_status()
        return {"response": response.json()['choices'][0]['message']['content']}
    except Exception as e:
        print(f"❌ Erreur Oracle : {e}")
        raise HTTPException(status_code=500, detail="L'Oracle local est débranché (LM Studio).")