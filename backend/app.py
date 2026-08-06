import os
import json
import logging
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
from logging_config import configure_logging, init_sentry
from services.data_loader import DataLoader
from services.chat_service import ChatService
from services.predictor import build_feature_row, estimate_confidence
from services.cavaliers_factors import summarize_cavaliers
from services.price_history import compute_price_history
from services.text_matching import resolve_quartier
from services import annonces_store
from schemas import ChatRequestSchema, QuartierStatsRequestSchema, PredictRequestSchema, ValidationError
import joblib

# Observabilité (ORA-63) : logging structuré + tracking d'erreurs Sentry,
# à configurer avant tout le reste (Flask, chargement des données/modèle)
# pour que les logs de démarrage soient déjà structurés.
configure_logging()
init_sentry()
logger = logging.getLogger(__name__)

# Initialisation de l'application
app = Flask(__name__)
# Origines de confiance toujours autorisées, même sans CORS_ORIGINS : le
# déploiement de démo et les serveurs de dev locaux (Vite). 5174 est inclus
# en plus du port par défaut 5173 : c'est le fallback vers lequel Vite
# bascule automatiquement quand un autre projet local occupe déjà le 5173
# (cf. FRONTEND_PORT dans docker-compose.yml, qui suit la même convention).
# Pas de fallback sur '*' pour éviter qu'un CORS_ORIGINS oublié n'ouvre
# l'API à n'importe quelle origine.
DEFAULT_CORS_ORIGINS = [
    'https://oracle-loyers.onrender.com',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
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
logger.info("Politique CORS effective : %s", cors_origins)
CORS(app, origins=cors_origins)  # Autorise les requêtes du Frontend React

# Documentation interactive Swagger/OpenAPI, accessible sur /apidocs (voir
# aussi API_CONTRACT.md à la racine du dépôt pour le contrat détaillé).
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}
swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Oracle des Loyers — API",
        "description": (
            "Documentation interactive des routes exposées par le backend Flask. "
            "Voir API_CONTRACT.md à la racine du dépôt pour le contrat détaillé "
            "(codes d'erreur, exemples complets)."
        ),
        "version": "1.0.0",
    },
}
swagger = Swagger(app, config=swagger_config, template=swagger_template)


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


@app.after_request
def set_security_headers(response):
    """
    En-têtes de sécurité de base (ORA-69), sans impact fonctionnel :
    l'API ne sert que du JSON, jamais de HTML/JS, donc pas de CSP applicative
    à définir ici (voir frontend/ pour le CSP éventuel côté SPA).
    """
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


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
MODEL_META_PATH = f"{MODEL_PATH}.meta.json"
CAVALIERS_PATH = os.path.join(BASE_DIR, 'data', 'cavaliers_lyon.csv')
SNAPSHOTS_DIR = os.path.join(BASE_DIR, 'data', 'snapshots')
SNAPSHOTS_MANIFEST_PATH = os.path.join(SNAPSHOTS_DIR, 'manifest.csv')
ANNONCES_DB_PATH = os.path.join(BASE_DIR, 'data', 'annonces.db')

# Chargement des services
logger.info("Initialisation de la base annonces...")
annonces_store.init_db(ANNONCES_DB_PATH)
logger.info("Chargement des données...")
data_loader = DataLoader(DATA_PATH)

logger.info("Chargement des points d'intérêt (cavaliers)...")
try:
    cavaliers_df = pd.read_csv(CAVALIERS_PATH)
except Exception as exc:
    logger.warning(
        "cavaliers_lyon.csv introuvable, features de distance à 0 par défaut : %s - %s",
        type(exc).__name__, exc,
    )
    cavaliers_df = None

logger.info("Initialisation d'Immotep (Service Chat)...")
chat_service = ChatService()

# Chargement du modèle IA (XGBoost)
logger.info("Chargement du modèle IA...")
try:
    model = joblib.load(MODEL_PATH)
except Exception as exc:
    logger.warning(
        "Modèle price_predictor.pkl introuvable : %s - %s",
        type(exc).__name__, exc,
    )
    model = None

# --- ROUTES API ---

@app.route('/api/health', methods=['GET'])
@limiter.exempt
def health():
    """Expose la version du modèle de prédiction actuellement chargé (ORA-31)."""
    model_info = {"model_version": None, "trained_at": None, "metrics": None}
    try:
        with open(MODEL_META_PATH, encoding='utf-8') as f:
            meta = json.load(f)
        model_info = {
            "model_version": meta.get("model_version"),
            "trained_at": meta.get("trained_at"),
            "metrics": meta.get("metrics"),
        }
    except Exception:
        pass

    return jsonify({
        "status": "ok" if model is not None else "degraded",
        "model_loaded": model is not None,
        "model": model_info,
    })

@app.route('/api/listings', methods=['GET'])
def get_listings():
    """
    Renvoie les annonces utilisées pour l'affichage sur la carte.
    ---
    tags:
      - Annonces
    responses:
      200:
        description: Liste des annonces (colonnes réduites, NaN remplacés par '')
        schema:
          type: array
          items:
            type: object
            properties:
              latitude:
                type: number
              longitude:
                type: number
              prix:
                type: number
              type_local:
                type: string
              quartier:
                type: string
    """
    df = data_loader.get_data()
    if df is None:
        return jsonify([])
    
    # On renvoie les colonnes nécessaires uniquement et on gère les NaN
    data = df[['latitude', 'longitude', 'prix', 'type_local', 'quartier']].fillna('').to_dict(orient='records')
    return jsonify(data)

@app.route('/api/annonces', methods=['GET'])
def get_annonces():
    """
    Liste paginée des annonces stockées, filtrable par ville et/ou quartier (ORA-84).
    ---
    tags:
      - Annonces
    parameters:
      - name: ville
        in: query
        type: string
        required: false
      - name: quartier
        in: query
        type: string
        required: false
      - name: page
        in: query
        type: integer
        required: false
        default: 1
      - name: per_page
        in: query
        type: integer
        required: false
        default: 20
    responses:
      200:
        description: Page d'annonces correspondant aux filtres
      400:
        description: Paramètre de pagination invalide
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except ValueError:
        return jsonify({"error": "page et per_page doivent être des entiers"}), 400

    if page < 1 or per_page < 1:
        return jsonify({"error": "page et per_page doivent être positifs"}), 400

    result = annonces_store.list_annonces(
        ville=request.args.get('ville') or None,
        quartier=request.args.get('quartier') or None,
        page=page,
        per_page=per_page,
        db_path=ANNONCES_DB_PATH,
    )
    return jsonify(result)

@app.route('/api/annonces/<int:annonce_id>', methods=['GET'])
def get_annonce_detail(annonce_id):
    """
    Détail d'une annonce par son id (ORA-85).
    ---
    tags:
      - Annonces
    parameters:
      - name: annonce_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Annonce trouvée
      404:
        description: Aucune annonce avec cet id
    """
    annonce = annonces_store.get_annonce_by_id(annonce_id, db_path=ANNONCES_DB_PATH)
    if annonce is None:
        return jsonify({"error": "Annonce introuvable"}), 404
    return jsonify(annonce)

@app.route('/api/annonces/<int:annonce_id>/click', methods=['POST'])
def log_annonce_click(annonce_id):
    """
    Journalise un clic sortant vers l'annonce source (ORA-91), et renvoie le
    nouveau total de vues (ORA-92).
    ---
    tags:
      - Annonces
    parameters:
      - name: annonce_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Clic journalisé
      404:
        description: Aucune annonce avec cet id
    """
    annonce = annonces_store.get_annonce_by_id(annonce_id, db_path=ANNONCES_DB_PATH)
    if annonce is None:
        return jsonify({"error": "Annonce introuvable"}), 404

    annonces_store.log_click(annonce_id, db_path=ANNONCES_DB_PATH)
    views = annonces_store.count_clicks(annonce_id, db_path=ANNONCES_DB_PATH)
    return jsonify({"logged": True, "views": views})

@app.route('/api/quartier-stats', methods=['POST'])
def get_quartier_stats():
    """
    Statistiques réelles (prix moyen, prix/m², nombre de biens) pour un quartier.
    Scan de quartier basé uniquement sur le CSV de données réelles : ne fait
    PAS appel au modèle de Machine Learning.
    ---
    tags:
      - Quartier
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - quartier
          properties:
            quartier:
              type: string
              example: Gerland
            type_local:
              type: string
              example: T2
              default: Tout
    responses:
      200:
        description: >
          Statistiques du quartier (found=true, avec count/prix_moyen/
          prix_m2_moyen/center), ou found=false avec un message si aucun bien
          ne correspond au quartier demandé.
      400:
        description: Le nom du quartier est manquant ou vide
      500:
        description: Données non disponibles ou erreur de traitement
    """
    try:
        raw_payload = get_request_json()
    except Exception:
        return jsonify({"error": "Payload JSON invalide"}), 400

    try:
        payload = QuartierStatsRequestSchema(**raw_payload)
    except (ValidationError, TypeError):
        return jsonify({"error": "Le nom du quartier est vide"}), 400

    quartier_input = payload.quartier.strip()
    type_filter = payload.type_local

    try:
        df = data_loader.get_data()
        if df is None or df.empty:
            return jsonify({"error": "Données non disponibles"}), 500

        # Nettoyage pour éviter les erreurs sur NaN
        df_clean = df.dropna(subset=['quartier', 'prix', 'surface'])

        # Résolution du quartier saisi (accents/casse/tirets + tolérance aux
        # fautes de frappe partagées avec le chat et /api/predict, ORA-110)
        known_quartiers = df_clean['quartier'].unique().tolist()
        resolved_quartier = resolve_quartier(quartier_input, known_quartiers)

        if resolved_quartier is None:
            return jsonify({
                "found": False,
                "message": f"Aucun bien trouvé pour le secteur '{quartier_input}'"
            }), 200

        filtered_df = df_clean[df_clean['quartier'] == resolved_quartier]

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
        
        # Libellé canonique déjà résolu (ex: "Gerland" au lieu de "greland")
        nom_officiel = resolved_quartier
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
            "center": center,
            "facteurs": summarize_cavaliers(filtered_df),
        })

    except Exception as e:
        logger.error(
            "Erreur endpoint /api/quartier-stats : %s - %s",
            type(e).__name__, e, exc_info=True,
        )
        return jsonify({"error": str(e)}), 500

@app.route('/api/quartier-historique', methods=['POST'])
def get_quartier_historique():
    """
    Évolution du prix moyen/m² pour un quartier à travers les snapshots de
    données enregistrés (ORA-72). Avec un seul snapshot (pas assez de recul
    pour une tendance), renvoie status="insufficient_history" plutôt qu'un
    historique trompeur à un seul point.
    ---
    tags:
      - Quartier
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - quartier
          properties:
            quartier:
              type: string
              example: Gerland
            type_local:
              type: string
              example: T2
              default: Tout
    responses:
      200:
        description: >
          historique (liste chronologique de {date, prix_m2_moyen, count})
          et status ("ok" ou "insufficient_history").
      400:
        description: Le nom du quartier est manquant ou vide
    """
    try:
        raw_payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Payload JSON invalide"}), 400

    try:
        payload = QuartierStatsRequestSchema(**raw_payload)
    except (ValidationError, TypeError):
        return jsonify({"error": "Le nom du quartier est vide"}), 400

    quartier_input = payload.quartier.strip()
    type_filter = payload.type_local

    historique, status = compute_price_history(
        quartier_input, type_filter, SNAPSHOTS_DIR, SNAPSHOTS_MANIFEST_PATH
    )

    if status == "insufficient_history":
        return jsonify({
            "found": True,
            "status": "insufficient_history",
            "message": "Pas encore assez d'historique de données pour observer une tendance (un seul snapshot enregistré à ce jour).",
            "historique": [],
        })

    return jsonify({
        "found": True,
        "status": "ok",
        "quartier": quartier_input,
        "historique": historique,
    })

@app.route('/api/predict', methods=['POST'])
def predict():
    """
    Prédiction de prix via le modèle Machine Learning (XGBoost) chargé en mémoire.
    ---
    tags:
      - Prédiction
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - surface
            - quartier
            - type_local
          properties:
            surface:
              type: number
              example: 45
            quartier:
              type: string
              example: Gerland
            type_local:
              type: string
              example: T2
            type:
              type: string
              example: Appartement
            latitude:
              type: number
            longitude:
              type: number
            code_postal:
              type: number
    responses:
      200:
        description: >
          Estimation chiffrée (estimated_price, price_m2, confiance,
          comparables, quartier_detecte, type_local_detecte)
      400:
        description: Payload invalide (champs manquants ou mal typés)
      500:
        description: Modèle ou données de référence indisponibles
    """
    if model is None:
        return jsonify({"error": "Modèle de prédiction indisponible sur ce serveur"}), 500

    df = data_loader.get_data()
    if df is None or df.empty:
        return jsonify({"error": "Données de référence indisponibles"}), 500

    try:
        payload = get_request_json()
    except Exception:
        return jsonify({"error": "Payload JSON invalide"}), 400

    try:
        PredictRequestSchema(**payload)
    except (ValidationError, TypeError):
        return jsonify({
            "error": "Payload invalide",
            "details": ["Le format des champs envoyés est incorrect."],
        }), 400

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
    """
    Chatbot Immotep : réponse groundée sur les données réelles, ou via Gemini.
    ---
    tags:
      - Chat
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - message
          properties:
            message:
              type: string
              example: Que vaut un T2 à Gerland ?
            context:
              type: string
              example: "Quartier: Gerland, Type: T2"
    responses:
      200:
        description: >
          Réponse du chatbot, incluant selon le cas intent/parsed/
          recommendations/comparisons/map_focus
      400:
        description: Message vide ou payload invalide
      429:
        description: Limite de requêtes dépassée (RATE_LIMIT_CHAT)
      500:
        description: Erreur interne côté serveur
    """
    try:
        data = get_request_json()

        try:
            payload = ChatRequestSchema(**data)
        except (ValidationError, TypeError):
            return jsonify({"response": "Silence... Tu n'as rien à dire ?"}), 400

        # On récupère le message utilisateur et le contexte envoyé par le front
        user_msg = payload.message
        context = payload.context

        # On récupère le DataFrame complet
        df = data_loader.get_data()

        # On appelle le service dédié qui gère le prompt, le parsing et Gemini
        result_immotep = chat_service.get_chat_result(user_msg, context, df)

        return jsonify(result_immotep)

    except Exception as e:
        logger.error(
            "Erreur endpoint /api/chat : %s - %s",
            type(e).__name__, e, exc_info=True,
        )
        return jsonify({"response": "Erreur interne côté serveur. Immotep revient dès que l'API répond correctement."}), 500

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=get_server_port())
