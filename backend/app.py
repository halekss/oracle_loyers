from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd
import joblib
import os
import numpy as np
from scipy.spatial import distance

# --- IMPORTS DES SERVICES (Architecture Modulaire) ---
from services.data_loader import DataLoader
from services.map_generator import MapGenerator
# On garde ton import utilitaire si besoin
from services.utils import haversine_distance 

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION CHEMINS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')

# Création du dossier static si absent
os.makedirs(STATIC_DIR, exist_ok=True)

print("⏳ Démarrage de l'Oracle...")

# 1. CHARGEMENT DES DONNÉES (Via le service dédié)
data_loader = DataLoader(DATA_DIR)
data_loader.load_csvs()
df = data_loader.df_immo # Raccourci pour ton code

# Sécurisation de la colonne type pour tes filtres
if not df.empty and 'type_local' in df.columns:
    df['type_local'] = df['type_local'].fillna('').astype(str)

# 2. GÉNÉRATION DE LA CARTE (INDISPENSABLE pour l'Espion et l'affichage)
map_generator = MapGenerator(STATIC_DIR, DATA_DIR)
map_generator.generate(data_loader)

# 3. CHARGEMENT DU MODÈLE IA
model = None
try:
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print("✅ Modèle IA chargé en mémoire.")
    else:
        print("⚠️ Fichier modèle introuvable (pas grave, on fera sans).")
except Exception as e:
    print(f"❌ Erreur chargement Modèle : {e}")

# --- FONCTIONS UTILITAIRES ---
def generate_analysis_text(appart_data):
    """Génère le texte cynique."""
    messages = []
    # Utilisation de .get() pour éviter les crashs
    dist_ecole = appart_data.get('dist_nuisance_ecole', 1000) # Attention aux accents dans les noms de colonnes CSV
    dist_bar = appart_data.get('dist_vice_bar', 1000)

    if dist_ecole < 200:
        messages.append(f"📉 **Bon plan économie** : Une école est à {int(dist_ecole)}m. C'est bruyant, donc le loyer est moins cher !")
    if dist_bar < 100:
        messages.append(f"🍻 **Taxe ambiance** : Bars à {int(dist_bar)}m. Le quartier est vivant, et ça se paie !")
    
    if not messages:
        messages.append("📍 Quartier standard, ni trop bruyant, ni trop fêtard.")
    return messages

# --- ROUTES ---

@app.route('/')
def home():
    return "Oracle Backend Running 🚀"

# Route pour servir la carte (On pointe vers STATIC car c'est là que le générateur la crée)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

# Compatibilité avec ton frontend (parfois il appelle /maps/)
@app.route('/maps/<path:filename>')
def serve_maps(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route('/api/listings', methods=['GET'])
def get_listings():
    if df.empty: return jsonify({"error": "No data"}), 500
    # On remplace les NaN par null pour le JSON
    return jsonify(df.where(pd.notnull(df), None).to_dict(orient='records'))

@app.route('/api/predict', methods=['POST'])
def predict_smart():
    # Si le dataframe est vide, on arrête tout
    if df.empty: return jsonify({"error": "Données non chargées"}), 500

    try:
        data = request.json
        user_lat = data.get('latitude')
        user_lon = data.get('longitude')
        surface = data.get('surface', 30)
        room_filter = data.get('room_filter', 'all') # 'all', 't1', 't2', ...

        if user_lat is None or user_lon is None:
            return jsonify({"error": "Coordonnées GPS manquantes"}), 400

        # --- ÉTAPE 1 : FILTRAGE INTELLIGENT ---
        df_filtered = df.copy()

        if room_filter == 't1':
            df_filtered = df[df['type_local'].str.contains('T1|Studio', case=False, na=False)]
        elif room_filter == 't2':
            df_filtered = df[df['type_local'].str.contains('T2', case=False, na=False)]
        elif room_filter == 't3':
            df_filtered = df[df['type_local'].str.contains('T3', case=False, na=False)]
        elif room_filter == 't4+':
            df_filtered = df[df['type_local'].str.contains('T4|T5|Maison', case=False, na=False)]
        
        # Fallback si filtre trop restrictif
        if df_filtered.empty:
            df_filtered = df.copy()
            info_debug = "Filtre ignoré (0 résultats)"
        else:
            info_debug = f"Filtre actif : {room_filter}"

        # --- ÉTAPE 2 : VOISIN LE PLUS PROCHE ---
        locations_filtered = df_filtered[['latitude', 'longitude']].astype(float).values
        user_point = np.array([[user_lat, user_lon]])
        
        # Calcul distance (Scipy est très rapide)
        distances = distance.cdist(user_point, locations_filtered, 'euclidean')
        closest_idx = distances.argmin()
        neighbor = df_filtered.iloc[closest_idx].to_dict()
        
        # --- ÉTAPE 3 : MOYENNE LOCALE (5 plus proches) ---
        sorted_indices = distances.argsort()[0][:5]
        closest_neighbors = df_filtered.iloc[sorted_indices]
        
        avg_price_m2 = closest_neighbors['prix_m2'].mean()
        if pd.isna(avg_price_m2): avg_price_m2 = neighbor.get('prix_m2', 0)

        estimated_market_price = avg_price_m2 * surface

        # --- ÉTAPE 4 : PRÉDICTION IA ---
        prediction_ml = estimated_market_price # Valeur par défaut
        if model:
            try:
                # On prépare les données pour le modèle
                input_data = neighbor.copy()
                input_data['surface'] = surface 
                input_data['latitude'] = user_lat
                input_data['longitude'] = user_lon
                
                # On ne garde que les colonnes connues du modèle
                if hasattr(model, 'feature_names_in_'):
                    expected_cols = model.feature_names_in_
                    model_input = pd.DataFrame(0, index=[0], columns=expected_cols)
                    for col in expected_cols:
                        if col in input_data:
                            model_input[col] = input_data[col]
                    
                    prediction_ml = model.predict(model_input)[0]
                else:
                    # Fallback si le modèle n'a pas feature_names_in_
                    pass
            except Exception as ml_err:
                print(f"⚠️ Warning ML: {ml_err}")

        # --- VERDICT FINAL ---
        final_price = round(prediction_ml, 0)
        analysis_text = generate_analysis_text(neighbor)

        return jsonify({
            "estimated_price": final_price,
            "currency": "€",
            "analysis": analysis_text,
            "stats": {
                "prix_moyen": final_price,
                "prix_m2": round(avg_price_m2, 0),
                "nb_biens_analyse": len(df_filtered)
            },
            "info_debug": f"{info_debug}. Voisin à {int(distances[0][closest_idx]*111000)}m"
        })

    except Exception as e:
        print(f"❌ Erreur API : {e}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)