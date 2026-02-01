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

print("🔥 ORACLE v7.0 PREMIUM - Scores + Calculs Financiers + Vie Pratique")

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
# 🔮 BIBLE PREMIUM DES QUARTIERS - ENRICHIE AU MAX
# ============================================================================
LYON_BIBLE = {
    # --- LYON 1er ---
    "terreaux": {
        "description": "L'épicentre du bruit. Skateurs, bars, zéro silence.",
        "prix_m2": 30,
        "ambiance": 8,
        "transports": 9,
        "commerces": 9,
        "vie_nocturne": 9,
        "metro": "Hôtel de Ville (A, C)",
        "verdict": "Central mais bruyant"
    },
    "pentes": {
        "description": "Mollets en béton requis. Bobos et graffitis.",
        "prix_m2": 28,
        "ambiance": 7,
        "transports": 7,
        "commerces": 8,
        "vie_nocturne": 8,
        "metro": "Croix-Paquet (C)",
        "verdict": "Bobo mais fatiguant"
    },
    "69001": {
        "description": "Lyon 1er : Cœur historique. Oublie le calme.",
        "prix_m2": 29,
        "ambiance": 8,
        "transports": 9,
        "commerces": 9,
        "vie_nocturne": 9,
        "metro": "Hôtel de Ville",
        "verdict": "Ultra central"
    },

    # --- LYON 2ème ---
    "ainay": {
        "description": "Aristocratie lyonnaise. Mocassins à glands obligatoires.",
        "prix_m2": 34,
        "ambiance": 6,
        "transports": 9,
        "commerces": 8,
        "vie_nocturne": 5,
        "metro": "Ampère-Victor Hugo (A)",
        "verdict": "Chic mais coincé"
    },
    "confluence": {
        "description": "Quartier SimCity. Cubes modernes, vide le soir.",
        "prix_m2": 32,
        "ambiance": 5,
        "transports": 7,
        "commerces": 6,
        "vie_nocturne": 3,
        "metro": "Confluence (T1)",
        "verdict": "Moderne mais mort"
    },
    "bellecour": {
        "description": "Centre du monde. Métro pratique, manifestations garanties.",
        "prix_m2": 36,
        "ambiance": 7,
        "transports": 10,
        "commerces": 10,
        "vie_nocturne": 7,
        "metro": "Bellecour (A, D)",
        "verdict": "Top mais cher"
    },
    "69002": {
        "description": "Lyon 2ème : Presqu'île chic. Beau, plat, cher.",
        "prix_m2": 34,
        "ambiance": 7,
        "transports": 9,
        "commerces": 9,
        "vie_nocturne": 6,
        "metro": "Bellecour",
        "verdict": "Prestigieux"
    },

    # --- LYON 3ème ---
    "part-dieu": {
        "description": "Béton, gares, dépression architecturale.",
        "prix_m2": 26,
        "ambiance": 4,
        "transports": 10,
        "commerces": 8,
        "vie_nocturne": 5,
        "metro": "Part-Dieu (B)",
        "verdict": "Pratique mais moche"
    },
    "part dieu": {
        "description": "Béton, gares, dépression architecturale.",
        "prix_m2": 26,
        "ambiance": 4,
        "transports": 10,
        "commerces": 8,
        "vie_nocturne": 5,
        "metro": "Part-Dieu (B)",
        "verdict": "Pratique mais moche"
    },
    "montchat": {
        "description": "Village des familles parfaites. Calme de campagne.",
        "prix_m2": 24,
        "ambiance": 6,
        "transports": 6,
        "commerces": 7,
        "vie_nocturne": 3,
        "metro": "Grange Blanche (D)",
        "verdict": "Familial tranquille"
    },
    "guillotière": {
        "description": "Far West lyonnais. Ça vit, ça crie.",
        "prix_m2": 20,
        "ambiance": 7,
        "transports": 8,
        "commerces": 9,
        "vie_nocturne": 8,
        "metro": "Guillotière (D)",
        "verdict": "Vivant mais crade"
    },
    "69003": {
        "description": "Lyon 3ème : Mélange business et famille.",
        "prix_m2": 24,
        "ambiance": 5,
        "transports": 8,
        "commerces": 8,
        "vie_nocturne": 6,
        "metro": "Part-Dieu",
        "verdict": "Mixte"
    },

    # --- LYON 4ème ---
    "croix-rousse": {
        "description": "Plateau bobo. Pentes et entre-soi garanti.",
        "prix_m2": 30,
        "ambiance": 8,
        "transports": 7,
        "commerces": 8,
        "vie_nocturne": 7,
        "metro": "Croix-Rousse (C)",
        "verdict": "Bobo mais sympa"
    },
    "croix rousse": {
        "description": "Plateau bobo. Pentes et entre-soi garanti.",
        "prix_m2": 30,
        "ambiance": 8,
        "transports": 7,
        "commerces": 8,
        "vie_nocturne": 7,
        "metro": "Croix-Rousse (C)",
        "verdict": "Bobo mais sympa"
    },
    "69004": {
        "description": "Lyon 4ème : Colline qui télétravaille.",
        "prix_m2": 30,
        "ambiance": 8,
        "transports": 7,
        "commerces": 8,
        "vie_nocturne": 7,
        "metro": "Croix-Rousse",
        "verdict": "Branché"
    },

    # --- LYON 5ème ---
    "vieux lyon": {
        "description": "Disneyland médiéval. Pavés + 4000 touristes.",
        "prix_m2": 28,
        "ambiance": 6,
        "transports": 8,
        "commerces": 7,
        "vie_nocturne": 6,
        "metro": "Vieux Lyon (D)",
        "verdict": "Joli mais touristique"
    },
    "69005": {
        "description": "Lyon 5ème : Pavés et histoire.",
        "prix_m2": 27,
        "ambiance": 6,
        "transports": 7,
        "commerces": 7,
        "vie_nocturne": 6,
        "metro": "Vieux Lyon",
        "verdict": "Historique"
    },

    # --- LYON 6ème ---
    "brotteaux": {
        "description": "Bunker des riches. Propre, large, calme, ennuyeux.",
        "prix_m2": 38,
        "ambiance": 5,
        "transports": 9,
        "commerces": 8,
        "vie_nocturne": 4,
        "metro": "Foch (A), Masséna (A)",
        "verdict": "Riche mais chiant"
    },
    "69006": {
        "description": "Lyon 6ème : Le plus riche.",
        "prix_m2": 38,
        "ambiance": 5,
        "transports": 9,
        "commerces": 8,
        "vie_nocturne": 4,
        "metro": "Foch",
        "verdict": "Bourgeois"
    },

    # --- LYON 7ème ---
    "gerland": {
        "description": "Stades, bureaux, vide le soir.",
        "prix_m2": 22,
        "ambiance": 3,
        "transports": 6,
        "commerces": 4,
        "vie_nocturne": 2,
        "metro": "Debourg (T1)",
        "verdict": "Pas cher mais ennuyeux"
    },
    "69007": {
        "description": "Lyon 7ème : Street-life + gentrification.",
        "prix_m2": 23,
        "ambiance": 6,
        "transports": 7,
        "commerces": 7,
        "vie_nocturne": 6,
        "metro": "Jean Macé (B, D)",
        "verdict": "Contrasté"
    },

    # --- LYON 8ème ---
    "monplaisir": {
        "description": "Village familial. 'Sympa' = rien à faire.",
        "prix_m2": 20,
        "ambiance": 5,
        "transports": 6,
        "commerces": 6,
        "vie_nocturne": 3,
        "metro": "Monplaisir Lumière (D)",
        "verdict": "Calme familial"
    },
    "69008": {
        "description": "Lyon 8ème : Calme absolu.",
        "prix_m2": 20,
        "ambiance": 5,
        "transports": 6,
        "commerces": 6,
        "vie_nocturne": 3,
        "metro": "Monplaisir",
        "verdict": "Périphérique"
    },

    # --- LYON 9ème ---
    "vaise": {
        "description": "Silicon Valley lyonnaise. Tech et immeubles neufs.",
        "prix_m2": 24,
        "ambiance": 5,
        "transports": 7,
        "commerces": 6,
        "vie_nocturne": 4,
        "metro": "Valmy (D), Gorge de Loup (D)",
        "verdict": "Tech mais loin"
    },
    "69009": {
        "description": "Lyon 9ème : Ouest lointain.",
        "prix_m2": 23,
        "ambiance": 5,
        "transports": 6,
        "commerces": 6,
        "vie_nocturne": 4,
        "metro": "Vaise",
        "verdict": "Éloigné"
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


# --- FONCTION : TROUVER LES INFOS DU QUARTIER ---
def get_quartier_info(ville_ou_code_postal):
    """Recherche les infos enrichies du quartier"""
    if not ville_ou_code_postal:
        return {
            "description": "Un quartier lambda de Lyon.",
            "prix_m2": 25,
            "ambiance": 5,
            "transports": 5,
            "commerces": 5,
            "vie_nocturne": 5,
            "metro": "N/A",
            "verdict": "Moyen"
        }
    
    search_key = str(ville_ou_code_postal).lower().replace('-', ' ').strip()
    
    if search_key in LYON_BIBLE:
        return LYON_BIBLE[search_key]
    
    for key, info in LYON_BIBLE.items():
        if search_key in key or key in search_key:
            return info
    
    return {
        "description": "Quartier sans données précises.",
        "prix_m2": 25,
        "ambiance": 5,
        "transports": 5,
        "commerces": 5,
        "vie_nocturne": 5,
        "metro": "N/A",
        "verdict": "Données limitées"
    }


# --- FONCTION : COMPARAISON AVEC SCORES ---
def compare_quartiers(quartier1, prix1, quartier2):
    """
    Compare 2 quartiers avec scores visuels.
    Retourne un texte formaté avec émojis.
    """
    info1 = get_quartier_info(quartier1)
    info2 = get_quartier_info(quartier2)
    
    # Calculer le prix du quartier 2 pour la même surface
    surface = prix1 / info1["prix_m2"] if info1["prix_m2"] > 0 else 45
    prix2 = info2["prix_m2"] * surface
    
    # Calcul économie
    economie = prix2 - prix1
    pourcentage = (abs(economie) / prix2 * 100) if prix2 > 0 else 0
    
    # Construction du texte de comparaison
    comparison = f"""
{quartier1.upper()} vs {quartier2.upper()} (T2, {surface:.0f}m²)

💰 Prix : {quartier1.title()} {prix1:.0f}€ vs {quartier2.title()} {prix2:.0f}€
   → {quartier1.title() if prix1 < prix2 else quartier2.title()} GAGNE (-{pourcentage:.0f}%)

🎉 Ambiance : {quartier1.title()} {info1['ambiance']}/10 vs {quartier2.title()} {info2['ambiance']}/10
   → {quartier1.title() if info1['ambiance'] > info2['ambiance'] else quartier2.title()} GAGNE

🚇 Transports : {quartier1.title()} {info1['transports']}/10 vs {quartier2.title()} {info2['transports']}/10
   → {'Match nul' if info1['transports'] == info2['transports'] else (quartier1.title() if info1['transports'] > info2['transports'] else quartier2.title()) + ' GAGNE'}

🛒 Commerces : {quartier1.title()} {info1['commerces']}/10 vs {quartier2.title()} {info2['commerces']}/10

🌙 Vie nocturne : {quartier1.title()} {info1['vie_nocturne']}/10 vs {quartier2.title()} {info2['vie_nocturne']}/10

💡 ÉCONOMIE ANNUELLE à {quartier1.title()} : {abs(economie) * 12:.0f}€/an

🏆 VERDICT : {info1['verdict']} vs {info2['verdict']}
"""
    return comparison.strip()


# --- FONCTION : CALCUL FINANCIER ---
def calcul_financier(prix_mensuel, surface):
    """Retourne un texte avec calculs sur 1 an, 5 ans, 10 ans"""
    prix_annuel = prix_mensuel * 12
    prix_5ans = prix_annuel * 5
    prix_10ans = prix_annuel * 10
    
    return f"""
💰 SIMULATION FINANCIÈRE ({surface:.0f}m²)

📅 1 mois : {prix_mensuel:.0f}€
📅 1 an : {prix_annuel:,.0f}€
📅 5 ans : {prix_5ans:,.0f}€
📅 10 ans : {prix_10ans:,.0f}€

💡 En 10 ans, tu payes {prix_10ans:,.0f}€ de loyer.
"""


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
    """Prédit le prix avec XGBoost"""
    if model is None:
        return None
    
    result = preprocess_for_ml(surface, latitude, longitude)
    if result[0] is None:
        return None
    
    X_prepared, neighbor_row = result
    
    try:
        prix_estime_brut = model.predict(X_prepared)[0]
        
        if prix_estime_brut > PRIX_MAX_LOCATION:
            print(f"⚠️ Prix aberrant : {prix_estime_brut:.0f}€")
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
                method = "Moyenne"
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
        # Extraire les quartiers mentionnés
        quartiers = []
        for key in LYON_BIBLE.keys():
            if key in msg_lower and not key.startswith('690'):
                quartiers.append(key)
        
        if len(quartiers) >= 2:
            return ('compare', quartiers[:2])
        elif len(quartiers) == 1:
            return ('compare_with_scan', quartiers[0])
        else:
            return ('compare_unknown', None)
    
    # Calcul financier
    if any(word in msg_lower for word in ['coût', 'cout', 'économ', 'épargn', 'annuel', 'calculer', 'simulation']):
        return ('calcul_financier', None)
    
    # Mauvaise foi détectée
    if any(word in msg_lower for word in ['pauvre', 'clochard', 'crade', 'ghetto', 'sans avenir']):
        return ('mauvaise_foi', None)
    
    # Question générale
    return ('general', None)


# --- FONCTION IA : MISTRAL PREMIUM ---
def ask_mistral_premium(user_message, prix_estime, prix_m2, surface, quartier):
    """Appelle Mistral avec prompt PREMIUM"""
    try:
        quartier_info = get_quartier_info(quartier)
        
        # Détection d'intention
        intent_type, intent_data = detect_intent(user_message)
        
        # --- INTENT : COMPARAISON ---
        if intent_type == 'compare' and intent_data and len(intent_data) >= 2:
            comparison = compare_quartiers(quartier, prix_estime, intent_data[1])
            
            prompt = f"""Tu es l'Oracle de Lyon, cynique et direct.

{comparison}

Commente cette comparaison en 2-3 phrases max, sans répéter les chiffres.
Utilise un ton cash avec de l'argot lyonnais (gone).

Réponse :"""

        # --- INTENT : COMPARAISON AVEC LE SCAN ---
        elif intent_type == 'compare_with_scan' and intent_data:
            comparison = compare_quartiers(quartier, prix_estime, intent_data)
            
            prompt = f"""Tu es l'Oracle de Lyon.

{comparison}

Commente en 2-3 phrases max, ton cash.

Réponse :"""

        # --- INTENT : CALCUL FINANCIER ---
        elif intent_type == 'calcul_financier':
            calculs = calcul_financier(prix_estime, surface)
            
            prompt = f"""Tu es l'Oracle de Lyon.

{calculs}

Commente ces chiffres en 2 phrases, ton cash.

Réponse :"""

        # --- INTENT : MAUVAISE FOI ---
        elif intent_type == 'mauvaise_foi':
            prompt = f"""Tu es l'Oracle de Lyon.

L'utilisateur a dit : "{user_message}"

Contexte : {quartier} coûte {prix_estime}€ ({prix_m2}€/m²)

RÈGLE : Il insulte un quartier populaire. Corrige-le fermement mais respectueusement.
Explique que "moins cher" ≠ "pour les pauvres".

Réponse (2-3 phrases max) :"""

        # --- INTENT : GÉNÉRAL ---
        else:
            prompt = f"""Tu es l'Oracle de Lyon, cynique et cash.

DONNÉES DU SCAN :
- Quartier : {quartier}
- Loyer : {prix_estime}€
- Prix/m² : {prix_m2}€/m²
- Surface : {surface}m²
- Ambiance : {quartier_info['description']}
- Métro : {quartier_info['metro']}

RÈGLES :
- MAX 2-3 PHRASES
- Argot lyonnais (gone)
- INTERDIT d'inventer des prix

QUESTION : {user_message}

RÉPONSE :"""

        payload = {
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 250
        }
        
        print(f"📤 Intent détecté : {intent_type}")
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            
            # Si c'est une comparaison, ajouter le tableau au début
            if intent_type in ['compare', 'compare_with_scan']:
                return comparison + "\n\n" + answer
            elif intent_type == 'calcul_financier':
                return calculs + "\n\n" + answer
            else:
                return answer
        else:
            print(f"❌ Erreur LM Studio {response.status_code}")
            return "⚠️ Erreur technique"
            
    except requests.exceptions.ConnectionError:
        return "🔴 L'Oracle est injoignable (LM Studio port 1234)"
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return "⚠️ Erreur interne"


# --- ROUTES API ---

@app.route('/')
def home():
    return jsonify({
        "status": "Oracle v7.0 PREMIUM", 
        "model_loaded": model is not None,
        "features": ["Scores", "Calculs financiers", "Vie pratique"],
        "bible_size": len(LYON_BIBLE)
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
                "analysis": f"📍 Voisin le plus proche",
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
    try:
        data = request.json
        user_msg = data.get('message', '').strip()
        context = data.get('context', None)
        
        if not user_msg:
            return jsonify({"response": "⚠️ Parle, gone."})
        
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
        
        response = ask_mistral_premium(user_msg, prix_estime, prix_m2, surface, quartier)
        
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"response": "⚠️ Erreur interne"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)