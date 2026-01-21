from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os

app = FastAPI()

# --- 1. CONFIGURATION CORS ---
# Permet au Frontend (port 5173) de parler au Backend (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod, remplacer par ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. CHARGEMENT DES DONNÉES ---
CSV_PATH = "/app/data/master_immo_final.csv"
df = pd.DataFrame()

def load_data():
    """Charge et nettoie les données CSV au démarrage."""
    global df
    try:
        if os.path.exists(CSV_PATH):
            # Chargement du fichier
            df = pd.read_csv(CSV_PATH)
            
            # -- SÉCURISATION DES COLONNES --
            # On vérifie que les colonnes vitales existent, sinon on met des valeurs par défaut
            required_cols = ['latitude', 'longitude', 'prix', 'surface']
            for col in required_cols:
                if col not in df.columns:
                    print(f"⚠️ Colonne manquante : '{col}'. Ajout de valeurs par défaut.")
                    df[col] = 0
            
            # Gestion intelligente du TITRE
            if 'titre' not in df.columns:
                if 'type_bien' in df.columns:
                    df['titre'] = df['type_bien']
                elif 'type' in df.columns:
                    df['titre'] = df['type']
                else:
                    df['titre'] = "Annonce Immobilière"

            # Nettoyage des valeurs vides (NaN) pour éviter les erreurs JSON
            df = df.fillna(0)
            
            print(f"✅ Données chargées avec succès : {len(df)} annonces en mémoire.")
            print(f"📊 Colonnes disponibles : {list(df.columns)}")
        else:
            print("⚠️ Fichier CSV introuvable dans /app/data/. La base est vide.")
            df = pd.DataFrame(columns=["titre", "prix", "surface", "latitude", "longitude"])
            
    except Exception as e:
        print(f"❌ Erreur critique lors du chargement CSV : {e}")
        df = pd.DataFrame()

# On charge les données dès le lancement de l'application
load_data()

# --- 3. MODÈLE DE DONNÉES (Input) ---
class AnalysisRequest(BaseModel):
    address: str
    lat: float
    lon: float

# --- 4. API ENDPOINTS ---

@app.get("/")
def read_root():
    """Route de santé pour vérifier que l'API tourne."""
    return {
        "status": "Oracle Backend Online 🟢", 
        "data_count": len(df),
        "columns": list(df.columns) if not df.empty else []
    }

@app.post("/api/analyze/vice")
def analyze_vice(request: AnalysisRequest):
    """
    Reçoit une coordonnée GPS, cherche les biens autour, et renvoie des stats.
    Logique : Rayon de 500m, sinon élargissement aux 10 plus proches.
    """
    global df
    
    # Si la base est vide, on essaie de recharger une dernière fois
    if df.empty:
        load_data()
        if df.empty:
             raise HTTPException(status_code=503, detail="Base de données vide. Vérifiez le dossier data.")

    try:
        # On travaille sur une copie pour ne pas modifier l'original
        temp_df = df.copy()
        
        # 1. Calcul de la distance pour chaque annonce (Formule Pythagore simplifiée)
        # Note : Sur de petites distances à Lyon, c'est suffisant et très rapide.
        temp_df['dist'] = np.sqrt((temp_df['latitude'] - request.lat)**2 + (temp_df['longitude'] - request.lon)**2)
        
        # 2. LOGIQUE DE RAYON DYNAMIQUE
        # 0.0045 degrés équivaut environ à 500 mètres à Lyon
        RAYON_500M = 0.0045
        
        # On essaie de prendre tout ce qui est dans le quartier (500m)
        neighbors = temp_df[temp_df['dist'] <= RAYON_500M]
        
        # Si le quartier est désert (moins de 5 annonces), on élargit la recherche
        mode_recherche = "Rayon 500m"
        if len(neighbors) < 5:
            print(f"⚠️ Peu de données ({len(neighbors)}) à 500m. Élargissement aux 10 plus proches.")
            neighbors = temp_df.sort_values('dist').head(10)
            mode_recherche = "10 plus proches"
        
        if neighbors.empty:
            return {
                "verdict": "Zone inconnue", 
                "stats": {"prix_moyen": 0}, 
                "message": "Aucune donnée disponible ici."
            }

        # 3. CALCUL DES STATISTIQUES
        prix_moyen = neighbors['prix'].mean()
        surface_moyenne = neighbors['surface'].mean()
        
        # Calcul du prix au m2 (avec sécurité division par zéro)
        # On calcule la moyenne des prix/m2 individuels pour plus de précision locale
        neighbors['temp_m2'] = neighbors['prix'] / neighbors['surface'].replace(0, 1)
        prix_m2_moyen = neighbors['temp_m2'].mean()
        
        # 4. GÉNÉRATION DU VERDICT (Ajusté pour des loyers)
        verdict = "Standard"
        if prix_m2_moyen > 25: 
            verdict = "Quartier Prisé 💎"
        elif prix_m2_moyen < 16: 
            verdict = "Abordable 💰"
        elif prix_m2_moyen > 35:
            verdict = "Zone de Luxe ✨"

        # 5. PRÉPARATION DE LA LISTE D'ANNONCES (Top 10 max pour l'affichage)
        top_annonces = []
        for _, row in neighbors.head(10).iterrows():
            top_annonces.append({
                "titre": str(row.get('titre', 'Appartement')),
                "prix": float(row['prix']),
                "surface": float(row['surface']),
                "lien": str(row.get('url', '#')) # Si tu as une colonne URL
            })

        print(f"🔮 ANALYSE : {request.address} | Mode: {mode_recherche} | Biens: {len(neighbors)}")

        # 6. ENVOI DE LA RÉPONSE JSON
        return {
            "address": request.address,
            "coords": {"lat": request.lat, "lon": request.lon},
            "stats": {
                "prix_moyen": round(prix_moyen),
                "surface_moyenne": round(surface_moyenne),
                "prix_m2": round(prix_m2_moyen, 1),
                "nb_biens_analyse": len(neighbors)
            },
            "verdict": verdict,
            "top_annonces": top_annonces
        }

    except Exception as e:
        print(f"❌ Erreur interne pendant l'analyse : {e}")
        raise HTTPException(status_code=500, detail=str(e))