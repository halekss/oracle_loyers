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

print("🔥 DÉMARRAGE ORACLE CHATBOT v3.2 (FIXED)")

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')

# URL de LM Studio
LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', "http://host.docker.internal:1234/v1/chat/completions")
print(f"🔗 LM Studio URL : {LM_STUDIO_URL}")

os.makedirs(STATIC_DIR, exist_ok=True)

# 1. CHARGEMENT DONNÉES
data_loader = DataLoader(DATA_DIR)
data_loader.load_csvs()
df = data_loader.df_immo
if not df.empty and 'type_local' in df.columns:
    df['type_local'] = df['type_local'].fillna('').astype(str)

# 2. GÉNÉRATION CARTE
map_generator = MapGenerator(STATIC_DIR, DATA_DIR)
map_generator.generate(data_loader)

# 3. CHARGEMENT MODÈLE
model = None
try:
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print("✅ Modèle ML chargé")
except Exception as e:
    print(f"⚠️ Pas de modèle ML : {e}")

# --- FONCTION IA (CORRIGÉE) ---
def ask_mistral(system_prompt, user_message):
    """Communique avec LM Studio (Mistral) - Format compatible"""
    try:
        # ✅ Combine system et user en un seul message
        # Car Mistral via LM Studio n'accepte pas le rôle "system"
        combined_message = f"{system_prompt}\n\nUtilisateur : {user_message}\n\nOracle :"
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "user", "content": combined_message}
            ],
            "temperature": 0.9,
            "max_tokens": 500
        }
        
        print(f"📤 Envoi à LM Studio : {user_message[:50]}...")
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            print(f"✅ Réponse reçue : {answer[:50]}...")
            return answer
        else:
            print(f"❌ Erreur LM Studio {response.status_code} : {response.text[:200]}")
            return f"⚠️ L'Oracle a un hoquet technique (Code {response.status_code})"
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de joindre LM Studio - Vérifiez qu'il tourne sur le port 1234")
        return "🔴 L'Oracle est injoignable. Vérifiez que LM Studio est démarré sur le port 1234."
    except requests.exceptions.Timeout:
        print("❌ Timeout LM Studio")
        return "⏱️ L'Oracle réfléchit trop longtemps... Réessayez."
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")
        return f"⚠️ Erreur technique : {str(e)}"

# --- ROUTES ---

@app.route('/')
def home():
    return jsonify({"status": "Oracle Backend v3.2 (Fixed) Alive", "lm_studio": LM_STUDIO_URL})

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route('/api/listings', methods=['GET'])
def get_listings():
    if df.empty:
        return jsonify([]), 500
    return jsonify(df.where(pd.notnull(df), None).to_dict(orient='records'))

@app.route('/api/predict', methods=['POST'])
def predict_smart():
    """Route SCAN (analyse rapide)"""
    if df.empty:
        return jsonify({"error": "Données non chargées"}), 500

    try:
        data = request.json
        lat = data.get('latitude')
        lon = data.get('longitude')
        surface = data.get('surface', 35)
        
        # Trouver le voisin le plus proche
        locations = df[['latitude', 'longitude']].astype(float).values
        user_point = np.array([[lat, lon]])
        distances = distance.cdist(user_point, locations, 'euclidean')
        closest_idx = distances.argmin()
        neighbor = df.iloc[closest_idx].to_dict()
        
        # Estimation prix
        price = neighbor.get('prix_m2', 0) * surface
        
        return jsonify({
            "estimated_price": round(price),
            "analysis": "📍 **Zone Analysée**. (Interrogez l'Oracle pour son avis tranché...)",
            "stats": {
                "prix_m2": round(neighbor.get('prix_m2', 0)),
                "nb_biens_analyse": 1
            }
        })
    except Exception as e:
        print(f"❌ Erreur predict : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_oracle():
    """Route CHAT : Communication avec Mistral via LM Studio"""
    try:
        data = request.json
        user_msg = data.get('message', '').strip()
        
        if not user_msg:
            return jsonify({"response": "⚠️ Message vide."})
        
        print(f"💬 Question reçue : {user_msg}")
        
        # Prompt pour Mistral (personnalité de l'Oracle)
        system_prompt = (
            "Tu es l'Oracle de Lyon, un expert immobilier cynique et sarcastique. "
            "Tu parles de manière directe, utilises l'argot lyonnais (Gones, Fenottes), "
            "et tu donnes des avis tranchés sur les quartiers. "
            "Tu inventes des détails croustillants si nécessaire (embouteillages, voisins, pollution). "
            "Ne dis JAMAIS que tu es une IA. Reste dans le personnage. "
            "Réponds en 2-3 phrases maximum, de manière percutante."
        )
        
        # Appel à LM Studio
        response = ask_mistral(system_prompt, user_msg)
        
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        return jsonify({"response": f"⚠️ Erreur interne : {str(e)}"})

# Test de connexion LM Studio au démarrage
def test_lm_studio_connection():
    """Vérifie si LM Studio est accessible"""
    try:
        test_url = LM_STUDIO_URL.replace('/v1/chat/completions', '/v1/models')
        response = requests.get(test_url, timeout=2)
        if response.status_code == 200:
            print("✅ LM Studio connecté")
            return True
        else:
            print(f"⚠️ LM Studio répond mais code {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️ LM Studio non joignable : {e}")
        print("   → Assurez-vous que LM Studio est démarré avec le serveur actif sur le port 1234")
        return False

# Test au démarrage
test_lm_studio_connection()

if __name__ == '__main__':
    app.run(debug=True, port=8000)