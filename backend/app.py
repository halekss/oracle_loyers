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

print("🔥 ORACLE v8.0 ULTRA PREMIUM - 4 Cavaliers du Vice Intégrés")

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')
CSV_PATH = os.path.join(DATA_DIR, 'master_immo_final.csv')
CAVALIERS_PATH = os.path.join(DATA_DIR, 'cavaliers_lyon.csv')

LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', "http://host.docker.internal:1234/v1/chat/completions")
print(f"🔗 LM Studio URL : {LM_STUDIO_URL}")

os.makedirs(STATIC_DIR, exist_ok=True)

# ============================================================================
# 🐴 CHARGEMENT DES 4 CAVALIERS
# ============================================================================
cavaliers_df = None
try:
    if os.path.exists(CAVALIERS_PATH):
        cavaliers_df = pd.read_csv(CAVALIERS_PATH, encoding='utf-8-sig')
        print(f"✅ Cavaliers chargés : {len(cavaliers_df)} lieux")
    else:
        print(f"⚠️ Fichier cavaliers introuvable : {CAVALIERS_PATH}")
except Exception as e:
    print(f"⚠️ Erreur chargement cavaliers : {e}")


# --- FONCTION : CALCULER LES SCORES DES CAVALIERS POUR UN QUARTIER ---
def calculate_cavaliers_scores(lat, lon, radius_km=1.0):
    """
    Calcule les scores des 4 cavaliers autour d'un point.
    Retourne un dict avec les scores /10.
    """
    if cavaliers_df is None or cavaliers_df.empty:
        return {
            "vice": 5,
            "gentrification": 5,
            "nuisance": 5,
            "superstition": 5,
            "details": {}
        }
    
    try:
        # Filtrer les lieux dans le rayon
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Distance en km entre 2 points GPS"""
            from math import radians, sin, cos, sqrt, atan2
            
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            
            return 6371 * c  # Rayon de la Terre en km
        
        # Calculer les distances
        cavaliers_df['distance'] = cavaliers_df.apply(
            lambda row: haversine_distance(lat, lon, row['latitude'], row['longitude']),
            axis=1
        )
        
        # Filtrer par rayon
        nearby = cavaliers_df[cavaliers_df['distance'] <= radius_km]
        
        # Compter par catégorie
        vice_count = len(nearby[nearby['categorie_cavalier'].str.contains('Vice', na=False)])
        gentrif_count = len(nearby[nearby['categorie_cavalier'].str.contains('Gentrification', na=False)])
        nuisance_count = len(nearby[nearby['categorie_cavalier'].str.contains('Nuisance', na=False)])
        superst_count = len(nearby[nearby['categorie_cavalier'].str.contains('Superstition', na=False)])
        
        # Détails par type
        details = {}
        
        # Vice détails
        bars = len(nearby[nearby['categorie_cavalier'] == 'Vice - Bar'])
        kebabs = len(nearby[nearby['categorie_cavalier'] == 'Vice - Kebab'])
        sexshops = len(nearby[nearby['categorie_cavalier'] == 'Vice - Sex-shop'])
        tabacs = len(nearby[nearby['categorie_cavalier'] == 'Vice - Tabac'])
        cbd = len(nearby[nearby['categorie_cavalier'] == 'Vice - CBD Shop'])
        
        details['vice'] = {
            'bars': bars,
            'kebabs': kebabs,
            'sexshops': sexshops,
            'tabacs': tabacs,
            'cbd': cbd
        }
        
        # Gentrification détails
        yoga = len(nearby[nearby['categorie_cavalier'] == 'Gentrification - Yoga'])
        torrefi = len(nearby[nearby['categorie_cavalier'] == 'Gentrification - Torréfacteur'])
        velo = len(nearby[nearby['categorie_cavalier'] == 'Gentrification - Atelier Vélo'])
        epicerie = len(nearby[nearby['categorie_cavalier'] == 'Gentrification - Épicerie Fine'])
        
        details['gentrification'] = {
            'yoga': yoga,
            'torrefacteur': torrefi,
            'atelier_velo': velo,
            'epicerie_fine': epicerie
        }
        
        # Nuisance détails
        ecoles = len(nearby[nearby['categorie_cavalier'] == 'Nuisance - École'])
        aires_jeux = len(nearby[nearby['categorie_cavalier'] == 'Nuisance - Aire de jeux'])
        discos = len(nearby[nearby['categorie_cavalier'] == 'Nuisance - Discothèque'])
        
        details['nuisance'] = {
            'ecoles': ecoles,
            'aires_jeux': aires_jeux,
            'discotheques': discos
        }
        
        # Superstition détails
        cimetieres = len(nearby[nearby['categorie_cavalier'] == 'Superstition - Cimetière'])
        pompes = len(nearby[nearby['categorie_cavalier'] == 'Superstition - Pompes Funèbres'])
        
        details['superstition'] = {
            'cimetieres': cimetieres,
            'pompes_funebres': pompes
        }
        
        # Calcul des scores /10 (normalisés)
        # Vice : 0-5 lieux = score faible, 50+ = score max
        vice_score = min(10, (vice_count / 5))
        
        # Gentrification : 0-3 lieux = faible, 30+ = max
        gentrif_score = min(10, (gentrif_count / 3))
        
        # Nuisance : 0-10 lieux = faible, 100+ = max
        nuisance_score = min(10, (nuisance_count / 10))
        
        # Superstition : 0-1 lieu = faible, 5+ = max
        superst_score = min(10, (superst_count / 0.5))
        
        return {
            "vice": round(vice_score, 1),
            "gentrification": round(gentrif_score, 1),
            "nuisance": round(nuisance_score, 1),
            "superstition": round(superst_score, 1),
            "details": details
        }
        
    except Exception as e:
        print(f"❌ Erreur calcul cavaliers : {e}")
        return {
            "vice": 5,
            "gentrification": 5,
            "nuisance": 5,
            "superstition": 5,
            "details": {}
        }


# --- FONCTION : FORMATER LES CAVALIERS POUR LE PROMPT ---
def format_cavaliers_for_prompt(scores):
    """Formate les scores des cavaliers pour le LLM"""
    details = scores.get('details', {})
    vice_det = details.get('vice', {})
    gentrif_det = details.get('gentrification', {})
    nuisance_det = details.get('nuisance', {})
    
    text = f"""
🔥 SCORE VICE : {scores['vice']}/10
   └─ {vice_det.get('bars', 0)} bars, {vice_det.get('kebabs', 0)} kebabs, {vice_det.get('sexshops', 0)} sex-shops

🌱 SCORE GENTRIFICATION : {scores['gentrification']}/10
   └─ {gentrif_det.get('yoga', 0)} salles yoga, {gentrif_det.get('torrefacteur', 0)} torréfacteurs, {gentrif_det.get('epicerie_fine', 0)} épiceries fines

⚠️ SCORE NUISANCE : {scores['nuisance']}/10
   └─ {nuisance_det.get('ecoles', 0)} écoles, {nuisance_det.get('aires_jeux', 0)} aires de jeux

👻 SCORE SUPERSTITION : {scores['superstition']}/10
"""
    return text.strip()


# ============================================================================
# 🔮 BIBLE DES QUARTIERS (inchangée)
# ============================================================================
LYON_BIBLE = {
    # ... (garder la Bible existante, je la réimporte)
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
    # ... (autres quartiers)
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
    """Recherche les infos du quartier dans la Bible"""
    search_key = str(ville_ou_code_postal).lower().replace('-', ' ').strip()
    
    if search_key in LYON_BIBLE:
        return LYON_BIBLE[search_key]
    
    for key, info in LYON_BIBLE.items():
        if search_key in key or key in search_key:
            return info
    
    return {
        "description": "Quartier sans données.",
        "prix_m2": 25,
        "ambiance": 5,
        "transports": 5,
        "commerces": 5,
        "vie_nocturne": 5,
        "metro": "N/A",
        "verdict": "Données limitées"
    }


# --- FONCTION : COMPARAISON AVEC CAVALIERS ---
# --- AVANT (Ce que vous avez) ---
# (Le code actuel génère du texte plat avec juste des emojis)

# --- APRÈS (À copier) ---
def compare_quartiers_full(quartier1, prix1, lat1, lon1, quartier2):
    """
    Compare 2 quartiers AVEC les scores des cavaliers.
    """
    info1 = get_quartier_info(quartier1)
    info2 = get_quartier_info(quartier2)
    
    # Calculer scores cavaliers (Simplifié pour l'exemple)
    cavaliers1 = calculate_cavaliers_scores(lat1, lon1)
    cavaliers2 = {"vice": 5, "gentrification": 5, "nuisance": 5, "superstition": 5}
    
    surface = prix1 / info1["prix_m2"] if info1["prix_m2"] > 0 else 45
    prix2 = info2["prix_m2"] * surface
    
    economie = prix2 - prix1
    pourcentage = (abs(economie) / prix2 * 100) if prix2 > 0 else 0
    gagnant = quartier1.title() if prix1 < prix2 else quartier2.title()
    
    # Utilisation de Markdown (**gras**) pour l'UI
    comparison = f"""
### ⚔️ DUEL : {quartier1.upper()} vs {quartier2.upper()}
*(Base T2 standard de {surface:.0f}m²)*

💰 **PRIX DU LOYER**
* **{quartier1.title()}** : {prix1:.0f}€
* **{quartier2.title()}** : {prix2:.0f}€
👉 **{gagnant} l'emporte** (différence de {pourcentage:.0f}%)

📊 **SCORES "ORACLE"**
* 🎉 **Ambiance** : {quartier1.title()} **{info1['ambiance']}/10** vs {quartier2.title()} **{info2['ambiance']}/10**
* 🚇 **Transports** : {quartier1.title()} **{info1['transports']}/10** vs {quartier2.title()} **{info2['transports']}/10**
* 🔥 **Vice** : {quartier1.title()} **{cavaliers1['vice']}/10** vs {quartier2.title()} **{cavaliers2['vice']}/10**

💡 **IMPACT PORTEMONNAIE**
En choisissant **{quartier1.title()}**, tu économises **{abs(economie) * 12:,.0f}€ par an**.

🏆 **VERDICT**
{info1['verdict']} vs {info2['verdict']}
"""
    return comparison.strip()

# --- FONCTION : CALCUL FINANCIER ---
def calcul_financier(prix_mensuel, surface):
    """Calculs financiers sur différentes durées"""
    prix_annuel = prix_mensuel * 12
    prix_5ans = prix_annuel * 5
    prix_10ans = prix_annuel * 10
    
    return f"""
### 💰 SIMULATION FINANCIÈRE
*(Pour une surface de {surface:.0f}m²)*

* 📅 **1 mois** : {prix_mensuel:.0f} €
* 📅 **1 an** : **{prix_annuel:,.0f} €**
* 📅 **5 ans** : {prix_5ans:,.0f} €

🛑 **LA DOULOUREUSE**
En 10 ans, tu auras versé **{prix_10ans:,.0f} €** à ton propriétaire.
*T'es sûr de ne pas vouloir acheter ?*
"""

# --- FONCTION ML : PREPROCESSING ---
def preprocess_for_ml(surface, latitude, longitude):
    """Prépare les features pour le ML"""
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
    """Prédiction ML"""
    if model is None:
        return None
    
    result = preprocess_for_ml(surface, latitude, longitude)
    if result[0] is None:
        return None
    
    X_prepared, neighbor_row = result
    
    try:
        prix_estime_brut = model.predict(X_prepared)[0]
        
        if prix_estime_brut > PRIX_MAX_LOCATION:
            prix_voisin = neighbor_row.get('prix', None)
            prix_m2_voisin = neighbor_row.get('prix_m2', None)
            
            if prix_voisin and not pd.isna(prix_voisin):
                if prix_m2_voisin and not pd.isna(prix_m2_voisin):
                    prix_estime = prix_m2_voisin * surface
                else:
                    ratio = surface / neighbor_row.get('surface', surface)
                    prix_estime = prix_voisin * ratio
                method = "Voisin"
            else:
                prix_estime = 15 * surface
                method = "Moyenne"
        else:
            prix_estime = prix_estime_brut
            method = "ML"
        
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
        print(f"❌ Erreur ML : {e}")
        return None


# --- FONCTION : DÉTECTION D'INTENTION ---
def detect_intent(message):
    """Détecte l'intention dans le message"""
    msg_lower = message.lower()
    
    # Comparaison
    if any(word in msg_lower for word in ['compar', 'vs', 'différence']):
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
    if any(word in msg_lower for word in ['coût', 'cout', 'économ', 'annuel', 'simulation']):
        return ('calcul_financier', None)
    
    # Mauvaise foi
    if any(word in msg_lower for word in ['pauvre', 'clochard', 'crade', 'ghetto']):
        return ('mauvaise_foi', None)
    
    return ('general', None)


# --- FONCTION IA : MISTRAL ULTRA PREMIUM ---
def ask_mistral_ultra(user_message, prix_estime, prix_m2, surface, quartier, lat, lon):
    """Mistral avec cavaliers intégrés"""
    try:
        quartier_info = get_quartier_info(quartier)
        cavaliers_scores = calculate_cavaliers_scores(lat, lon)
        cavaliers_text = format_cavaliers_for_prompt(cavaliers_scores)
        
        intent_type, intent_data = detect_intent(user_message)
        
        # --- COMPARAISON ---
        if intent_type == 'compare' and intent_data and len(intent_data) >= 2:
            comparison = compare_quartiers_full(quartier, prix_estime, lat, lon, intent_data[1])
            
            prompt = f"""Tu es l'Oracle de Lyon, cynique et direct.

{comparison}

Commente cette comparaison en 2-3 phrases max. Ton cash, argot lyonnais (gone).

Réponse :"""

        # --- COMPARAISON AVEC SCAN ---
        elif intent_type == 'compare_with_scan' and intent_data:
            comparison = compare_quartiers_full(quartier, prix_estime, lat, lon, intent_data)
            
            prompt = f"""Tu es l'Oracle de Lyon.

{comparison}

Commente en 2-3 phrases, ton cash.

Réponse :"""

        # --- CALCUL FINANCIER ---
        elif intent_type == 'calcul_financier':
            calculs = calcul_financier(prix_estime, surface)
            
            prompt = f"""Tu es l'Oracle de Lyon.

{calculs}

Commente en 2 phrases.

Réponse :"""

        # --- MAUVAISE FOI ---
        elif intent_type == 'mauvaise_foi':
            prompt = f"""Tu es l'Oracle de Lyon.

L'utilisateur dit : "{user_message}"

Contexte : {quartier} = {prix_estime}€ ({prix_m2}€/m²)

{cavaliers_text}

Corrige-le fermement : "moins cher" ≠ "pour les pauvres".

Réponse (2-3 phrases) :"""

        # --- GÉNÉRAL ---
        else:
            prompt = f"""Tu es l'Oracle de Lyon, expert immobilier cynique.

CONTEXTE DU SCAN :
- Quartier : {quartier}
- Loyer Estimé : {prix_estime}€
- Surface : {surface}m²
- Ambiance Bible : {quartier_info['description']}

{cavaliers_text}

INSTRUCTIONS DE STYLE (A RESPECTER STRICTEMENT) :
1. Utilise du **Markdown** pour mettre en forme.
2. Mets les prix et le nom du quartier en **gras**.
3. Fais des paragraphes courts. Saute des lignes.
4. Utilise des listes à puces (- point) si tu cites plusieurs arguments.
5. Sois drôle, argotique (gone), mais lisible.

QUESTION UTILISATEUR : {user_message}

RÉPONSE :"""

        payload = {
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 250
        }
        
        print(f"📤 Intent : {intent_type} | Cavaliers Vice={cavaliers_scores['vice']}/10")
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content']
            
            # Ajouter les tableaux si comparaison
            if intent_type in ['compare', 'compare_with_scan']:
                return comparison + "\n\n" + answer
            elif intent_type == 'calcul_financier':
                return calculs + "\n\n" + answer
            else:
                return answer
        else:
            return "⚠️ Erreur technique"
            
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return "⚠️ Erreur interne"


# --- ROUTES API ---

@app.route('/')
def home():
    return jsonify({
        "status": "Oracle v8.0 ULTRA PREMIUM", 
        "features": ["Scores", "Calculs", "Vie pratique", "4 Cavaliers"],
        "cavaliers_loaded": cavaliers_df is not None
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
        
        # Calculer les cavaliers
        cavaliers = calculate_cavaliers_scores(lat, lon)
        
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
                "cavaliers": cavaliers,  # ← NOUVEAU
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
                "analysis": "📍 Voisin",
                "stats": {
                    "prix_m2": round(prix_m2),
                    "method": "Nearest Neighbor",
                    "surface": surface
                },
                "details": {
                    "ville": neighbor.get('ville', 'Lyon')
                },
                "cavaliers": cavaliers,
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
            return jsonify({"response": "Fais un SCAN d'abord."})
        
        # Parser le contexte
        prix_estime = 0
        prix_m2 = 0
        surface = 0
        quartier = "Lyon"
        lat = 45.75  # Valeurs par défaut
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
            
            if 'ville' in line.lower():
                parts = line.split(':')
                if len(parts) > 1:
                    quartier = parts[1].strip()
            
            if 'position' in line.lower():
                match = re.search(r'([\d.]+),\s*([\d.]+)', line)
                if match:
                    lat = float(match.group(1))
                    lon = float(match.group(2))
        
        response = ask_mistral_ultra(user_msg, prix_estime, prix_m2, surface, quartier, lat, lon)
        
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"response": "⚠️ Erreur interne"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)