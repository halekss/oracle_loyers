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

print("🔥 DÉMARRAGE ORACLE CHATBOT v5.0 (REAL ML + FEATURES)")

app = Flask(__name__)
CORS(app)

# ============================================================================
# ⚙️ CONFIGURATION
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODELS_DIR = os.path.join(BASE_DIR, 'models')

MODEL_PATH = os.path.join(MODELS_DIR, 'price_predictor.pkl')
FEATURES_PATH = os.path.join(MODELS_DIR, 'model_features.pkl') # <--- Liste des colonnes

# URL LM Studio (Mac/Docker friendly)
LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', "http://host.docker.internal:1234/v1/chat/completions")
print(f"🔗 LM Studio URL : {LM_STUDIO_URL}")

os.makedirs(STATIC_DIR, exist_ok=True)

# ============================================================================
# 📥 CHARGEMENT DONNÉES & MODÈLE
# ============================================================================

# 1. Données Immo (CSV)
data_loader = DataLoader(DATA_DIR)
data_loader.load_csvs()
df = data_loader.df_immo

# 2. Carte
map_generator = MapGenerator(STATIC_DIR, DATA_DIR)
map_generator.generate(data_loader)

# 3. Modèle ML & Features
model = None
model_features = None

try:
    if os.path.exists(MODEL_PATH) and os.path.exists(FEATURES_PATH):
        model = joblib.load(MODEL_PATH)
        model_features = joblib.load(FEATURES_PATH) # Liste exacte des colonnes du train
        print(f"✅ Modèle ML chargé (attend {len(model_features)} critères)")
    else:
        print("⚠️ FICHIERS ML MANQUANTS : Le modèle ou la liste des features est absente.")
        print("👉 Lancez 'python scripts/train_model.py' pour les générer.")
except Exception as e:
    print(f"❌ Erreur chargement ML : {e}")

# ============================================================================
# 🧠 FONCTIONS INTELLIGENTES
# ============================================================================

def ask_mistral(system_prompt, user_message):
    """Interroge LM Studio"""
    try:
        combined_message = f"{system_prompt}\n\nUtilisateur : {user_message}\n\nOracle :"
        payload = {
            "model": "local-model",
            "messages": [{"role": "user", "content": combined_message}],
            "temperature": 0.7,
            "max_tokens": 500
        }
        r = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
        return f"⚠️ Erreur Oracle (Code {r.status_code})"
    except:
        return "🔴 L'Oracle est injoignable (Vérifiez LM Studio)."

def prepare_data_for_ml(neighbor, surface, features_list):
    """
    Transforme les données brutes en une ligne prête pour XGBoost.
    C'est ici que la magie opère pour éviter les erreurs de forme.
    """
    # 1. On part des données du voisin (environnement, distances...)
    input_df = pd.DataFrame([neighbor])
    
    # 2. On met à jour la surface (critère n°1)
    input_df['surface'] = surface
    
    # 3. Gestion des TYPES (One-Hot Encoding manuel)
    # Le modèle attend des colonnes comme 'type_local_Studio/T1', 'type_local_T2', etc.
    # On doit les créer et mettre 1 ou 0 selon la surface.
    
    # D'abord, on met toutes les colonnes 'type_' potentielles à 0
    for col in features_list:
        if 'type' in col:
            input_df[col] = 0
            
    # Ensuite, on active la bonne colonne
    if surface < 30:
        if 'type_local_Studio/T1' in features_list: input_df['type_local_Studio/T1'] = 1
        if 'type_Studio' in features_list: input_df['type_Studio'] = 1
    elif surface < 50:
        if 'type_local_T2' in features_list: input_df['type_local_T2'] = 1
    elif surface < 75:
        if 'type_local_T3' in features_list: input_df['type_local_T3'] = 1
    else:
        # Pour les grands apparts, si T4+ existe ou Maison
        if 'type_local_Grand (T4+)' in features_list: input_df['type_local_Grand (T4+)'] = 1
        if 'type_Maison' in features_list: input_df['type_Maison'] = 0 # On assume appart par défaut

    # 4. ALIGNEMENT FINAL (Reindex)
    # Force l'ordre exact des colonnes comme lors de l'entraînement.
    # Remplit les trous avec 0. Vire les colonnes en trop.
    final_df = input_df.reindex(columns=features_list, fill_value=0)
    
    return final_df

# ============================================================================
# 🌐 ROUTES API
# ============================================================================

@app.route('/')
def home():
    return jsonify({
        "status": "Oracle v5.0 Alive", 
        "ml_ready": model is not None
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route('/api/listings', methods=['GET'])
def get_listings():
    if df.empty: return jsonify([]), 500
    return jsonify(df.where(pd.notnull(df), None).to_dict(orient='records'))

@app.route('/api/predict', methods=['POST'])
def predict_smart():
    """Route SCAN : Prédiction via XGBoost"""
    if df.empty: return jsonify({"error": "No Data"}), 500

    try:
        data = request.json
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        surface = float(data.get('surface', 35))
        
        # 1. Trouver l'environnement (Voisin le plus proche)
        locations = df[['latitude', 'longitude']].astype(float).values
        user_point = np.array([[lat, lon]])
        distances = distance.cdist(user_point, locations, 'euclidean')
        closest_idx = distances.argmin()
        neighbor = df.iloc[closest_idx].to_dict()
        
        # 2. PRÉDICTION ML
        price_estimated = 0
        method = "Inconnue"
        
        if model and model_features:
            # A. Préparation des données (Alignement avec le train)
            input_df = prepare_data_for_ml(neighbor, surface, model_features)
            
            # B. Prédiction
            price_estimated = float(model.predict(input_df)[0])
            method = "IA (XGBoost)"
            
            # C. Garde-fous (Si le modèle hallucine un prix négatif ou géant)
            if price_estimated < 200 or price_estimated > 10000:
                print(f"⚠️ Aberration ML ({price_estimated}€) -> Fallback Voisin")
                base_m2 = float(neighbor.get('prix_m2', 20))
                price_estimated = base_m2 * surface
                method = "Voisin (Secours)"
        else:
            # Fallback si pas de modèle chargé
            base_m2 = float(neighbor.get('prix_m2', 20))
            price_estimated = base_m2 * surface
            method = "Voisin (Pas de modèle)"

        # Calcul du prix au m² induit
        final_prix_m2 = price_estimated / surface if surface > 0 else 0

        return jsonify({
            "estimated_price": round(price_estimated),
            "analysis": f"📍 Analyse {method} à {neighbor.get('ville', 'Lyon')}.",
            "stats": {
                "prix_m2": round(final_prix_m2),
                "surface": surface,
                "nb_biens_analyse": 1
            },
            "details": {
                "latitude": lat, 
                "longitude": lon, 
                "ville": neighbor.get('ville', 'Lyon')
            }
        })

    except Exception as e:
        print(f"❌ Erreur predict : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_oracle():
    """Route CHAT : Discussion"""
    try:
        data = request.json
        user_msg = data.get('message', '').strip()
        scan_data = data.get('scan_data', {})
        
        if not user_msg: return jsonify({"response": "..."})
        
        # Construction du contexte
        context_info = ""
        if scan_data and scan_data.get('estimated_price'):
            context_info = (
                f"\nINFO SCAN :"
                f"\n- Loyer estimé : {scan_data['estimated_price']} €"
                f"\n- Surface : {scan_data['surface']} m²"
                f"\n- Quartier : {scan_data.get('ville', 'Lyon')}"
            )

        system_prompt = (
            f"Tu es l'Oracle de Lyon, expert immo cynique. "
            f"Tu parles avec l'argot lyonnais. Sois bref. "
            f"Données réelles : {context_info}"
        )
        
        return jsonify({"response": ask_mistral(system_prompt, user_msg)})
        
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        return jsonify({"response": "Erreur interne."})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)