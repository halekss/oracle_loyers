from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import joblib
import os
import numpy as np
from scipy.spatial import distance

# --- CONFIGURATION ---
app = Flask(__name__)
CORS(app) 

# Chemins
base_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(base_dir, 'data', 'master_immo_final.csv')
model_path = os.path.join(base_dir, 'models', 'price_predictor.pkl')

print("⏳ Chargement du Cerveau...")

# 1. Chargement des données
try:
    df = pd.read_csv(data_path)
    df = df.where(pd.notnull(df), None)
    # On garde les coordonnées en mémoire pour la recherche rapide
    # On s'assure que c'est bien des nombres (float)
    locations = df[['latitude', 'longitude']].astype(float).values
    print(f"✅ Données chargées : {len(df)} annonces.")
except Exception as e:
    print(f"❌ Erreur CSV : {e}")
    df = pd.DataFrame()
    locations = []

# 2. Chargement du Modèle
try:
    model = joblib.load(model_path)
    print("✅ Modèle IA chargé.")
except Exception as e:
    print(f"❌ Erreur Modèle : {e}")
    model = None

# --- FONCTION D'ANALYSE (Le "Bavard") ---
def generate_analysis_text(appart_data):
    """
    Regarde les distances et génère un texte sympa pour l'utilisateur.
    Basé sur ta logique 'Locataire' (Vice = Cher, Nuisance = Pas cher).
    """
    messages = []
    
    # 1. Les Nuisances (Bons plans pour le portefeuille)
    if appart_data['dist_nuisance_école'] < 200:
        messages.append(f"📉 **Bon plan économie** : Une école est à {int(appart_data['dist_nuisance_école'])}m. C'est bruyant, donc le loyer est moins cher !")
    
    if appart_data['dist_nuisance_station_service'] < 300:
        messages.append(f"⛽ **Rabais odeur** : Station-service à {int(appart_data['dist_nuisance_station_service'])}m. Pas glamour, mais ça fait baisser le prix.")
        
    if appart_data['dist_superstition_cimetière'] < 300:
        messages.append(f"👻 **Voisins calmes** : Cimetière à {int(appart_data['dist_superstition_cimetière'])}m. Les superstitions font chuter le prix !")

    # 2. Les Atouts (Surcoûts)
    if appart_data['dist_vice_bar'] < 100:
        messages.append(f"🍻 **Taxe ambiance** : Bars à {int(appart_data['dist_vice_bar'])}m. Le quartier est vivant, et ça se paie !")
        
    if appart_data['dist_vice_sex-shop'] < 200:
        messages.append(f"🔞 **Hyper-centre** : La présence d'un Sex-shop à {int(appart_data['dist_vice_sex-shop'])}m indique un quartier central et cher.")

    if not messages:
        messages.append("📍 Quartier standard, ni trop bruyant, ni trop fêtard.")

    return messages

# --- ROUTES ---

@app.route('/api/listings', methods=['GET'])
def get_listings():
    if df.empty: return jsonify({"error": "No data"}), 500
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/predict', methods=['POST'])
def predict_smart():
    """
    Reçoit { "latitude": 45.76, "longitude": 4.85, "surface": 30 }
    Renvoie le prix ET l'analyse du quartier.
    """
    if not model: return jsonify({"error": "Modèle HS"}), 500

    try:
        data = request.json
        user_lat = data.get('latitude')
        user_lon = data.get('longitude')
        surface = data.get('surface', 30) # 30m2 par défaut si oublié

        if user_lat is None or user_lon is None:
            return jsonify({"error": "Il faut une latitude et longitude !"}), 400

        # --- ÉTAPE 1 : TROUVER LE VOISIN LE PLUS PROCHE ---
        # On compare le point utilisateur avec tous nos apparts
        user_point = np.array([[user_lat, user_lon]])
        # Calcul des distances (Euclidienne simple)
        distances = distance.cdist(user_point, locations, 'euclidean')
        # L'index du plus proche
        closest_idx = distances.argmin()
        
        # On récupère les infos de ce voisin (c'est notre "référence")
        neighbor = df.iloc[closest_idx].to_dict()
        dist_to_neighbor = distances[0][closest_idx] * 111000 # Degrés vers Mètres (approx)

        print(f"📍 Point demandé : {user_lat}, {user_lon}")
        print(f"🏠 Voisin trouvé : ID {neighbor['id_annonce']} à {int(dist_to_neighbor)}m")

        # --- ÉTAPE 2 : PRÉPARER LES DONNÉES POUR L'IA ---
        # On prend les distances du voisin, mais on garde la surface demandée par l'user
        input_data = neighbor.copy()
        input_data['surface'] = surface 
        input_data['latitude'] = user_lat # On garde la vraie pos
        input_data['longitude'] = user_lon
        
        # Nettoyage pour le modèle (garder que les bonnes colonnes)
        expected_cols = model.feature_names_in_
        model_input = pd.DataFrame(0, index=[0], columns=expected_cols)
        
        for col in expected_cols:
            if col in input_data:
                model_input[col] = input_data[col]

        # --- ÉTAPE 3 : PRÉDIRE ET ANALYSER ---
        prediction = model.predict(model_input)[0]
        analysis_text = generate_analysis_text(neighbor)

        return jsonify({
            "estimated_price": round(prediction, 0),
            "price_m2": round(prediction / surface, 1),
            "currency": "€",
            "analysis": analysis_text, # <--- C'est ça que le React va afficher !
            "info_debug": f"Basé sur un immeuble voisin situé à {int(dist_to_neighbor)}m"
        })

    except Exception as e:
        print(f"❌ Erreur : {e}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)