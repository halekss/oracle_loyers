import os
import requests
import joblib
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from scipy.spatial import distance

# --- SERVICES ---
from services.data_loader import DataLoader
from services.map_generator import MapGenerator

print("🔥 DÉMARRAGE ORACLE CHATBOT v3.2 (FINAL)")

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')

# URL de LM Studio (Connexion Docker -> Mac/PC)
LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', "http://host.docker.internal:1234/v1/chat/completions")
print(f"🔗 LM Studio URL : {LM_STUDIO_URL}")

os.makedirs(STATIC_DIR, exist_ok=True)

# 1. CHARGEMENT DONNÉES
data_loader = DataLoader(DATA_DIR)
data_loader.load_csvs()
df = data_loader.df_immo

# Nettoyage préventif
if not df.empty and 'type_local' in df.columns:
    df['type_local'] = df['type_local'].fillna('').astype(str)

# 2. GÉNÉRATION CARTE
map_generator = MapGenerator(STATIC_DIR, DATA_DIR)
map_generator.generate(data_loader)

# 3. CHARGEMENT MODÈLE ML (Optionnel, fallback sur voisins si échec)
model = None
try:
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print("✅ Modèle ML chargé")
except Exception as e:
    print(f"⚠️ Pas de modèle ML (Mode Voisins activé) : {e}")

# --- FONCTION IA (MISTRAL / LM STUDIO) ---
def ask_mistral(system_prompt, user_message):
    """Communique avec LM Studio (Mistral)"""
    try:
        # On combine le prompt système et utilisateur car certains modèles locaux préfèrent un seul bloc
        combined_message = f"{system_prompt}\n\nUtilisateur : {user_message}\n\nOracle :"
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "user", "content": combined_message}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        print(f"📤 Envoi à LM Studio : {user_message[:50]}...")
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            return answer
        else:
            print(f"❌ Erreur LM Studio {response.status_code}")
            return f"⚠️ L'Oracle a un hoquet technique (Code {response.status_code})"
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de joindre LM Studio - Vérifiez le port 1234")
        return "🔴 L'Oracle est injoignable. Vérifiez que LM Studio tourne bien."
    except Exception as e:
        print(f"❌ Erreur technique : {e}")
        return "⚠️ Erreur technique interne."

# --- ROUTES API ---

@app.route('/')
def home():
    return jsonify({
        "status": "Oracle Backend Alive", 
        "mode": "ML + CHAT",
        "lm_studio": LM_STUDIO_URL
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route('/api/listings', methods=['GET'])
def get_listings():
    """Renvoie les données pour la carte"""
    if df.empty:
        return jsonify([]), 500
    # Remplace les NaN par None pour le JSON valide
    return jsonify(df.where(pd.notnull(df), None).to_dict(orient='records'))

@app.route('/api/predict', methods=['POST'])
def predict_smart():
    """Route SCAN : Estimation prix + Analyse"""
    if df.empty:
        return jsonify({"error": "Données non chargées"}), 500

    try:
        data = request.json
        lat = data.get('latitude')
        lon = data.get('longitude')
        surface = data.get('surface', 35)
        
        # Logique robuste : Voisin le plus proche (Nearest Neighbor)
        locations = df[['latitude', 'longitude']].astype(float).values
        user_point = np.array([[lat, lon]])
        distances = distance.cdist(user_point, locations, 'euclidean')
        closest_idx = distances.argmin()
        neighbor = df.iloc[closest_idx].to_dict()
        
        # Calcul du prix
        prix_m2 = neighbor.get('prix_m2', 5000)
        price = prix_m2 * surface
        
        return jsonify({
            "estimated_price": round(price),
            "analysis": f"📍 Zone analysée à {neighbor.get('ville', 'Lyon')}. (Demandez des détails à l'Oracle !)",
            "stats": {
                "prix_m2": round(prix_m2),
                "nb_biens_analyse": 1
            }
        })
    except Exception as e:
        print(f"❌ Erreur predict : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_oracle():
    """Route CHAT : Discussion avec l'Oracle"""
    try:
        data = request.json
        user_msg = data.get('message', '').strip()
        
        if not user_msg:
            return jsonify({"response": "⚠️ Le silence est d'or, mais j'ai besoin d'une question."})
        
        print(f"💬 Question reçue : {user_msg}")
        
        # Prompt de personnalité
        system_prompt = (
            "Tu es l'Oracle de Lyon, un expert immobilier cynique, drôle et un peu hautain. "
            "Tu connais tout sur Lyon (Croix-Rousse, Presqu'île, Guillotière, etc.). "
            "Tu utilises l'argot lyonnais occasionnellement. "
            "Tes réponses sont courtes (max 3 phrases) et percutantes."
        )
        
        response = ask_mistral(system_prompt, user_msg)
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        return jsonify({"response": "⚠️ Erreur interne du serveur."})

# --- LANCEMENT ---
if __name__ == '__main__':
    # 🚨 CRUCIAL : host='0.0.0.0' pour Docker et port=5000
    app.run(debug=True, host='0.0.0.0', port=5000)