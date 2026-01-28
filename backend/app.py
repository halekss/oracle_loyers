from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd
import joblib
import os
import numpy as np
import requests  # Indispensable pour parler à LM Studio
from scipy.spatial import distance

# --- IMPORTS DES SERVICES ---
# (Assurez-vous que les fichiers data_loader.py et map_generator.py existent bien dans /services)
from services.data_loader import DataLoader
from services.map_generator import MapGenerator

app = Flask(__name__)
CORS(app)  # Autorise le Frontend React à parler au Backend

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')

# URL Spéciale pour Docker (permet de sortir du conteneur pour atteindre le Mac)
# Si "host.docker.internal" ne marche pas, remplacez par votre IP locale (ex: 192.168.1.XX)
LM_STUDIO_URL = "http://host.docker.internal:1234/v1/chat/completions"

os.makedirs(STATIC_DIR, exist_ok=True)

print("⏳ Démarrage de l'Oracle All-in-One...")

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

# 3. CHARGEMENT MODÈLE ML
model = None
try:
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print("✅ Modèle IA (ML) chargé avec succès.")
    else:
        print("⚠️ Pas de modèle .pkl trouvé. Le système utilisera la moyenne simple.")
except Exception as e:
    print(f"❌ Erreur chargement ML : {e}")


# --- FONCTION HELPER : PARLER À L'IA ---
def ask_phi3(system_prompt, user_prompt):
    """Envoie une requête à LM Studio et attend la réponse."""
    try:
        payload = {
            # 👇 NOM EXACT DU MODÈLE (VU DANS VOTRE CAPTURE D'ÉCRAN)
            "model": "phi-3-mini-4k-instruct:2", 
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }
        # 👇 TIMEOUT AUGMENTÉ À 30 SECONDES (Pour éviter l'erreur si le Mac est lent)
        r = requests.post(LM_STUDIO_URL, json=payload, timeout=30)
        
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
        else:
            print(f"⚠️ Erreur LM Studio: {r.status_code} - {r.text}")
            return None
    except Exception as e:
        print(f"⚠️ Exception connexion LLM: {e}")
        return None


# --- ROUTES API ---

@app.route('/')
def home():
    return "Oracle Backend is Alive 🔮"

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Sert la carte HTML générée."""
    return send_from_directory(STATIC_DIR, filename)

@app.route('/api/listings', methods=['GET'])
def get_listings():
    """Envoie toutes les données pour afficher les points sur la carte."""
    if df.empty: return jsonify({"error": "No data"}), 500
    # Remplace les NaN par None pour le JSON valide
    return jsonify(df.where(pd.notnull(df), None).to_dict(orient='records'))

@app.route('/api/predict', methods=['POST'])
def predict_smart():
    """
    Route 'SCAN' : INSTANTANÉE ⚡️
    Utilise Maths + Logique (Pas d'IA générative ici pour la vitesse).
    """
    if df.empty: return jsonify({"error": "Data not loaded"}), 500

    try:
        data = request.json
        lat = data.get('latitude')
        lon = data.get('longitude')
        surface = data.get('surface', 35)
        room_filter = data.get('room_filter', 'all')

        # --- A. FILTRAGE ---
        df_filtered = df.copy()
        if room_filter in ['t1', 't2', 't3']:
            df_filtered = df[df['type_local'].str.contains(room_filter.upper(), case=False, na=False)]
        
        # Si le filtre est trop strict et renvoie vide, on reprend tout
        if df_filtered.empty: 
            df_filtered = df.copy()

        # --- B. RECHERCHE DU VOISIN LE PLUS PROCHE ---
        locations = df_filtered[['latitude', 'longitude']].astype(float).values
        user_point = np.array([[lat, lon]])
        distances = distance.cdist(user_point, locations, 'euclidean')
        closest_idx = distances.argmin()
        neighbor = df_filtered.iloc[closest_idx].to_dict()
        
        # --- C. CALCUL PRIX (Moyenne + ML) ---
        # Moyenne des 5 voisins les plus proches
        avg_price_m2 = df_filtered.iloc[distances.argsort()[0][:5]]['prix_m2'].mean()
        if pd.isna(avg_price_m2): avg_price_m2 = neighbor.get('prix_m2', 0)
        
        estimated_price = avg_price_m2 * surface
        
        # Correction par le Machine Learning (si dispo)
        if model:
            try:
                input_vector = pd.DataFrame([neighbor])
                input_vector['surface'] = surface
                input_vector['latitude'] = lat
                input_vector['longitude'] = lon
                
                # Alignement des colonnes avec celles apprises par le modèle
                if hasattr(model, 'feature_names_in_'):
                    model_input = pd.DataFrame(0, index=[0], columns=model.feature_names_in_)
                    for col in model.feature_names_in_:
                        if col in input_vector:
                            model_input[col] = input_vector[col]
                    estimated_price = model.predict(model_input)[0]
            except Exception as e:
                print(f"Warning ML (fallback moyenne): {e}")

        final_price = round(estimated_price)

        # --- D. ANALYSE INSTANTANÉE (Algorithmique) ---
        # On évite LM Studio ici pour que le résultat s'affiche en < 1 seconde
        dist_bar = neighbor.get('dist_vice_bar', 999)
        dist_ecole = neighbor.get('dist_nuisance_ecole', 999)
        dist_metro = neighbor.get('dist_metro', 999)
        
        details = []
        ambiance = "Quartier Standard"
        
        if dist_bar < 100:
            ambiance = "Quartier Fêtard"
            details.append(f"🍻 Bars à {int(dist_bar)}m (bruyant le soir).")
        
        if dist_ecole < 150:
            if ambiance == "Quartier Fêtard": ambiance = "Zone Chaotique"
            else: ambiance = "Zone Familiale"
            details.append(f"👶 École à {int(dist_ecole)}m (bruyant le matin).")
            
        if dist_metro < 300:
            details.append(f"🚇 Métro à {int(dist_metro)}m (pratique).")

        if not details:
            details.append("Rien de spécial à proximité immédiate. Calme absolu.")

        # Construction du texte
        ai_analysis_text = f"📍 **{ambiance}** : {' '.join(details)}"

        return jsonify({
            "estimated_price": final_price,
            "analysis": ai_analysis_text,
            "stats": {
                "prix_m2": round(avg_price_m2),
                "nb_biens_analyse": len(df_filtered)
            }
        })

    except Exception as e:
        print(f"❌ Erreur Predict: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat_oracle():
    """
    Route 'CHAT' : Interactive 🤖
    C'est ici qu'on appelle vraiment l'IA (LM Studio).
    """
    try:
        data = request.json
        user_msg = data.get('message', '')
        
        print(f"💬 Question reçue : {user_msg}")
        
        # Prompt système pour donner une personnalité à l'Oracle
        system_prompt = (
            "Tu es l'Oracle Immobilier de Lyon. Tu es un expert cynique, drôle et un peu hautain. "
            "Tu connais tout sur les loyers, le bruit et la gentrification. "
            "Réponds en français, sois concis (max 2 phrases) et sarcastique."
        )
        
        response = ask_phi3(system_prompt, user_msg)
        
        if not response:
            return jsonify({"response": "🔇 L'Oracle médite (Vérifiez LM Studio : Serveur ON ? Network ON ? Port 1234 ?)."})
            
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"response": f"Erreur interne: {str(e)}"})


if __name__ == '__main__':
    # Écoute sur 0.0.0.0 pour être accessible depuis l'extérieur du conteneur Docker
    app.run(host='0.0.0.0', port=5000, debug=True)