from flask import Flask, jsonify, request, send_from_directory
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
    # Important : On garde une copie propre pour pouvoir filtrer plus tard
    df['type_local'] = df['type_local'].fillna('').astype(str) # Sécurise la colonne type
    print(f"✅ Données chargées : {len(df)} annonces.")
except Exception as e:
    print(f"❌ Erreur CSV : {e}")
    df = pd.DataFrame()

# 2. Chargement du Modèle
try:
    model = joblib.load(model_path)
    print("✅ Modèle IA chargé.")
except Exception as e:
    print(f"❌ Erreur Modèle : {e}")
    model = None

def generate_analysis_text(appart_data):
    """Génère le texte cynique."""
    messages = []
    # Utilisation de .get() pour éviter les crashs si colonnes manquantes
    if appart_data.get('dist_nuisance_école', 1000) < 200:
        messages.append(f"📉 **Bon plan économie** : Une école est à {int(appart_data['dist_nuisance_école'])}m. C'est bruyant, donc le loyer est moins cher !")
    if appart_data.get('dist_vice_bar', 1000) < 100:
        messages.append(f"🍻 **Taxe ambiance** : Bars à {int(appart_data['dist_vice_bar'])}m. Le quartier est vivant, et ça se paie !")
    if not messages:
        messages.append("📍 Quartier standard, ni trop bruyant, ni trop fêtard.")
    return messages

# --- ROUTES ---

# NOUVELLE ROUTE : Pour servir la carte HTML qui est dans 'data'
@app.route('/maps/<path:filename>')  # <--- On change le nom ici
def serve_map(filename):
    static_folder = os.path.join(base_dir, 'data')
    return send_from_directory(static_folder, filename)

@app.route('/api/listings', methods=['GET'])
def get_listings():
    if df.empty: return jsonify({"error": "No data"}), 500
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/predict', methods=['POST'])
def predict_smart():
    if not model: return jsonify({"error": "Modèle HS"}), 500

    try:
        data = request.json
        user_lat = data.get('latitude')
        user_lon = data.get('longitude')
        surface = data.get('surface', 30)
        
        # --- NOUVEAU : Récupération du Filtre ---
        room_filter = data.get('room_filter', 'all') # 'all', 't1', 't2', ...

        if user_lat is None or user_lon is None:
            return jsonify({"error": "Il faut une latitude et longitude !"}), 400

        # --- ÉTAPE 1 : FILTRAGE INTELLIGENT ---
        # On crée un sous-ensemble de données qui correspond au filtre
        df_filtered = df.copy()

        # Mapping des filtres vers les noms dans le CSV
        if room_filter == 't1':
            df_filtered = df[df['type_local'].str.contains('T1|Studio', case=False, na=False)]
        elif room_filter == 't2':
            df_filtered = df[df['type_local'].str.contains('T2', case=False, na=False)]
        elif room_filter == 't3':
            df_filtered = df[df['type_local'].str.contains('T3', case=False, na=False)]
        elif room_filter == 't4+':
            df_filtered = df[df['type_local'].str.contains('T4|T5|Maison', case=False, na=False)]
        
        # Si le filtre est trop restrictif et qu'on a 0 résultat, on revient à 'all' pour éviter le crash
        if df_filtered.empty:
            df_filtered = df.copy() 
            info_debug_filter = "Filtre ignoré (pas assez de données)"
        else:
            info_debug_filter = f"Filtre actif : {room_filter} ({len(df_filtered)} biens)"

        # --- ÉTAPE 2 : TROUVER LE VOISIN LE PLUS PROCHE (DANS LE FILTRE) ---
        if 'latitude' not in df_filtered.columns or 'longitude' not in df_filtered.columns:
             return jsonify({"error": "Colonnes GPS manquantes"}), 500

        locations_filtered = df_filtered[['latitude', 'longitude']].astype(float).values
        user_point = np.array([[user_lat, user_lon]])
        
        distances = distance.cdist(user_point, locations_filtered, 'euclidean')
        closest_idx = distances.argmin()
        
        # On récupère le voisin dans le DF filtré
        neighbor = df_filtered.iloc[closest_idx].to_dict()
        
        # --- ÉTAPE 3 : CALCUL DE LA MOYENNE LOCALE ---
        # On prend les 5 biens les plus proches du même type pour faire une moyenne de prix fiable
        sorted_indices = distances.argsort()[0][:5] 
        closest_neighbors = df_filtered.iloc[sorted_indices]
        
        # Calcul des moyennes sur ces 5 voisins
        avg_price_m2 = closest_neighbors['prix_m2'].mean()
        # Sécurité si avg_price_m2 est NaN
        if pd.isna(avg_price_m2): avg_price_m2 = neighbor.get('prix_m2', 0)

        estimated_market_price = avg_price_m2 * surface

        # --- ÉTAPE 4 : PRÉDICTION IA (Si on veut utiliser le modèle ML) ---
        try:
            input_data = neighbor.copy()
            input_data['surface'] = surface 
            input_data['latitude'] = user_lat
            input_data['longitude'] = user_lon
            
            expected_cols = model.feature_names_in_
            model_input = pd.DataFrame(0, index=[0], columns=expected_cols)
            for col in expected_cols:
                if col in input_data:
                    model_input[col] = input_data[col]

            prediction_ml = model.predict(model_input)[0]
        except Exception as ml_err:
            print(f"⚠️ Erreur ML (fallback sur moyenne) : {ml_err}")
            prediction_ml = estimated_market_price

        # --- VERDICT FINAL : Mix entre IA et Moyenne Locale ---
        # On affiche la prédiction ML, mais on renvoie aussi les stats locales pour info
        final_price = round(prediction_ml, 0)
        
        analysis_text = generate_analysis_text(neighbor)

        return jsonify({
            "estimated_price": final_price,
            "currency": "€",
            "analysis": analysis_text,
            "stats": {
                "prix_moyen": final_price,
                "prix_m2": round(avg_price_m2, 0), # Prix m2 moyen des 5 voisins du même type
                "nb_biens_analyse": len(df_filtered)
            },
            "info_debug": f"{info_debug_filter}. Voisin à {int(distances[0][closest_idx]*111000)}m"
        })

    except Exception as e:
        print(f"❌ Erreur : {e}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)