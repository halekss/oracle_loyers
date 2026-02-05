# backend/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import pandas as pd

# Import des services
from services.data_loader import DataLoader
from services.map_generator import MapGenerator

app = FastAPI(title="Immotep API", version="Final")

# --- CONFIGURATION CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CHEMINS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    DATA_DIR = "/app/data"

STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- INSTANCIATION DES SERVICES (CORRIGÉE) ---
print(f"📂 Data Dir: {DATA_DIR}")
print(f"📂 Static Dir: {STATIC_DIR}")

data_loader = DataLoader(DATA_DIR)

# 👇 FIX : On donne à manger les deux dossiers au générateur de carte
try:
    map_generator = MapGenerator(DATA_DIR, STATIC_DIR)
except TypeError:
    # Fallback si ton MapGenerator n'attend qu'un seul argument (dépend de ton fichier service)
    print("⚠️ MapGenerator n'attendait qu'un argument, on s'adapte.")
    map_generator = MapGenerator(STATIC_DIR)


# Variable globale pour le contexte Chatbot
CONTEXTE_IMMOBILIER = ""

# --- AU DÉMARRAGE ---
@app.on_event("startup")
def startup_event():
    global CONTEXTE_IMMOBILIER
    print("🚀 Démarrage Oracle Backend...")
    
    # 1. Chargement pour la Carte
    try:
        data_loader.load_csvs()
        # On passe le data_loader au generateur
        map_generator.generate(data_loader)
    except Exception as e:
        print(f"⚠️ Warning Services: {e}")

    # 2. Chargement pour le Chatbot
    print("🔍 Préparation du cerveau d'Immotep...")
    target_file = None
    if os.path.exists(DATA_DIR):
        for file in os.listdir(DATA_DIR):
            if file.endswith(".csv"):
                target_file = os.path.join(DATA_DIR, file)
                break
    
    if target_file:
        try:
            df = pd.read_csv(target_file, sep=',')
            nb_max = 60
            if len(df) > nb_max:
                df = df.sample(nb_max)
            
            liste_compacte = ""
            for index, row in df.iterrows():
                try:
                    id_a = row.get('id_annonce', index)
                    quartier = str(row.get('quartier', 'Inconnu'))
                    prix = float(row.get('prix', row.get('loyer', 0)))
                    surf = float(row.get('surface', 0))
                    type_b = row.get('type_local', row.get('type', '?'))
                    if prix > 0 and surf > 0:
                        liste_compacte += f"[ID:{id_a}] {type_b} | {quartier} | {prix}€ | {surf}m²\n"
                except: continue
            
            CONTEXTE_IMMOBILIER = liste_compacte
            print(f"📦 Immotep est prêt ({len(liste_compacte)} caractères chargés).")
        except Exception as e:
            print(f"❌ Erreur lecture CSV Chat : {e}")
            CONTEXTE_IMMOBILIER = "Erreur chargement données."
    else:
        print(f"⚠️ Aucun fichier CSV trouvé dans {DATA_DIR}")

# --- ROUTES API ---

class ChatRequest(BaseModel):
    message: str
    history: list = []

class QuartierRequest(BaseModel):
    quartier: str
    type_local: str = "Tout"

@app.get("/api/listings")
def get_listings():
    if hasattr(data_loader, 'df_main') and data_loader.df_main is not None:
        return data_loader.df_main.head(100).fillna("").to_dict(orient="records")
    return []

@app.post("/api/quartier-stats")
def get_quartier_stats(req: QuartierRequest):
    return {"quartier": req.quartier, "prix_m2": 0, "verdict": "Analyse en cours...", "ambiance": "Inconnue"}

@app.post("/api/chat")
async def chat_with_oracle(request: ChatRequest):
    LM_STUDIO_URL = "http://host.docker.internal:1234/v1/chat/completions"
    
    system_prompt = """
    Tu es Immotep, l'agent immobilier le plus désagréable et cynique de Lyon.
    RÈGLE D'OR : UN SEUL FORMAT AUTORISÉ.
    
    FORMAT DE RÉPONSE OBLIGATOIRE :
    --------------------------------------------------
    LE CANDIDAT : [Type] à [Quartier]
    PRIX : [Prix]€ pour [Surface]m²
    VERDICT : [Paragraphe sarcastique et mordant.]
    --------------------------------------------------
    """

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": f"Base chargée :\n{CONTEXTE_IMMOBILIER}\n\nSois désagréable et précis."})
    if request.history: messages.extend(request.history[-4:])
    
    consigne = " (Utilise UNIQUEMENT le format 'LE CANDIDAT'. Sois sarcastique.)"
    messages.append({"role": "user", "content": request.message + consigne})

    payload = {
        "model": "dolphin-2.9.3-mistral-nemo-12b",
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 600,
        "stream": False
    }

    try:
        r = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        if r.status_code == 200:
            content = r.json()['choices'][0]['message']['content']
            clean_content = content.replace("ID:", "").replace("[", "").replace("]", "").strip()
            return {"response": clean_content}
        else:
            return {"response": f"Erreur IA ({r.status_code})."}
    except Exception as e:
        print(f"Erreur connexion : {e}")
        return {"response": "Immotep dort (Problème connexion Docker)."}