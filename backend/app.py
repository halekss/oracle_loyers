import os
import requests
import joblib
import pandas as pd
import numpy as np
import uuid
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from scipy.spatial import distance

# --- SERVICES ---
from services.data_loader import DataLoader
from services.map_generator import MapGenerator

# --- NOUVEAUX MODULES ---
from conversation_manager import ConversationManager
from prompt_system import (
    build_constrained_prompt, 
    LYON_QUARTIERS, 
    is_off_topic,
    extract_quartiers_mentioned
)
from smart_agent import SmartAgent

print("🔥 DÉMARRAGE ORACLE CHATBOT v5.0 (ML + AGENT INTELLIGENT + MÉMOIRE)")

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')
CSV_PATH = os.path.join(DATA_DIR, 'master_immo_final.csv')

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

# 3. CHARGEMENT MODÈLE ML + DATASET COMPLET (pour l'alignement)
model = None
df_full = None
X_columns = None  # Colonnes du modèle après preprocessing

try:
    if os.path.exists(MODEL_PATH) and os.path.exists(CSV_PATH):
        model = joblib.load(MODEL_PATH)
        df_full = pd.read_csv(CSV_PATH)
        
        # On récupère les colonnes attendues par le modèle
        X_columns = model.feature_names_in_
        print(f"✅ Modèle ML chargé ({len(X_columns)} features attendues)")
    else:
        print("⚠️ Modèle ou CSV introuvable")
except Exception as e:
    print(f"⚠️ Erreur chargement ML : {e}")

# 4. INITIALISATION CONVERSATION MANAGER (Sauvegarde)
conversation_manager = ConversationManager(db_path=os.path.join(DATA_DIR, 'conversations.db'))
print("✅ Gestionnaire de conversations initialisé")

# 5. INITIALISATION SMART AGENT (IA qui déclenche le ML automatiquement)
smart_agent = None
if model and not df_full.empty:
    # On passe la fonction predict_price_ml au SmartAgent
    smart_agent = SmartAgent(
        ml_predictor=lambda s, lat, lon: predict_price_ml(s, lat, lon),
        df_data=df_full
    )
    print("✅ Agent intelligent initialisé")


# --- FONCTION ML : PREPROCESSING (Logique exacte de test_prediction.py) ---
def preprocess_for_ml(surface, latitude, longitude):
    """
    Prépare les features pour la prédiction ML en suivant EXACTEMENT
    la logique de test_prediction.py (nettoyage, encodage, alignement).
    """
    if model is None or df_full is None:
        return None
    
    try:
        # 1. On trouve le voisin le plus proche pour récupérer ses features
        locations = df_full[['latitude', 'longitude']].astype(float).values
        user_point = np.array([[latitude, longitude]])
        distances = distance.cdist(user_point, locations, 'euclidean')
        closest_idx = distances.argmin()
        neighbor_row = df_full.iloc[closest_idx].copy()
        
        # 2. On remplace la surface par celle demandée
        neighbor_row['surface'] = surface
        
        # 3. NETTOYAGE (comme dans test_prediction.py)
        features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 
                           'description', 'ville', 'titre', 'date']
        
        # Créer un mini DataFrame avec cette ligne
        df_temp = pd.DataFrame([neighbor_row])
        X = df_temp.drop(columns=features_to_drop, errors='ignore')
        
        # Supprimer les colonnes 'nb_'
        cols_nb = [c for c in X.columns if c.startswith('nb_')]
        X = X.drop(columns=cols_nb)
        
        # 4. ENCODAGE (get_dummies)
        X = pd.get_dummies(X, drop_first=True)
        
        # 5. ALIGNEMENT MAGIQUE (reindex avec les colonnes du modèle)
        X = X.reindex(columns=X_columns, fill_value=0)
        
        return X
        
    except Exception as e:
        print(f"❌ Erreur preprocessing : {e}")
        return None


# --- FONCTION ML : PRÉDICTION ---
def predict_price_ml(surface, latitude, longitude):
    """
    Utilise le modèle XGBoost pour prédire le prix.
    Retourne un dict avec le prix estimé et des stats.
    """
    if model is None:
        return None
    
    X_prepared = preprocess_for_ml(surface, latitude, longitude)
    
    if X_prepared is None:
        return None
    
    try:
        prix_estime = model.predict(X_prepared)[0]
        prix_m2 = prix_estime / surface if surface > 0 else 0
        
        return {
            "estimated_price": round(prix_estime),
            "prix_m2": round(prix_m2),
            "surface": surface,
            "method": "ML (XGBoost)"
        }
    except Exception as e:
        print(f"❌ Erreur prédiction ML : {e}")
        return None


# --- FONCTION IA (MISTRAL / LM STUDIO) ---
def ask_mistral(system_instruction, user_message, context=None):
    """
    Communique avec LM Studio (Mistral).
    Pour Mistral v0.3, on combine tout dans un seul message 'user'.
    """
    try:
        # Construction du message fusionné (système + contexte + question)
        if context:
            combined_message = f"""{system_instruction}

[CONTEXTE DE L'ANALYSE]
{context}

[QUESTION DE L'UTILISATEUR]
{user_message}

[RÉPONSE DE L'ORACLE]"""
        else:
            combined_message = f"""{system_instruction}

[QUESTION DE L'UTILISATEUR]
{user_message}

[RÉPONSE DE L'ORACLE]"""
        
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
            print(f"❌ Erreur LM Studio {response.status_code} : {response.text}")
            return f"⚠️ L'Oracle a un hoquet technique (Code {response.status_code})"
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de joindre LM Studio - Vérifiez le port 1234")
        return "🔴 L'Oracle est injoignable. Vérifiez que LM Studio tourne bien sur le port 1234."
    except Exception as e:
        print(f"❌ Erreur technique : {e}")
        return "⚠️ Erreur technique interne."


# --- ROUTES API ---

@app.route('/')
def home():
    return jsonify({
        "status": "Oracle Backend v4.0 - ML + Chat Fusionnés", 
        "model_loaded": model is not None,
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
    return jsonify(df.where(pd.notnull(df), None).to_dict(orient='records'))


@app.route('/api/predict', methods=['POST'])
def predict_smart():
    """
    Route SCAN : Estimation prix avec ML (XGBoost).
    Utilise la logique exacte de test_prediction.py.
    """
    if df.empty:
        return jsonify({"error": "Données non chargées"}), 500

    try:
        data = request.json
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        surface = float(data.get('surface', 35))
        
        # TENTATIVE ML
        ml_result = predict_price_ml(surface, lat, lon)
        
        if ml_result:
            # Succès ML
            return jsonify({
                "estimated_price": ml_result["estimated_price"],
                "analysis": f"🔮 Estimation ML : {ml_result['estimated_price']} € pour {surface} m² ({ml_result['prix_m2']} €/m²)",
                "stats": {
                    "prix_m2": ml_result["prix_m2"],
                    "method": ml_result["method"],
                    "surface": surface
                },
                "details": {
                    "latitude": lat,
                    "longitude": lon
                }
            })
        else:
            # Fallback : Voisin le plus proche (méthode simple)
            locations = df[['latitude', 'longitude']].astype(float).values
            user_point = np.array([[lat, lon]])
            distances = distance.cdist(user_point, locations, 'euclidean')
            closest_idx = distances.argmin()
            neighbor = df.iloc[closest_idx].to_dict()
            
            prix_m2 = neighbor.get('prix_m2', 15)
            price = prix_m2 * surface
            
            return jsonify({
                "estimated_price": round(price),
                "analysis": f"📍 Estimation basée sur le voisin le plus proche à {neighbor.get('ville', 'Lyon')}",
                "stats": {
                    "prix_m2": round(prix_m2),
                    "method": "Nearest Neighbor (Fallback)",
                    "surface": surface
                }
            })
            
    except Exception as e:
        print(f"❌ Erreur predict : {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat_oracle():
    """
    Route CHAT v2.0 : 
    - Utilise l'agent intelligent pour détecter les intentions
    - Déclenche le ML automatiquement si nécessaire
    - Sauvegarde la conversation
    - Utilise un prompt anti-hallucination
    """
    try:
        data = request.json
        user_msg = data.get('message', '').strip()
        context = data.get('context', None)  # Contexte manuel du frontend
        session_id = data.get('session_id', str(uuid.uuid4()))  # ID de session
        
        if not user_msg:
            return jsonify({
                "response": "⚠️ Le silence est d'or, mais j'ai besoin d'une question.",
                "session_id": session_id
            })
        
        print(f"💬 [{session_id}] Question : {user_msg}")
        
        # ÉTAPE 1 : Récupérer l'historique de conversation
        history_formatted = conversation_manager.format_history_for_llm(session_id, limit=5)
        
        # ÉTAPE 2 : Utiliser l'agent intelligent pour analyser la question
        enriched_context = context or ""
        agent_data = {}
        
        if smart_agent:
            intent_result = smart_agent.analyze_question(user_msg)
            print(f"🧠 Intent détecté : {intent_result['intent']} → Action : {intent_result['action']}")
            
            # L'agent exécute l'action (peut déclencher le ML)
            if intent_result['action'] != 'chat_only':
                action_result = smart_agent.execute_action(intent_result, user_msg)
                enriched_context += "\n" + action_result['context']
                agent_data = action_result.get('data', {})
        
        # ÉTAPE 3 : Construire le prompt anti-hallucination
        quartiers_mentioned = extract_quartiers_mentioned(user_msg)
        quartiers_data = {k: v for k, v in LYON_QUARTIERS.items() 
                         if any(q in k for q in quartiers_mentioned)} if quartiers_mentioned else LYON_QUARTIERS
        
        full_prompt = build_constrained_prompt(
            user_message=user_msg,
            context=enriched_context if enriched_context else None,
            history=history_formatted if history_formatted else None,
            quartiers_data=quartiers_data
        )
        
        # ÉTAPE 4 : Appeler LM Studio avec le prompt optimisé
        oracle_response = ask_mistral_direct(full_prompt)
        
        # ÉTAPE 5 : Sauvegarder la conversation
        conversation_manager.save_message(
            session_id=session_id,
            user_message=user_msg,
            oracle_response=oracle_response,
            context=enriched_context if enriched_context else None
        )
        
        print(f"💾 Conversation sauvegardée [session: {session_id}]")
        
        return jsonify({
            "response": oracle_response,
            "session_id": session_id,
            "agent_data": agent_data  # Données ML si déclenchées
        })
        
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"response": "⚠️ Erreur interne du serveur."})


def ask_mistral_direct(combined_prompt: str) -> str:
    """
    Version simplifiée qui envoie un prompt pré-construit à LM Studio.
    """
    try:
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "user", "content": combined_prompt}
            ],
            "temperature": 0.5,  # Plus bas = moins de créativité/hallucinations
            "max_tokens": 400
        }
        
        print(f"📤 Envoi à LM Studio...")
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            return answer
        else:
            print(f"❌ Erreur LM Studio {response.status_code} : {response.text}")
            return f"⚠️ L'Oracle a un hoquet technique (Code {response.status_code})"
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de joindre LM Studio")
        return "🔴 L'Oracle est injoignable. Vérifiez que LM Studio tourne bien sur le port 1234."
    except Exception as e:
        print(f"❌ Erreur technique : {e}")
        return "⚠️ Erreur technique interne."


@app.route('/api/history/<session_id>', methods=['GET'])
def get_conversation_history(session_id):
    """
    Récupère l'historique d'une conversation.
    """
    try:
        history = conversation_manager.get_history(session_id, limit=50)
        return jsonify({"history": history})
    except Exception as e:
        print(f"❌ Erreur récupération historique : {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/clear-history/<session_id>', methods=['DELETE'])
def clear_conversation(session_id):
    """
    Efface l'historique d'une session.
    """
    try:
        conversation_manager.clear_session(session_id)
        return jsonify({"message": "Historique effacé"})
    except Exception as e:
        print(f"❌ Erreur suppression historique : {e}")
        return jsonify({"error": str(e)}), 500


# --- LANCEMENT ---
if __name__ == '__main__':
    # 🚨 CRUCIAL : host='0.0.0.0' pour Docker et port=5000
    app.run(debug=True, host='0.0.0.0', port=5000)