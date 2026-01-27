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

@app.post("/api/chat")
async def chat_with_oracle(request: ChatRequest):
    """Route pour discuter avec l'Oracle via LM Studio."""
    # Utilisation de host.docker.internal pour accéder au localhost du Mac depuis Docker
    LM_STUDIO_URL = "http://host.docker.internal:1234/v1/chat/completions"
    
    payload = {
    "model": "qwen2.5-7b-instruct-1m",  # ← Nom exact de votre modèle
    "messages": [
        {
            "role": "system", 
            "content": """Tu es l'Oracle des Loyers de Lyon, un expert immobilier cynique et sarcastique.

Tu analyses les biens immobiliers en révélant les vérités cachées du marché avec les "4 Cavaliers" :
- La Gentrification (cafés hipsters, magasins bio, studios de yoga)
- Le Vice (kebabs, PMU, sex-shops)
- La Nuisance (bars de nuit, axes routiers, terrasses bruyantes)
- La Superstition (cimetières, hôpitaux, pompes funèbres)

Ton style : Direct, sardonique, mais toujours factuel. Tu expliques pourquoi un prix est justifié avec un humour noir.
IMPORTANT : Réponds en 3-4 phrases maximum pour être percutant."""
        },
        {"role": "user", "content": request.message}
    ],
    "temperature": 0.8,
    "max_tokens": 200  # ← Réduit de 600 à 200 pour des réponses 3x plus rapides
}

    try:
        print(f"🔄 Envoi à LM Studio via {LM_STUDIO_URL}")
        print(f"📦 Payload : {payload}")
        
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        print(f"📥 Status Code : {response.status_code}")
        print(f"📥 Réponse brute : {response.text[:300]}...")
        
        response.raise_for_status()
        data = response.json()
        
        # Extraction de la réponse de l'Oracle
        oracle_response = data['choices'][0]['message']['content']
        print(f"✅ Réponse Oracle : {oracle_response[:100]}...")
        
        return {"response": oracle_response}
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Impossible de se connecter à LM Studio : {e}")
        raise HTTPException(
            status_code=500, 
            detail="LM Studio n'est pas accessible. Vérifiez que le serveur tourne et que docker-compose.yml contient 'extra_hosts'."
        )
        
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout LM Studio : {e}")
        raise HTTPException(
            status_code=500, 
            detail="LM Studio met trop de temps à répondre (>60s). Le modèle est peut-être trop lent."
        )
        
    except KeyError as e:
        print(f"❌ Format de réponse invalide : {e}")
        print(f"📥 Réponse complète : {response.text}")
        raise HTTPException(
            status_code=500, 
            detail="Format de réponse LM Studio invalide. Vérifiez que le modèle est bien chargé."
        )
        
    except Exception as e:
        print(f"❌ Erreur inattendue : {type(e).__name__} - {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur Oracle : {str(e)}"
        )