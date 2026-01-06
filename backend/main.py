from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="L'Oracle des Loyers API")

# Autoriser React (qui tourne sur le port 5173) à interroger l'API
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "L'Oracle est éveillé", "python_version": "3.12"}

@app.get("/api/predict")
def predict_rent(address: str):
    # C'est ici que l'Alchimiste connectera le modèle ML plus tard
    return {
        "address": address,
        "predicted_price": 850,
        "cavaliers": {"gentrification": "High", "vice": "Medium"}
    }