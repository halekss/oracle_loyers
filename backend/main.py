from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. CONFIGURATION DES DONNÉES ---
BASE_DIR = "/app/data"
DATA_PATH = os.path.join(BASE_DIR, "master_immo_final.csv")

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

# --- 3. CHARGEMENT AU DÉMARRAGE ---

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

# --- 4. ANALYSE ---

class AnalysisRequest(BaseModel):
    address: str
    lat: float
    lon: float
    filter_type: str = "all"

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
        
        # On prend TOUT ce qui est dans le rayon (Pas de limite à 10)
        RAYON_500M = 0.0045
        neighbors = temp_df[temp_df['dist'] <= RAYON_500M]
        
        # Fallback de sécurité : si le rayon est vide, on prend les 5 plus proches quand même
        if len(neighbors) < 3:
            neighbors = temp_df.sort_values('dist').head(5)

        if neighbors.empty:
             return {"verdict": "Désert", "stats": {"prix_moyen": 0}}

        # 3. STATISTIQUES COMPLÈTES (Moyenne, Min, Max)
        prix_moyen = neighbors['prix'].mean()
        surface_moyenne = neighbors['surface'].mean()
        my_m2_avg = (neighbors['prix'] / neighbors['surface'].replace(0, 1)).mean()
        
        # Nouveaux indicateurs
        prix_min = neighbors['prix'].min()
        prix_max = neighbors['prix'].max()

        # 4. COMPARAISON MARCHÉ (Avec tes fichiers CSV spécifiques)
        ref_price = 0
        market_label = "Pas de Réf."
        diff_pct = 0
        target_insee = "Inconnu"
        
        # Choix du bon fichier de référence
        ref_key = request.filter_type if request.filter_type in ref_datasets else "all"
        current_ref_df = ref_datasets.get(ref_key)

        # Recherche code INSEE
        try:
            detected_zip = str(int(neighbors.iloc[0]['code_postal']))
            target_insee = get_insee_from_zip(detected_zip)
        except:
            target_insee = "69383" # Fallback

        if current_ref_df is not None and not current_ref_df.empty:
            match_row = current_ref_df[current_ref_df['INSEE_C'] == target_insee]
            if not match_row.empty:
                ref_price = match_row.iloc[0]['price_ref']
                diff_pct = ((my_m2_avg - ref_price) / ref_price) * 100
                
                if diff_pct > 15: market_label = "Surchcoté 🚩"
                elif diff_pct > 5: market_label = "Un peu cher"
                elif diff_pct < -10: market_label = "Bonne Affaire 💎"
                else: market_label = "Prix Marché ✅"
        
        # 5. LISTE COMPLÈTE DES ANNONCES (Sans limite de nombre)
        # On renvoie tout pour que tu puisses voir la réalité du marché
        top_annonces = []
        for _, row in neighbors.iterrows(): # Plus de .head(10) ici !
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
                "prix_min": round(prix_min),  # Ajouté
                "prix_max": round(prix_max),  # Ajouté
                "surface_moyenne": round(surface_moyenne),
                "prix_m2": round(my_m2_avg, 1),
                "nb_biens_analyse": len(neighbors)
            },
            "market_analysis": {
                "ref_price": round(ref_price, 1),
                "diff_percent": round(diff_pct, 1),
                "label": market_label,
                "dataset_used": ref_key
            },
            "verdict": market_label,
            "top_annonces": top_annonces
        }

    except Exception as e:
        print(f"❌ Erreur : {e}")
        raise HTTPException(status_code=500, detail=str(e))