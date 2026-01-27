# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests

# Import des services qu'on vient de créer
from services.data_loader import DataLoader
from services.map_generator import MapGenerator

app = FastAPI()

# --- CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chemins (Gestion Docker et Local)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
if not os.path.exists(DATA_DIR):
    DATA_DIR = "/app/data" # Fallback Docker

STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- INSTANCIATION DES SERVICES ---
# On crée les objets une seule fois
data_loader = DataLoader(DATA_DIR)
map_generator = MapGenerator(STATIC_DIR)

# --- AU DÉMARRAGE ---
@app.on_event("startup")
def startup_event():
    print("🚀 Démarrage Oracle Backend (Architecture Modulaire)...")
    
    # 1. Charger les données (CSV + API)
    data_loader.load_csvs()
    data_loader.fetch_tcl_api()
    
    # 2. Générer la carte avec les données chargées
    map_generator.generate(data_loader)

# --- ROUTES API ---

class ChatRequest(BaseModel):
    message: str
class AnalysisRequest(BaseModel):
    address: str

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