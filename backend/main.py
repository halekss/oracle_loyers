from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os
import re

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# On pointe vers ton fichier PROPRE généré par le script de nettoyage
CSV_FILE_PATH = os.path.join(BASE_DIR, "data", "master_immo_final.csv")

app = FastAPI(title="Oracle Immo - Data Engine V3 (Pandas)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- VALEURS DE SECOURS (Ton code d'origine) ---
FALLBACK_PRICES = {
    "69001": 1350, "69002": 1450, "69003": 1150,
    "69004": 1250, "69005": 1200, "69006": 1300,
    "69007": 1100, "69008": 1050, "69009": 1000
}

# --- MÉMOIRE GLOBALE ---
global_df = pd.DataFrame()

@app.on_event("startup")
def load_data():
    global global_df
    if os.path.exists(CSV_FILE_PATH):
        print(f"📂 Lecture du fichier : {CSV_FILE_PATH}")
        try:
            # PANDAS : Lecture ultra-rapide
            df = pd.read_csv(CSV_FILE_PATH)
            # Nettoyage des NaN pour le JSON
            global_df = df.where(pd.notnull(df), None)
            
            # On s'assure que le CP est bien une chaine de caractère pour les filtres
            if 'cp' in global_df.columns:
                global_df['cp'] = global_df['cp'].astype(str).str.replace(r'\.0$', '', regex=True)

            print(f"✅ SUCCÈS : {len(global_df)} annonces chargées via Pandas.")
        except Exception as e:
            print(f"❌ CRASH : Erreur Pandas : {e}")
    else:
        print(f"⚠️ Fichier introuvable : {CSV_FILE_PATH}")

# --- ENDPOINT 1 : POUR LA CARTE (Indispensable) ---
@app.get("/annonces")
def get_annonces(limit: int = 2000):
    if global_df.empty:
        return {"count": 0, "data": []}
    return {"count": len(global_df), "data": global_df.head(limit).to_dict(orient="records")}

# --- ENDPOINT 2 : ANALYSE (Adapté de ton ancien code) ---
class Payload(BaseModel):
    address: str
    lat: float = 0.0
    lon: float = 0.0

@app.post("/api/analyze/vice")
def analyze(p: Payload):
    print(f"🔮 ANALYSE : {p.address}")

    # 1. Extraction du CP via Regex (Comme avant)
    cp = None
    match = re.search(r"690\d{2}", p.address)
    if match:
        cp = match.group(0)
    
    if not cp:
        cp = "69002" # Valeur défaut

    estimated_price = 0
    note = ""

    # 2. Analyse via PANDAS (Beaucoup plus simple qu'avant)
    # On filtre le tableau global pour ne garder que le bon CP
    if not global_df.empty and 'cp' in global_df.columns:
        quartier_df = global_df[global_df['cp'] == cp]
        
        if not quartier_df.empty:
            # On calcule la moyenne des prix
            avg_price = quartier_df['price'].mean()
            # On calcule la moyenne du m2 si la colonne existe
            if 'price_m2' in quartier_df.columns:
                avg_m2 = quartier_df['price_m2'].mean()
                note = f"{round(avg_m2)} €/m² (Basé sur {len(quartier_df)} annonces réelles)"
            
            estimated_price = round(avg_price) if pd.notnull(avg_price) else 0
            print(f"✅ Source : Données Réelles ({len(quartier_df)} annonces)")
        else:
            # Pas d'annonce dans ce CP -> On utilise tes FALLBACKS
            estimated_price = FALLBACK_PRICES.get(cp, 1200)
            note = "Estimation théorique (Pas de data récente)"
            print(f"⚠️ Source : Fallback")

    return {
        "score": 0,
        "message": f"Analyse pour {cp}",
        "estimated_price": estimated_price,
        "price_note": note,
        "cavaliers": {"gentrification":0, "vice":0, "nuisance":0},
        "details": {}
    }