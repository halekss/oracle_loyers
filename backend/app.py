import os
import requests
import joblib
import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from scipy.spatial import distance
import re

# --- SERVICES ---
from services.data_loader import DataLoader
from services.map_generator import MapGenerator

print("🔥 DÉMARRAGE ORACLE CHATBOT v7.0 (RAG MANUEL OPTIMISÉ)")

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
FEATURES_PATH = os.path.join(MODELS_DIR, 'model_features.pkl')

# URL LM Studio
LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', "http://localhost:1234/v1/chat/completions")
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
        model_features = joblib.load(FEATURES_PATH)
        print(f"✅ Modèle ML chargé (attend {len(model_features)} critères)")
    else:
        print("⚠️ FICHIERS ML MANQUANTS : Le modèle ou la liste des features est absente.")
        print("👉 Lancez 'python scripts/train_model.py' pour les générer.")
except Exception as e:
    print(f"❌ Erreur chargement ML : {e}")

# ============================================================================
# 🧠 SYSTÈME RAG MANUEL (BASE DE CONNAISSANCES)
# ============================================================================

class ManualRAG:
    """
    Système RAG manuel qui charge les annonces en mémoire
    et les recherche selon les critères de l'utilisateur
    """
    
    def __init__(self, csv_df):
        self.df = csv_df
        print(f"📚 RAG Manuel initialisé avec {len(self.df)} annonces")
    
    def search_by_criteria(self, user_query):
        """
        Recherche intelligente dans le CSV selon la question
        Retourne les annonces pertinentes
        """
        query_lower = user_query.lower()
        
        # Extraction des critères de la question
        criteria = {
            'prix_max': None,
            'prix_min': None,
            'surface_min': None,
            'surface_max': None,
            'quartier': None,
            'ville': None,
            'code_postal': None
        }
        
        # 1. PRIX
        prix_match = re.search(r'(\d+)\s*(?:€|euros?|balles?)', query_lower)
        if prix_match:
            prix = int(prix_match.group(1))
            if 'moins' in query_lower or '<' in query_lower or 'max' in query_lower:
                criteria['prix_max'] = prix
            elif 'plus' in query_lower or '>' in query_lower or 'min' in query_lower:
                criteria['prix_min'] = prix
            else:
                # Par défaut, on considère que c'est un prix max
                criteria['prix_max'] = prix
        
        # 2. SURFACE
        surface_match = re.search(r'(\d+)\s*m[²2]', query_lower)
        if surface_match:
            surface = int(surface_match.group(1))
            if 'moins' in query_lower or '<' in query_lower:
                criteria['surface_max'] = surface
            elif 'plus' in query_lower or '>' in query_lower:
                criteria['surface_min'] = surface
        
        # 3. LOCALISATION
        # Quartiers de Lyon
        quartiers = ['guillotière', 'croix-rousse', 'ainay', 'confluence', 
                     'part-dieu', 'bellecour', 'vieux lyon', 'fourvière',
                     'gerland', 'monplaisir', 'saxe', 'garibaldi']
        
        for quartier in quartiers:
            if quartier in query_lower:
                criteria['quartier'] = quartier
                break
        
        # Codes postaux Lyon
        cp_match = re.search(r'69(\d{3})', query_lower)
        if cp_match:
            criteria['code_postal'] = f"69{cp_match.group(1)}"
        
        # Arrondissements
        arr_match = re.search(r'lyon\s*(\d+)', query_lower)
        if arr_match:
            arr = arr_match.group(1)
            criteria['code_postal'] = f"6900{arr}"
        
        # 4. FILTRAGE
        filtered_df = self.df.copy()
        
        if criteria['prix_max']:
            filtered_df = filtered_df[filtered_df['prix'] <= criteria['prix_max']]
        
        if criteria['prix_min']:
            filtered_df = filtered_df[filtered_df['prix'] >= criteria['prix_min']]
        
        if criteria['surface_min']:
            filtered_df = filtered_df[filtered_df['surface'] >= criteria['surface_min']]
        
        if criteria['surface_max']:
            filtered_df = filtered_df[filtered_df['surface'] <= criteria['surface_max']]
        
        if criteria['code_postal']:
            filtered_df = filtered_df[filtered_df['code_postal'].astype(str).str.startswith(criteria['code_postal'][:5])]
        
        if criteria['quartier']:
            filtered_df = filtered_df[
                filtered_df['quartier'].astype(str).str.lower().str.contains(criteria['quartier'], na=False)
            ]
        
        # Limiter à 5 résultats max pour ne pas surcharger le contexte
        return filtered_df.head(5), criteria
    
    def format_annonces_for_context(self, annonces_df):
        """
        Formate les annonces en texte compact pour le contexte LLM
        """
        if annonces_df.empty:
            return "Aucune annonce correspondante trouvée."
        
        context = f"📊 {len(annonces_df)} annonce(s) trouvée(s) :\n\n"
        
        for idx, row in annonces_df.iterrows():
            context += f"""
Annonce #{row.get('id_annonce', idx)} :
- Lieu : {row.get('quartier', 'N/A')}, {row.get('ville', 'Lyon')} ({row.get('code_postal', 'N/A')})
- Type : {row.get('type', 'Appartement')}
- Surface : {row.get('surface', 'N/A')} m²
- Prix : {row.get('prix', 'N/A')} €/mois ({row.get('prix_m2', 'N/A')} €/m²)
- Nuisances : {row.get('nb_nuisance_discothèque_500m', 0)} discothèque(s) à proximité
- Description : {str(row.get('description', ''))[:100]}...

"""
        
        return context
    
    def get_stats(self, quartier=None, code_postal=None):
        """
        Calcule des statistiques sur un quartier
        """
        filtered = self.df.copy()
        
        if quartier:
            filtered = filtered[
                filtered['quartier'].astype(str).str.lower().str.contains(quartier.lower(), na=False)
            ]
        
        if code_postal:
            filtered = filtered[filtered['code_postal'].astype(str) == str(code_postal)]
        
        if filtered.empty:
            return "Pas de données pour ce quartier."
        
        return f"""
📊 STATISTIQUES :
- Nombre d'annonces : {len(filtered)}
- Prix moyen : {filtered['prix'].mean():.0f} €/mois
- Prix au m² moyen : {filtered['prix_m2'].mean():.2f} €/m²
- Surface moyenne : {filtered['surface'].mean():.1f} m²
- Prix min : {filtered['prix'].min():.0f} € | Prix max : {filtered['prix'].max():.0f} €
"""

# Initialiser le RAG manuel
rag = ManualRAG(df)

# ============================================================================
# 🧠 FONCTIONS INTELLIGENTES
# ============================================================================

def ask_mistral_with_context(system_prompt, user_message, context=""):
    """
    Interroge LM Studio avec contexte enrichi
    """
    try:
        # Construction du message avec contexte
        full_message = user_message
        if context:
            full_message = f"""CONTEXTE (Données réelles) :
{context}

QUESTION DE L'UTILISATEUR :
{user_message}

Réponds en te basant UNIQUEMENT sur les données ci-dessus. Si l'info n'est pas dans le contexte, dis-le clairement."""
        
        payload = {
            "model": "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_message}
            ],
            "temperature": 0.7,
            "max_tokens": 800,
            "top_p": 0.9,
            "stream": False
        }
        
        print(f"📤 Envoi à LM Studio (avec contexte: {len(context)} chars)")
        r = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        if r.status_code == 200:
            response = r.json()['choices'][0]['message']['content']
            print(f"📥 Réponse reçue ({len(response)} caractères)")
            return response
        else:
            error_text = r.text[:200] if r.text else "Pas de détails"
            print(f"❌ Erreur HTTP {r.status_code}: {error_text}")
            return f"⚠️ Erreur Oracle (Code {r.status_code})"
            
    except requests.exceptions.Timeout:
        return "⏱️ L'Oracle prend trop de temps... Réessaye."
        
    except requests.exceptions.ConnectionError:
        return "🔴 **L'Oracle est injoignable**\n\nVérifie que LM Studio est lancé sur http://localhost:1234"
        
    except Exception as e:
        print(f"❌ Exception : {e}")
        return f"🔴 Erreur : {str(e)}"

def prepare_data_for_ml(neighbor, surface, features_list):
    """Transforme les données pour XGBoost"""
    input_df = pd.DataFrame([neighbor])
    input_df['surface'] = surface
    
    for col in features_list:
        if 'type' in col:
            input_df[col] = 0
            
    if surface < 30:
        if 'type_local_Studio/T1' in features_list: input_df['type_local_Studio/T1'] = 1
        if 'type_Studio' in features_list: input_df['type_Studio'] = 1
    elif surface < 50:
        if 'type_local_T2' in features_list: input_df['type_local_T2'] = 1
    elif surface < 75:
        if 'type_local_T3' in features_list: input_df['type_local_T3'] = 1
    else:
        if 'type_local_Grand (T4+)' in features_list: input_df['type_local_Grand (T4+)'] = 1
        if 'type_Maison' in features_list: input_df['type_Maison'] = 0

    final_df = input_df.reindex(columns=features_list, fill_value=0)
    return final_df

# ============================================================================
# 🌐 ROUTES API
# ============================================================================

@app.route('/')
def home():
    return jsonify({
        "status": "Oracle v7.0 Alive (RAG Manuel)", 
        "ml_ready": model is not None,
        "nb_annonces": len(df),
        "lm_studio_url": LM_STUDIO_URL
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
        
        locations = df[['latitude', 'longitude']].astype(float).values
        user_point = np.array([[lat, lon]])
        distances = distance.cdist(user_point, locations, 'euclidean')
        closest_idx = distances.argmin()
        neighbor = df.iloc[closest_idx].to_dict()
        
        price_estimated = 0
        method = "Inconnue"
        
        if model and model_features:
            input_df = prepare_data_for_ml(neighbor, surface, model_features)
            price_estimated = float(model.predict(input_df)[0])
            method = "IA (XGBoost)"
            
            if price_estimated < 200 or price_estimated > 10000:
                print(f"⚠️ Aberration ML ({price_estimated}€) -> Fallback Voisin")
                base_m2 = float(neighbor.get('prix_m2', 20))
                price_estimated = base_m2 * surface
                method = "Voisin (Secours)"
        else:
            base_m2 = float(neighbor.get('prix_m2', 20))
            price_estimated = base_m2 * surface
            method = "Voisin (Pas de modèle)"

        final_prix_m2 = price_estimated / surface if surface > 0 else 0

        return jsonify({
            "estimated_price": round(price_estimated),
            "analysis": f"📍 Analyse {method} à {neighbor.get('ville', 'Lyon')}.",
            "stats": {
                "prix_m2": round(final_prix_m2),
                "surface": surface,
                "nb_biens_analyse": 1,
                "method": method
            },
            "details": {
                "latitude": lat, 
                "longitude": lon, 
                "ville": neighbor.get('ville', 'Lyon'),
                "quartier": neighbor.get('quartier', 'N/A')
            }
        })

    except Exception as e:
        print(f"❌ Erreur predict : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_oracle():
    """
    Route CHAT avec RAG manuel intelligent
    """
    try:
        data = request.json
        user_msg = data.get('message', '').strip()
        context_str = data.get('context', '')
        
        if not user_msg: 
            return jsonify({"response": "..."})
        
        # 🆕 RECHERCHE INTELLIGENTE dans le CSV
        relevant_annonces, criteria = rag.search_by_criteria(user_msg)
        
        # Détection du type de question
        query_lower = user_msg.lower()
        
        # Si c'est une question de stats
        if any(word in query_lower for word in ['prix moyen', 'moyenne', 'statistique', 'combien', 'coûte']):
            # Extraire le quartier/code postal
            quartier = criteria.get('quartier')
            cp = criteria.get('code_postal')
            
            stats_context = rag.get_stats(quartier=quartier, code_postal=cp)
            context_to_send = stats_context
        else:
            # Sinon, envoyer les annonces
            context_to_send = rag.format_annonces_for_context(relevant_annonces)
        
        # Ajouter le contexte du scan si présent
        if context_str:
            context_to_send += f"\n\n📍 SCAN EN COURS :\n{context_str}"
        
        # Prompt système optimisé
        system_prompt = f"""Tu es l'Oracle de Lyon, expert immobilier cynique et sarcastique.

🎯 TON STYLE :
- Sois direct, précis et factuel
- Un cynique sur les prix délirants de l'immobilier à Lyon et soit sarcastique
- Utilise des emojis avec parcimonie pour illustrer tes propos
- Maximum 5-6 lignes de réponse

⚠️ RÈGLES STRICTES :
1. Réponds UNIQUEMENT avec les données fournies dans le CONTEXTE
2. Cite TOUJOURS les ID d'annonces (#123, #456...)
3. Si l'info n'est pas dans le contexte → dis "J'ai pas cette info dans ma base"
4. JAMAIS inventer de chiffres ou d'annonces

💡 TU PEUX :
- Comparer des annonces
- Calculer des moyennes (si données fournies)
- Analyser les nuisances
- Conseiller selon les données réelles"""

        response = ask_mistral_with_context(system_prompt, user_msg, context_to_send)
        return jsonify({"response": response})
        
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        return jsonify({"response": "⚠️ Erreur interne. Réessaye."})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 ORACLE CHATBOT v7.0 - RAG MANUEL OPTIMISÉ")
    print("="*60)
    print(f"📡 Backend API : http://0.0.0.0:5000")
    print(f"🤖 LM Studio  : {LM_STUDIO_URL}")
    print(f"📚 Base RAG   : {len(df)} annonces en mémoire")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)