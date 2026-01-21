from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os

app = FastAPI()

# 1. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. CHARGEMENT DES DONNÉES
CSV_PATH = "/app/data/master_immo_final.csv"

# Variable globale pour stocker le dataframe
df = pd.DataFrame()

def load_data():
    global df
    try:
        if os.path.exists(CSV_PATH):
            # On charge le CSV
            df = pd.read_csv(CSV_PATH)
            
            # --- NETTOYAGE ET SECURISATION DES COLONNES ---
            # On vérifie si les colonnes vitales existent, sinon on les crée
            required_cols = ['latitude', 'longitude', 'prix', 'surface']
            for col in required_cols:
                if col not in df.columns:
                    print(f"⚠️ Attention : Colonne '{col}' manquante. Création d'une colonne vide.")
                    df[col] = 0
            
            # Gestion spécifique du TITRE
            if 'titre' not in df.columns:
                if 'type_bien' in df.columns:
                    df['titre'] = df['type_bien'] # On utilise le type comme titre
                else:
                    df['titre'] = "Annonce Immobilière" # Titre par défaut
            
            # On s'assure que tout est propre (pas de NaN qui font planter le JSON)
            df = df.fillna(0)
            
            print(f"✅ Données chargées : {len(df)} annonces.")
            print(f"📊 Colonnes disponibles : {list(df.columns)}")
        else:
            print("⚠️ Fichier CSV introuvable. Base vide.")
            df = pd.DataFrame(columns=["titre", "prix", "surface", "latitude", "longitude"])
    except Exception as e:
        print(f"⚠️ Erreur chargement CSV: {e}")
        df = pd.DataFrame()

# On lance le chargement au démarrage
load_data()

# 3. MODÈLE DE DONNÉES
class AnalysisRequest(BaseModel):
    address: str
    lat: float
    lon: float

# 4. LA ROUTE D'ANALYSE
@app.post("/api/analyze/vice")
def analyze_vice(request: AnalysisRequest):
    global df
    
    # Sécurité : Si la base est vide
    if df.empty:
        # On tente de recharger au cas où le fichier serait arrivé entre temps
        load_data()
        if df.empty:
             raise HTTPException(status_code=503, detail="Base de données vide ou illisible.")

    # Calcul simple de distance
    try:
        # On travaille sur une copie pour ne pas casser l'original
        temp_df = df.copy()
        
        temp_df['dist'] = np.sqrt((temp_df['latitude'] - request.lat)**2 + (temp_df['longitude'] - request.lon)**2)
        
        # On prend les 10 plus proches
        neighbors = temp_df.sort_values('dist').head(10)
        
        if neighbors.empty:
            return {"verdict": "Désert", "stats": {"prix_moyen": 0}, "message": "Aucun bien trouvé à proximité."}

        # Stats
        prix_moyen = neighbors['prix'].mean()
        surface_moyenne = neighbors['surface'].mean()
        prix_m2_moyen = (neighbors['prix'] / neighbors['surface'].replace(0, 1)).mean() # Avoid division by zero
        
        # Verdict
        verdict = "Standard"
        if prix_m2_moyen > 6000: verdict = "Quartier Riche 💎"
        elif prix_m2_moyen < 3500: verdict = "Bonne Affaire 💰"

        # Préparation des annonces pour le renvoi (Sécurisé)
        top_annonces = []
        for _, row in neighbors.iterrows():
            top_annonces.append({
                "titre": str(row['titre']),
                "prix": float(row['prix']),
                "surface": float(row['surface'])
            })

        return {
            "address": request.address,
            "coords": {"lat": request.lat, "lon": request.lon},
            "stats": {
                "prix_moyen": round(prix_moyen) if not np.isnan(prix_moyen) else 0,
                "surface_moyenne": round(surface_moyenne) if not np.isnan(surface_moyenne) else 0,
                "prix_m2": round(prix_m2_moyen) if not np.isnan(prix_m2_moyen) else 0,
                "nb_biens_analyse": len(neighbors)
            },
            "verdict": verdict,
            "top_annonces": top_annonces
        }

    except Exception as e:
        print(f"❌ Erreur pendant l'analyse : {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "Online", "columns": list(df.columns) if not df.empty else []}