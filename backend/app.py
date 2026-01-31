import os
import requests
import joblib
import pandas as pd
import numpy as np
import re
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from scipy.spatial import distance

# --- SERVICES ---
from services.data_loader import DataLoader
from services.map_generator import MapGenerator

print("🔥 ORACLE v6.1 ULTRA - Prompt Agressif + Bible Enrichie")

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')
CSV_PATH = os.path.join(DATA_DIR, 'master_immo_final.csv')

LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', "http://host.docker.internal:1234/v1/chat/completions")
print(f"🔗 LM Studio URL : {LM_STUDIO_URL}")

os.makedirs(STATIC_DIR, exist_ok=True)

# ============================================================================
# 🔮 BIBLE ULTIME DES QUARTIERS - ENRICHIE AVEC PRIX MOYENS
# ============================================================================
LYON_BIBLE = {
    # --- LYON 1er ---
    "terreaux": {
        "description": "L'épicentre du bruit. Skateurs, bars, zéro silence.",
        "prix_m2": 30,
        "ambiance": "festif_bruyant"
    },
    "pentes": {
        "description": "Mollets en béton requis. Bobos et graffitis partout.",
        "prix_m2": 28,
        "ambiance": "bobo_sportif"
    },
    "69001": {
        "description": "Lyon 1er : Cœur historique. Oublie le calme.",
        "prix_m2": 29,
        "ambiance": "central_vivant"
    },

    # --- LYON 2ème ---
    "ainay": {
        "description": "Aristocratie lyonnaise. Mocassins à glands obligatoires.",
        "prix_m2": 34,
        "ambiance": "chic_snob"
    },
    "confluence": {
        "description": "Quartier SimCity. Cubes modernes, vide le soir.",
        "prix_m2": 32,
        "ambiance": "moderne_desert"
    },
    "bellecour": {
        "description": "Centre du monde. Métro pratique, manifestations garanties.",
        "prix_m2": 36,
        "ambiance": "ultra_central"
    },
    "69002": {
        "description": "Lyon 2ème : Presqu'île chic. Beau, plat, cher.",
        "prix_m2": 34,
        "ambiance": "prestige"
    },

    # --- LYON 3ème ---
    "part-dieu": {
        "description": "Béton, gares, dépression architecturale.",
        "prix_m2": 26,
        "ambiance": "business_froid"
    },
    "part dieu": {
        "description": "Béton, gares, dépression architecturale.",
        "prix_m2": 26,
        "ambiance": "business_froid"
    },
    "montchat": {
        "description": "Village des familles parfaites. Calme de campagne.",
        "prix_m2": 24,
        "ambiance": "familial_calme"
    },
    "guillotière": {
        "description": "Far West lyonnais. Ça vit, ça crie.",
        "prix_m2": 20,
        "ambiance": "street_populaire"
    },
    "69003": {
        "description": "Lyon 3ème : Mélange business et vie de famille.",
        "prix_m2": 24,
        "ambiance": "mixte"
    },

    # --- LYON 4ème ---
    "croix-rousse": {
        "description": "Plateau bobo. Pentes et entre-soi garanti.",
        "prix_m2": 30,
        "ambiance": "bobo_superieur"
    },
    "croix rousse": {
        "description": "Plateau bobo. Pentes et entre-soi garanti.",
        "prix_m2": 30,
        "ambiance": "bobo_superieur"
    },
    "69004": {
        "description": "Lyon 4ème : Colline qui télétravaille au chai latte.",
        "prix_m2": 30,
        "ambiance": "bobo"
    },

    # --- LYON 5ème ---
    "vieux lyon": {
        "description": "Disneyland médiéval. Pavés + 4000 touristes.",
        "prix_m2": 28,
        "ambiance": "touristique"
    },
    "69005": {
        "description": "Lyon 5ème : Pavés, histoire, touristes en masse.",
        "prix_m2": 27,
        "ambiance": "historique"
    },

    # --- LYON 6ème ---
    "brotteaux": {
        "description": "Bunker des riches. Propre, large, calme, ennuyeux.",
        "prix_m2": 38,
        "ambiance": "riche_ennuyeux"
    },
    "69006": {
        "description": "Lyon 6ème : Le plus riche. Ennuyeux à mourir le dimanche.",
        "prix_m2": 38,
        "ambiance": "bourgeois"
    },

    # --- LYON 7ème ---
    "gerland": {
        "description": "Stades, bureaux, vide le soir.",
        "prix_m2": 22,
        "ambiance": "industriel_calme"
    },
    "69007": {
        "description": "Lyon 7ème : Street-life crade + gentrification hipster.",
        "prix_m2": 23,
        "ambiance": "contraste"
    },

    # --- LYON 8ème ---
    "monplaisir": {
        "description": "Village familial. 'Sympa' = rien à faire le soir.",
        "prix_m2": 20,
        "ambiance": "familial_ennuyeux"
    },
    "69008": {
        "description": "Lyon 8ème : Calme absolu. Bon compromis si t'es loin du centre.",
        "prix_m2": 20,
        "ambiance": "peripherique"
    },

    # --- LYON 9ème ---
    "vaise": {
        "description": "Silicon Valley lyonnaise (en moins cher). Tech et immeubles neufs.",
        "prix_m2": 24,
        "ambiance": "startup_loin"
    },
    "69009": {
        "description": "Lyon 9ème : Ouest lointain. Start-ups et barres.",
        "prix_m2": 23,
        "ambiance": "eloigne"
    }
}

# 1. CHARGEMENT DONNÉES
data_loader = DataLoader(DATA_DIR)
data_loader.load_csvs()
df = data_loader.df_immo

if not df.empty and 'type_local' in df.columns:
    df['type_local'] = df['type_local'].fillna('').astype(str)

# 2. GÉNÉRATION CARTE
map_generator = MapGenerator(STATIC_DIR, DATA_DIR)
map_generator.generate(data_loader)

# 3. CHARGEMENT MODÈLE ML
model = None
df_full = None
X_columns = None
PRIX_MAX_LOCATION = 5000

try:
    if os.path.exists(MODEL_PATH) and os.path.exists(CSV_PATH):
        model = joblib.load(MODEL_PATH)
        df_full = pd.read_csv(CSV_PATH)
        X_columns = model.feature_names_in_
        print(f"✅ Modèle ML chargé ({len(X_columns)} features)")
except Exception as e:
    print(f"⚠️ Erreur chargement ML : {e}")


# --- FONCTION : TROUVER LA DESCRIPTION DU QUARTIER ---
def get_quartier_info(ville_ou_code_postal):
    """
    Recherche les infos du quartier dans la BIBLE.
    Retourne {description, prix_m2, ambiance} ou fallback.
    """
    if not ville_ou_code_postal:
        return {
            "description": "Un quartier lambda de Lyon.",
            "prix_m2": 25,
            "ambiance": "inconnu"
        }
    
    search_key = str(ville_ou_code_postal).lower().replace('-', ' ').strip()
    
    # Chercher directement
    if search_key in LYON_BIBLE:
        return LYON_BIBLE[search_key]
    
    # Chercher par correspondance partielle
    for key, info in LYON_BIBLE.items():
        if search_key in key or key in search_key:
            return info
    
    # Fallback
    return {
        "description": f"Un coin de Lyon sans grand caractère.",
        "prix_m2": 25,
        "ambiance": "moyen"
    }


# --- FONCTION ML : PREPROCESSING ---
def preprocess_for_ml(surface, latitude, longitude):
    """Prépare les features pour la prédiction ML"""
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


# --- FONCTION ML : PRÉDICTION ---
def predict_price_ml(surface, latitude, longitude):
    """Prédit le prix avec XGBoost + correction des aberrations"""
    if model is None:
        return None
    
    result = preprocess_for_ml(surface, latitude, longitude)
    if result[0] is None:
        return None
    
    X_prepared, neighbor_row = result
    
    try:
        prix_estime_brut = model.predict(X_prepared)[0]
        
        if prix_estime_brut > PRIX_MAX_LOCATION:
            print(f"⚠️ Prix aberrant : {prix_estime_brut:.0f}€ → Fallback voisin")
            prix_voisin = neighbor_row.get('prix', None)
            prix_m2_voisin = neighbor_row.get('prix_m2', None)
            
            if prix_voisin and not pd.isna(prix_voisin):
                if prix_m2_voisin and not pd.isna(prix_m2_voisin):
                    prix_estime = prix_m2_voisin * surface
                else:
                    ratio = surface / neighbor_row.get('surface', surface)
                    prix_estime = prix_voisin * ratio
                method = "Voisin (ML corrigé)"
            else:
                prix_estime = 15 * surface
                method = "Moyenne (ML défaillant)"
        else:
            prix_estime = prix_estime_brut
            method = "ML (XGBoost)"
        
        prix_m2 = prix_estime / surface if surface > 0 else 0
        ville = neighbor_row.get('ville', 'Lyon')
        
        return {
            "estimated_price": round(prix_estime),
            "prix_m2": round(prix_m2),
            "surface": surface,
            "method": method,
            "ville": ville
        }
        
    except Exception as e:
        print(f"❌ Erreur prédiction ML : {e}")
        return None


# --- FONCTION : DÉTECTION D'INTENTION ---
def detect_intent(message):
    """Détecte l'intention de la question"""
    msg_lower = message.lower()
    
    # Comparaison
    if any(word in msg_lower for word in ['compar', 'vs', 'différence', 'mieux', 'plutôt']):
        return 'compare'
    
    # Demande de prix d'un autre quartier
    quartiers_mentions = []
    for key in LYON_BIBLE.keys():
        if key in msg_lower and key not in ['69001', '69002', '69003', '69004', '69005', '69006', '69007', '69008', '69009']:
            quartiers_mentions.append(key)
    
    if len(quartiers_mentions) > 0:
        return 'autre_quartier'
    
    # Question générale
    return 'general'


# --- FONCTION IA : MISTRAL AVEC RAG RIGIDE ---
def ask_mistral_rag(user_message, prix_estime, prix_m2, surface, quartier):
    """Appelle Mistral avec un prompt RAG ULTRA-RIGIDE et COURT"""
    try:
        # Récupérer les infos du quartier
        quartier_info = get_quartier_info(quartier)
        description_quartier = quartier_info["description"]
        prix_m2_quartier = quartier_info["prix_m2"]
        
        # Détection d'intention
        intent = detect_intent(user_message)
        
        # Construction du prompt selon l'intention
        if intent == 'autre_quartier':
            # L'utilisateur demande un autre quartier
            prompt_rigide = f"""### DONNÉES DU SCAN ACTUEL :
Quartier scanné : {quartier}
Loyer : {prix_estime} €
Prix/m² : {prix_m2} €/m²

### RÈGLE :
T'as scanné {quartier}. Si on te demande un autre quartier, tu réorientes SEC.

### QUESTION :
{user_message}

### RÉPONSE (2 PHRASES MAX, CASH) :"""

        elif intent == 'compare':
            # L'utilisateur veut comparer
            prompt_rigide = f"""### DONNÉES DU SCAN :
Quartier : {quartier} ({prix_m2}€/m²)
Description : {description_quartier}

### BASE DE DONNÉES (Prix moyens au m²) :
{format_bible_for_comparison()}

### QUESTION :
{user_message}

### RÉPONSE (MAX 3 PHRASES, AVEC CHIFFRES RÉELS) :"""

        else:
            # Question générale sur le quartier scanné
            prompt_rigide = f"""### DONNÉES DU SCAN :
- Quartier : {quartier}
- Loyer : {prix_estime} €
- Prix/m² : {prix_m2} €/m²
- Ambiance : {description_quartier}

### TON RÔLE :
Oracle de Lyon, cynique et cash. Argot lyonnais (gone, mâchon).
INTERDIT d'inventer des prix.
MAX 2-3 PHRASES.

### EXEMPLES DE BONNES RÉPONSES :
Q: "C'est cher ?"
R: "Pour Ainay, {prix_estime}€ c'est dans la norme, gone. Les aristos payent cher leurs mocassins."

Q: "C'est bien ?"
R: "{description_quartier} Si t'aimes ça, vas-y."

### QUESTION :
{user_message}

### RÉPONSE (2-3 PHRASES MAX) :"""

        payload = {
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt_rigide}],
            "temperature": 0.3,  # Encore plus bas
            "max_tokens": 200  # Encore plus court
        }
        
        print(f"📤 Envoi RAG à LM Studio (température 0.3)...")
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"❌ Erreur LM Studio {response.status_code}")
            return f"⚠️ Hoquet technique (Code {response.status_code})"
            
    except requests.exceptions.ConnectionError:
        return "🔴 L'Oracle est injoignable. Vérifie LM Studio (port 1234)."
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return "⚠️ Erreur technique."


def format_bible_for_comparison():
    """Formate la Bible pour les comparaisons"""
    lines = []
    for key, info in LYON_BIBLE.items():
        if not key.startswith('690'):  # Ignorer les codes postaux
            lines.append(f"- {key.title()}: {info['prix_m2']}€/m²")
    return "\n".join(lines[:15])  # Top 15


# --- ROUTES API ---

@app.route('/')
def home():
    return jsonify({
        "status": "Oracle v6.1 ULTRA - Prompt Agressif", 
        "model_loaded": model is not None,
        "lm_studio": LM_STUDIO_URL,
        "bible_size": len(LYON_BIBLE)
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
    """Route SCAN"""
    if df.empty:
        return jsonify({"error": "Données non chargées"}), 500

    try:
        data = request.json
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        surface = float(data.get('surface', 35))
        
        ml_result = predict_price_ml(surface, lat, lon)
        
        if ml_result:
            return jsonify({
                "estimated_price": ml_result["estimated_price"],
                "analysis": f"🔮 {ml_result['estimated_price']} € pour {surface} m² ({ml_result['prix_m2']} €/m²)",
                "stats": {
                    "prix_m2": ml_result["prix_m2"],
                    "method": ml_result["method"],
                    "surface": surface
                },
                "details": {
                    "latitude": lat,
                    "longitude": lon,
                    "ville": ml_result.get("ville", "Lyon")
                },
                "currency": "EUR"
            })
        else:
            locations = df[['latitude', 'longitude']].astype(float).values
            user_point = np.array([[lat, lon]])
            distances = distance.cdist(user_point, locations, 'euclidean')
            closest_idx = distances.argmin()
            neighbor = df.iloc[closest_idx].to_dict()
            
            prix_m2 = neighbor.get('prix_m2', 15)
            price = prix_m2 * surface
            
            return jsonify({
                "estimated_price": round(price),
                "analysis": f"📍 Basé sur le voisin",
                "stats": {
                    "prix_m2": round(prix_m2),
                    "method": "Nearest Neighbor",
                    "surface": surface
                },
                "details": {
                    "ville": neighbor.get('ville', 'Lyon')
                },
                "currency": "EUR"
            })
            
    except Exception as e:
        print(f"❌ Erreur predict : {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat_oracle():
    """Route CHAT avec RAG rigide"""
    try:
        data = request.json
        user_msg = data.get('message', '').strip()
        context = data.get('context', None)
        
        if not user_msg:
            return jsonify({"response": "⚠️ Parle, gone."})
        
        print(f"💬 Question : {user_msg}")
        
        if not context:
            return jsonify({
                "response": "Fais un SCAN d'abord, je suis pas devin."
            })
        
        # Parser le contexte
        prix_estime = 0
        prix_m2 = 0
        surface = 0
        quartier = "Lyon"
        
        lines = context.split('\n')
        for line in lines:
            if 'prix estimé' in line.lower() or 'loyer' in line.lower():
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
            
            if 'ville' in line.lower():
                parts = line.split(':')
                if len(parts) > 1:
                    quartier = parts[1].strip()
        
        print(f"📊 Contexte : {quartier} | {prix_estime}€ | {prix_m2}€/m² | {surface}m²")
        
        # Appel Mistral
        response = ask_mistral_rag(user_msg, prix_estime, prix_m2, surface, quartier)
        
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"response": "⚠️ Erreur interne."})


# --- LANCEMENT ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)