import os
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from services.data_loader import DataLoader
from services.chat_service import ChatService
import joblib

# Initialisation de l'application
app = Flask(__name__)
CORS(app)  # Autorise les requêtes du Frontend React

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'master_immo_final.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')

# Chargement des services
print("Chargement des données...")
data_loader = DataLoader(DATA_PATH)

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
        data = request.json
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

        return jsonify({
            "found": True,
            "quartier_detecte": nom_officiel,
            "type_filtre": type_filter,
            "count": int(count),
            "prix_moyen": round(float(mean_price), 0),
            "prix_m2_moyen": round(float(mean_price_m2), 0)
        })

    except Exception as e:
        print(f"Erreur Stats Quartier: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    """Prédiction via Machine Learning (XGBoost) - Placeholder fonctionnel"""
    try:
        # Ici on utilise un mock pour l'instant car ton utils.py dépend de ça
        return jsonify({
            "estimated_price": 0, 
            "price_m2": 0, 
            "confiance": "Non disponible"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Route pour le Chatbot Immotep"""
    try:
        data = request.json
        # On récupère le message utilisateur et le contexte envoyé par le front
        user_msg = data.get('message', '')
        context = data.get('context', '') 

        if not user_msg:
            return jsonify({"response": "Silence... Tu n'as rien à dire ?"}), 400

        # On récupère le DataFrame complet
        df = data_loader.get_data()

        # On appelle le service dédié qui gère le prompt et Llama
        reponse_immotep = chat_service.get_response(user_msg, context, df)

        return jsonify({"response": reponse_immotep})

    except Exception as e:
        print(f"Erreur Chat: {e}")
        return jsonify({"response": "J'ai eu un bug interne. C'est sûrement ta faute."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)