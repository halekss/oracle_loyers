import os
import json
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.data_loader import DataLoader
from services.chat_service import ChatService
from services.predictor import build_feature_row, estimate_confidence
import joblib

# Initialisation de l'application
app = Flask(__name__)
# Origines de confiance toujours autorisées, même sans CORS_ORIGINS : le
# déploiement de démo et les serveurs de dev locaux (Vite). Pas de fallback
# sur '*' pour éviter qu'un CORS_ORIGINS oublié n'ouvre l'API à n'importe
# quelle origine.
DEFAULT_CORS_ORIGINS = [
    'https://oracle-loyers.onrender.com',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]


def normalize_origin(origin):
    return origin.strip().rstrip('/')


def get_cors_origins():
    origins = os.environ.get('CORS_ORIGINS', '').strip()

    allowed_origins = []
    for origin in origins.split(','):
        normalized_origin = normalize_origin(origin)
        if normalized_origin and normalized_origin not in allowed_origins:
            allowed_origins.append(normalized_origin)

    for origin in DEFAULT_CORS_ORIGINS:
        if origin not in allowed_origins:
            allowed_origins.append(origin)

    return allowed_origins


def get_server_port():
    return int(os.environ.get('PORT', '5000'))


cors_origins = get_cors_origins()
print(f"🔒 Politique CORS effective : {cors_origins}")
CORS(app, origins=cors_origins)  # Autorise les requêtes du Frontend React


def get_default_rate_limits():
    """
    Limites par défaut appliquées à toutes les routes, configurables via
    RATE_LIMIT_DEFAULT (format Flask-Limiter, plusieurs limites séparées
    par des virgules, ex : "200 per day,50 per hour").
    """
    raw = os.environ.get('RATE_LIMIT_DEFAULT', '200 per day,50 per hour')
    return [part.strip() for part in raw.split(',') if part.strip()]


limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=get_default_rate_limits(),
    storage_uri="memory://",
)


def get_chat_rate_limit():
    """
    Limite dédiée à /api/chat, plus stricte que le défaut global : protège
    le quota gratuit Gemini contre un unique utilisateur/bot qui l'épuiserait
    pour tout le monde. Configurable via RATE_LIMIT_CHAT.
    """
    return os.environ.get('RATE_LIMIT_CHAT', '15 per hour')


@app.errorhandler(429)
def handle_rate_limit_exceeded(error):
    return jsonify({"error": "Trop de requêtes. Réessayez dans quelques instants."}), 429


def get_request_json():
    data = request.get_json(silent=True)
    if data is not None:
        return data

    raw_body = request.get_data(as_text=True).strip()
    if not raw_body:
        return {}

    return json.loads(raw_body)

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'master_immo_final.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')
CAVALIERS_PATH = os.path.join(BASE_DIR, 'data', 'cavaliers_lyon.csv')

# Chargement des services
print("Chargement des données...")
data_loader = DataLoader(DATA_PATH)

print("Chargement des points d'intérêt (cavaliers)...")
try:
    cavaliers_df = pd.read_csv(CAVALIERS_PATH)
except Exception:
    print("⚠️ Attention : cavaliers_lyon.csv introuvable, features de distance à 0 par défaut.")
    cavaliers_df = None

print("Initialisation d'Immotep (Service Chat)...")
chat_service = ChatService()

# Chargement du modèle IA (XGBoost)
print("Chargement du modèle IA...")
try:
    model = joblib.load(MODEL_PATH)
except Exception:
    print("⚠️ Attention : Modèle price_predictor.pkl introuvable.")
    model = None

# --- ROUTES API ---

@app.route('/api/listings', methods=['GET'])
def get_listings():
    """Renvoie les données pour la carte (limité pour la performance)"""
    df = data_loader.get_data()
    if df is None:
        return jsonify([])
    
    # On renvoie les colonnes nécessaires uniquement et on gère les NaN
    data = df[['latitude', 'longitude', 'prix', 'type_local', 'quartier']].fillna('').to_dict(orient='records')
    return jsonify(data)

@app.route('/api/quartier-stats', methods=['POST'])
def get_quartier_stats():
    """
    SCAN DE QUARTIER (Données Réelles CSV).
    Ne fait PAS appel au Machine Learning.
    Filtre le dataframe par nom de quartier et par type de bien.
    """
    try:
        data = get_request_json()
        quartier_input = data.get('quartier', '').strip()
        type_filter = data.get('type_local', 'Tout')

        df = data_loader.get_data()
        if df is None or df.empty:
            return jsonify({"error": "Données non disponibles"}), 500

        # 1. Filtrage par Quartier (Recherche textuelle flexible)
        if not quartier_input:
            return jsonify({"error": "Le nom du quartier est vide"}), 400

        # Nettoyage pour éviter les erreurs sur NaN
        df_clean = df.dropna(subset=['quartier', 'prix', 'surface'])
        
        # Recherche insensible à la casse
        mask_quartier = df_clean['quartier'].str.contains(quartier_input, case=False, na=False)
        filtered_df = df_clean[mask_quartier]

        if filtered_df.empty:
            return jsonify({
                "found": False,
                "message": f"Aucun bien trouvé pour le secteur '{quartier_input}'"
            }), 200

        # 2. Filtrage par Type de bien (Si pas 'Tout')
        mapping_types = {
            "T1": ["Studio/T1", "Studio", "T1"],
            "T2": ["T2"],
            "T3": ["T3"],
            "T4+": ["Grand (T4+)", "T4", "T5", "Maison"]
        }

        if type_filter != 'Tout':
            types_cibles = mapping_types.get(type_filter, [type_filter])
            filtered_df = filtered_df[filtered_df['type_local'].isin(types_cibles)]

        # Si après filtrage type il n'y a plus rien
        if filtered_df.empty:
            return jsonify({
                "found": True,
                "quartier_detecte": quartier_input,
                "count": 0,
                "prix_moyen": 0,
                "prix_m2_moyen": 0,
                "message": f"Pas de {type_filter} trouvé dans ce secteur."
            }), 200

        # 3. Calcul des Moyennes Réelles
        mean_price = filtered_df['prix'].mean()
        
        # Calcul du prix au m2 moyen
        if 'prix_m2' in filtered_df.columns:
             mean_price_m2 = filtered_df['prix_m2'].mean()
        else:
             mean_price_m2 = (filtered_df['prix'] / filtered_df['surface']).mean()

        count = len(filtered_df)
        
        # Nom officiel le plus fréquent pour l'affichage (ex: "Gerland" au lieu de "gerland")
        nom_officiel = filtered_df['quartier'].mode()[0] if not filtered_df['quartier'].empty else quartier_input
        center = None
        if {'latitude', 'longitude'}.issubset(filtered_df.columns):
            coords = filtered_df.dropna(subset=['latitude', 'longitude'])
            if not coords.empty:
                center = {
                    "lat": round(float(coords['latitude'].mean()), 6),
                    "lng": round(float(coords['longitude'].mean()), 6)
                }

        return jsonify({
            "found": True,
            "quartier_detecte": nom_officiel,
            "type_filtre": type_filter,
            "count": int(count),
            "prix_moyen": round(float(mean_price), 0),
            "prix_m2_moyen": round(float(mean_price_m2), 0),
            "center": center
        })

    except Exception as e:
        print(f"Erreur Stats Quartier: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    """Prédiction de prix via le modèle Machine Learning (XGBoost) chargé en mémoire."""
    if model is None:
        return jsonify({"error": "Modèle de prédiction indisponible sur ce serveur"}), 500

    df = data_loader.get_data()
    if df is None or df.empty:
        return jsonify({"error": "Données de référence indisponibles"}), 500

    try:
        payload = get_request_json()
    except Exception:
        return jsonify({"error": "Payload JSON invalide"}), 400

    features_df, result = build_feature_row(payload, df, cavaliers_df, list(model.feature_names_in_))
    if features_df is None:
        return jsonify({"error": "Payload invalide", "details": result}), 400

    try:
        estimated_price = float(model.predict(features_df)[0])
    except Exception as e:
        return jsonify({"error": f"Erreur lors de la prédiction : {e}"}), 500

    surface = result["surface"]
    price_m2 = estimated_price / surface if surface else 0.0
    confidence, comparables = estimate_confidence(df, result["quartier"], result["type_local"])

    return jsonify({
        "estimated_price": round(estimated_price, 0),
        "price_m2": round(price_m2, 0),
        "confiance": confidence,
        "comparables": comparables,
        "quartier_detecte": result["quartier"],
        "type_local_detecte": result["type_local"],
    })

@app.route('/api/chat', methods=['POST'])
@limiter.limit(get_chat_rate_limit)
def chat():
    """Route pour le Chatbot Immotep"""
    try:
        data = get_request_json()
        # On récupère le message utilisateur et le contexte envoyé par le front
        user_msg = data.get('message', '')
        context = data.get('context', '') 

        if not user_msg or not user_msg.strip():
            return jsonify({"response": "Silence... Tu n'as rien à dire ?"}), 400

        # On récupère le DataFrame complet
        df = data_loader.get_data()

        # On appelle le service dédié qui gère le prompt, le parsing et Gemini
        result_immotep = chat_service.get_chat_result(user_msg, context, df)

        return jsonify(result_immotep)

    except Exception as e:
        print(f"Erreur Chat: {e}")
        return jsonify({"response": "Erreur interne côté serveur. Immotep revient dès que l'API répond correctement."}), 500

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=get_server_port())
