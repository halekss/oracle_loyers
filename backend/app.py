import os
import requests
import joblib
import pandas as pd
import numpy as np
import re
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from scipy.spatial import distance

from services.data_loader import DataLoader
from services.map_generator import MapGenerator

print("🔥 ORACLE v10.1 FIXED - Bug JSON corrigé")

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')
CSV_PATH = os.path.join(DATA_DIR, 'master_immo_final.csv')

LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', "http://host.docker.internal:1234/v1/chat/completions")

os.makedirs(STATIC_DIR, exist_ok=True)

# ============================================================================
# 🔧 HELPER : CONVERSION NUMPY → PYTHON NATIF (FIX JSON)
# ============================================================================
def to_python_type(value):
    """Convertit les types numpy en types Python natifs pour JSON"""
    if isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32)):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif pd.isna(value):
        return None
    return value


# ============================================================================
# 📍 MAPPING QUARTIERS → CODE POSTAL
# ============================================================================
QUARTIERS_MAPPING = {
    "terreaux": "69001",
    "pentes": "69001",
    "ainay": "69002",
    "confluence": "69002",
    "bellecour": "69002",
    "part-dieu": "69003",
    "part dieu": "69003",
    "montchat": "69003",
    "guillotiere": "69007",
    "guillotière": "69007",
    "croix-rousse": "69004",
    "croix rousse": "69004",
    "vieux lyon": "69005",
    "brotteaux": "69006",
    "gerland": "69007",
    "jean mace": "69007",
    "jean macé": "69007",
    "monplaisir": "69008",
    "vaise": "69009"
}

# CHARGEMENT DONNÉES
data_loader = DataLoader(DATA_DIR)
data_loader.load_csvs()
df = data_loader.df_immo

if not df.empty and 'type_local' in df.columns:
    df['type_local'] = df['type_local'].fillna('').astype(str)

map_generator = MapGenerator(STATIC_DIR, DATA_DIR)
map_generator.generate(data_loader)

model = None
df_full = None
X_columns = None
PRIX_MAX_LOCATION = 5000

try:
    if os.path.exists(MODEL_PATH) and os.path.exists(CSV_PATH):
        model = joblib.load(MODEL_PATH)
        df_full = pd.read_csv(CSV_PATH)
        X_columns = model.feature_names_in_
        print(f"✅ Modèle + Dataset chargés : {len(df_full)} annonces")
except Exception as e:
    print(f"⚠️ Erreur chargement : {e}")


# ============================================================================
# 🔧 FONCTION : STATS PAR CODE POSTAL
# ============================================================================
def get_stats_by_code_postal(code_postal, surface=65):
    """Calcule les vraies stats d'un quartier depuis son code postal"""
    if df_full is None or df_full.empty:
        return None
    
    try:
        zone = df_full[df_full['code_postal'].astype(str) == str(code_postal)]
        
        if zone.empty:
            print(f"⚠️ Aucune annonce pour {code_postal}")
            return None
        
        # Calculs avec conversion Python natif
        prix_m2_moyen = to_python_type(zone['prix_m2'].mean())
        prix_estime = to_python_type(prix_m2_moyen * surface)
        nb_annonces = to_python_type(len(zone))
        prix_min = to_python_type(zone['prix'].min())
        prix_max = to_python_type(zone['prix'].max())
        
        # Scores
        vice_score = 0
        gentrif_score = 0
        nuisance_score = 0
        
        if 'nb_vice_bar_500m' in zone.columns:
            vice_bars = to_python_type(zone['nb_vice_bar_500m'].mean())
            vice_kebabs = to_python_type(zone['nb_vice_kebab_500m'].mean()) if 'nb_vice_kebab_500m' in zone.columns else 0
            vice_score = min(10, (vice_bars + vice_kebabs) / 5)
        
        if 'nb_gentrification_yoga_500m' in zone.columns:
            gentrif_yoga = to_python_type(zone['nb_gentrification_yoga_500m'].mean())
            gentrif_torrefi = to_python_type(zone['nb_gentrification_torréfacteur_500m'].mean()) if 'nb_gentrification_torréfacteur_500m' in zone.columns else 0
            gentrif_score = min(10, (gentrif_yoga + gentrif_torrefi) / 3)
        
        if 'nb_nuisance_école_500m' in zone.columns:
            nuisance_ecoles = to_python_type(zone['nb_nuisance_école_500m'].mean())
            nuisance_aires = to_python_type(zone['nb_nuisance_aire_de_jeux_500m'].mean()) if 'nb_nuisance_aire_de_jeux_500m' in zone.columns else 0
            nuisance_score = min(10, (nuisance_ecoles + nuisance_aires) / 10)
        
        return {
            "prix_m2": round(prix_m2_moyen, 1),
            "prix_estime": round(prix_estime),
            "nb_annonces": nb_annonces,
            "prix_min": round(prix_min),
            "prix_max": round(prix_max),
            "scores": {
                "vice": round(vice_score, 1),
                "gentrification": round(gentrif_score, 1),
                "nuisance": round(nuisance_score, 1)
            }
        }
        
    except Exception as e:
        print(f"❌ Erreur get_stats_by_code_postal : {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# 🔧 FONCTION : DÉTECTER QUARTIER DANS MESSAGE
# ============================================================================
def detect_quartier_in_message(message):
    """Détecte si un quartier est mentionné"""
    msg_lower = message.lower()
    
    for quartier, code_postal in QUARTIERS_MAPPING.items():
        if quartier in msg_lower:
            print(f"✅ Quartier détecté : {quartier} → {code_postal}")
            return quartier, code_postal
    
    return None, None


# ============================================================================
# 🔧 FONCTION : STATS DEPUIS COORDONNÉES
# ============================================================================
def get_stats_from_coords(lat, lon, radius_km=0.5):
    """Stats autour de coordonnées GPS"""
    if df_full is None or df_full.empty:
        return None
    
    try:
        def haversine(lat1, lon1, lat2, lon2):
            from math import radians, sin, cos, sqrt, atan2
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            return 6371 * 2 * atan2(sqrt(a), sqrt(1-a))
        
        df_full['distance'] = df_full.apply(
            lambda row: haversine(lat, lon, row['latitude'], row['longitude']),
            axis=1
        )
        
        nearby = df_full[df_full['distance'] <= radius_km]
        
        if nearby.empty:
            closest_idx = df_full['distance'].idxmin()
            nearby = df_full.iloc[[closest_idx]]
        
        # Conversions Python natif
        prix_m2_moyen = to_python_type(nearby['prix_m2'].mean())
        nb_annonces = to_python_type(len(nearby))
        ville = to_python_type(nearby.iloc[0]['ville']) if not nearby.empty else "Lyon"
        code_postal = to_python_type(nearby.iloc[0]['code_postal']) if not nearby.empty else "69000"
        prix_min = to_python_type(nearby['prix'].min())
        prix_max = to_python_type(nearby['prix'].max())
        
        # Scores
        vice_score = 0
        gentrif_score = 0
        nuisance_score = 0
        
        if 'nb_vice_bar_500m' in nearby.columns:
            vice_bars = to_python_type(nearby['nb_vice_bar_500m'].mean())
            vice_kebabs = to_python_type(nearby['nb_vice_kebab_500m'].mean()) if 'nb_vice_kebab_500m' in nearby.columns else 0
            vice_score = min(10, (vice_bars + vice_kebabs) / 5)
        
        if 'nb_gentrification_yoga_500m' in nearby.columns:
            gentrif_yoga = to_python_type(nearby['nb_gentrification_yoga_500m'].mean())
            gentrif_score = min(10, gentrif_yoga / 3)
        
        if 'nb_nuisance_école_500m' in nearby.columns:
            nuisance_ecoles = to_python_type(nearby['nb_nuisance_école_500m'].mean())
            nuisance_score = min(10, nuisance_ecoles / 10)
        
        return {
            "prix_m2_moyen": round(prix_m2_moyen, 1),
            "nb_annonces": nb_annonces,
            "ville": ville,
            "code_postal": str(code_postal),
            "prix_min": round(prix_min),
            "prix_max": round(prix_max),
            "scores": {
                "vice": round(vice_score, 1),
                "gentrification": round(gentrif_score, 1),
                "nuisance": round(nuisance_score, 1)
            }
        }
        
    except Exception as e:
        print(f"❌ Erreur get_stats_from_coords : {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# 🤖 ML
# ============================================================================
def preprocess_for_ml(surface, latitude, longitude):
    if model is None or df_full is None or df_full.empty:
        return None, None
    
    try:
        locations = df_full[['latitude', 'longitude']].astype(float).values
        user_point = np.array([[latitude, longitude]])
        distances = distance.cdist(user_point, locations, 'euclidean')
        closest_idx = distances.argmin()
        neighbor_row = df_full.iloc[closest_idx].copy()
        
        neighbor_row['surface'] = surface
        
        features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 
                           'description', 'ville', 'titre', 'date']
        
        df_temp = pd.DataFrame([neighbor_row])
        X = df_temp.drop(columns=features_to_drop, errors='ignore')
        
        cols_nb = [c for c in X.columns if c.startswith('nb_')]
        X = X.drop(columns=cols_nb)
        
        X = pd.get_dummies(X, drop_first=True)
        X = X.reindex(columns=X_columns, fill_value=0)
        
        return X, neighbor_row
        
    except Exception as e:
        print(f"❌ Erreur preprocessing : {e}")
        return None, None


def predict_price_ml(surface, latitude, longitude):
    if model is None:
        return None
    
    result = preprocess_for_ml(surface, latitude, longitude)
    if result[0] is None:
        return None
    
    X_prepared, neighbor_row = result
    
    try:
        prix_estime_brut = float(model.predict(X_prepared)[0])
        
        if prix_estime_brut > PRIX_MAX_LOCATION:
            prix_voisin = neighbor_row.get('prix', None)
            prix_m2_voisin = neighbor_row.get('prix_m2', None)
            
            if prix_voisin and not pd.isna(prix_voisin):
                if prix_m2_voisin and not pd.isna(prix_m2_voisin):
                    prix_estime = float(prix_m2_voisin) * surface
                else:
                    ratio = surface / float(neighbor_row.get('surface', surface))
                    prix_estime = float(prix_voisin) * ratio
                method = "Voisin"
            else:
                prix_estime = 15.0 * surface
                method = "Moyenne"
        else:
            prix_estime = prix_estime_brut
            method = "ML"
        
        prix_m2 = prix_estime / surface if surface > 0 else 0
        ville = to_python_type(neighbor_row.get('ville', 'Lyon'))
        
        return {
            "estimated_price": round(prix_estime),
            "prix_m2": round(prix_m2),
            "surface": float(surface),
            "method": method,
            "ville": ville
        }
        
    except Exception as e:
        print(f"❌ Erreur ML : {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# 🧠 MISTRAL
# ============================================================================
def ask_mistral_corrected(user_message, prix_estime_scan, prix_m2_scan, surface, quartier_scan, lat, lon):
    try:
        quartier_mentionne, code_postal_mentionne = detect_quartier_in_message(user_message)
        
        if quartier_mentionne and code_postal_mentionne:
            print(f"🔍 Quartier mentionné : {quartier_mentionne} ({code_postal_mentionne})")
            
            stats_autre = get_stats_by_code_postal(code_postal_mentionne, surface)
            
            if stats_autre:
                prompt = f"""Tu es l'Oracle de Lyon.

L'utilisateur a scanné **{quartier_scan}** ({prix_estime_scan}€ pour {surface}m²)
Mais il demande : "{user_message}"

VRAIES DONNÉES DE {quartier_mentionne.upper()} (code {code_postal_mentionne}) :
- Prix moyen : **{stats_autre['prix_estime']}€** pour {surface}m²
- Prix/m² : **{stats_autre['prix_m2']}€/m²**
- {stats_autre['nb_annonces']} annonces
- Fourchette : {stats_autre['prix_min']}€ - {stats_autre['prix_max']}€
- Score Vice : {stats_autre['scores']['vice']}/10
- Score Gentrification : {stats_autre['scores']['gentrification']}/10

Réponds en 2-3 phrases AVEC LES VRAIS CHIFFRES.
Argot lyonnais (gone).

Réponse :"""
            else:
                prompt = f"""Pas de données pour {quartier_mentionne}. Dis-le en 1 phrase."""
        
        else:
            stats_scan = get_stats_from_coords(lat, lon)
            
            if stats_scan:
                prompt = f"""Tu es l'Oracle de Lyon.

SCAN ACTUEL ({quartier_scan}) :
- Prix : {prix_estime_scan}€ ({prix_m2_scan}€/m²)
- {stats_scan['nb_annonces']} annonces zone
- Fourchette : {stats_scan['prix_min']}€ - {stats_scan['prix_max']}€
- Score Vice : {stats_scan['scores']['vice']}/10

Question : "{user_message}"

Réponds en 2-3 phrases, ton cash.

Réponse :"""
            else:
                prompt = f"""Erreur données."""
        
        payload = {
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 250
        }
        
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return "⚠️ Erreur technique"
            
    except Exception as e:
        print(f"❌ Erreur Mistral : {e}")
        import traceback
        traceback.print_exc()
        return "⚠️ Erreur interne"


# ============================================================================
# 🌐 ROUTES
# ============================================================================
@app.route('/')
def home():
    return jsonify({
        "status": "Oracle v10.1 FIXED - Bug JSON corrigé",
        "data_source": "master_immo_final.csv",
        "nb_annonces": len(df_full) if df_full is not None else 0
    })


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
    if df.empty:
        return jsonify({"error": "Données non chargées"}), 500

    try:
        data = request.json
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        surface = float(data.get('surface', 35))
        
        ml_result = predict_price_ml(surface, lat, lon)
        stats = get_stats_from_coords(lat, lon)
        
        if ml_result and stats:
            return jsonify({
                "estimated_price": ml_result["estimated_price"],
                "analysis": f"🔮 {ml_result['estimated_price']} € pour {surface} m² ({ml_result['prix_m2']} €/m²)",
                "stats": {
                    "prix_m2": ml_result["prix_m2"],
                    "method": ml_result["method"],
                    "surface": ml_result["surface"],
                    "nb_annonces_zone": stats["nb_annonces"],
                    "prix_m2_zone": stats["prix_m2_moyen"]
                },
                "details": {
                    "latitude": lat,
                    "longitude": lon,
                    "ville": ml_result.get("ville", "Lyon"),
                    "code_postal": stats.get("code_postal", "69000")
                },
                "scores": stats["scores"],
                "currency": "EUR"
            })
        else:
            return jsonify({"error": "Prédiction impossible"}), 500
            
    except Exception as e:
        print(f"❌ Erreur predict : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat_oracle():
    try:
        data = request.json
        user_msg = data.get('message', '').strip()
        context = data.get('context', None)
        
        if not user_msg:
            return jsonify({"response": "⚠️ Parle, gone."})
        
        if not context:
            return jsonify({"response": "Fais un SCAN d'abord."})
        
        # Parser contexte
        prix_estime = 0
        prix_m2 = 0
        surface = 0
        quartier = "Lyon"
        lat = 45.75
        lon = 4.85
        
        lines = context.split('\n')
        for line in lines:
            if 'prix estimé' in line.lower():
                match = re.search(r'(\d+)\s*€', line)
                if match:
                    prix_estime = int(match.group(1))
            
            if 'prix au m²' in line.lower():
                match = re.search(r'(\d+)\s*€', line)
                if match:
                    prix_m2 = int(match.group(1))
            
            if 'surface' in line.lower():
                match = re.search(r'(\d+(?:\.\d+)?)\s*m', line)
                if match:
                    surface = float(match.group(1))
            
            if 'ville' in line.lower() or 'quartier' in line.lower():
                parts = line.split(':')
                if len(parts) > 1:
                    quartier = parts[1].strip()
            
            if 'position' in line.lower() or 'latitude' in line.lower():
                match = re.search(r'([\d.]+),\s*([\d.]+)', line)
                if match:
                    lat = float(match.group(1))
                    lon = float(match.group(2))
        
        print(f"📊 Contexte : {quartier} | {prix_estime}€ | {lat},{lon}")
        
        response = ask_mistral_corrected(user_msg, prix_estime, prix_m2, surface, quartier, lat, lon)
        
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"response": "⚠️ Erreur interne"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)