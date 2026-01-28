from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd
import joblib
import os
import numpy as np
from scipy.spatial import distance

# --- IMPORTS DES SERVICES (On garde ton architecture) ---
from services.data_loader import DataLoader
from services.map_generator import MapGenerator
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

# 1. CHARGEMENT DES DONNÉES
data_loader = DataLoader(DATA_DIR)
data_loader.load_csvs()
df = data_loader.df_immo 

# Sécurisation de la colonne type pour tes filtres
if not df.empty and 'type_local' not in df.columns:
    # Fallback si la colonne n'existe pas encore proprement
    df['type_local'] = df['type'] 

# 2. CHARGEMENT DU MODÈLE XGBOOST
print("🔮 Chargement du Cerveau XGBoost...")
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
    print("✅ Modèle chargé.")
else:
    print("❌ Modèle introuvable.")
    model = None

# 3. INITIALISATION DU GÉNÉRATEUR DE CARTE
map_gen = MapGenerator(data_loader, STATIC_DIR)
# On lance la génération au démarrage pour être sûr
try:
    map_gen.generate_full_map()
except Exception as e:
    print(f"⚠️ Erreur génération map au boot: {e}")


# --- FONCTIONS UTILITAIRES ---

def infer_type_local(surface):
    """Devine le type de bien selon la surface (Logique identique à l'entraînement)"""
    try:
        s = float(surface)
        if s < 35: return 'Studio/T1'
        elif s < 55: return 'T2'
        elif s < 75: return 'T3'
        else: return 'Grand (T4+)'
    except:
        return 'Studio/T1'

def generate_analysis_text(neighbor_row):
    """Génère le texte cynique basé sur le voisin le plus proche"""
    if neighbor_row is None:
        return "Zone inconnue. Probablement un terrain vague ou une faille spatio-temporelle."
    
    # Logique cynique simple basée sur les distances du voisin
    txt = "Analyse du secteur : "
    if neighbor_row.get('dist_gentrification_torréfacteur', 1000) < 300:
        txt += "Quartier Bobo confirmé (Torréfacteur à proximité). Prépare ton lait d'avoine. "
    elif neighbor_row.get('dist_vice_kebab', 1000) < 200:
        txt += "Zone étudiante ou fêtarde (Kebab stratégique détecté). "
    else:
        txt += "Quartier calme... ou mort. À toi de voir. "
    return txt


# --- ROUTES ---

@app.route('/')
def home():
    return jsonify({"status": "Oracle Online", "model": "XGBoost Contextualisé"})

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        surface = float(data.get('surface', 30))
        lat = float(data.get('latitude', 45.76))
        lon = float(data.get('longitude', 4.83))
        
        # 1. TROUVER LE VOISIN LE PLUS PROCHE (KNN)
        # On en a besoin pour récupérer les distances (écoles, bars...) et le Code Postal
        # car le frontend n'envoie pas ces infos.
        
        # On calcule les distances avec tous les points connus
        coords_ref = df[['latitude', 'longitude']].to_numpy()
        coords_user = np.array([[lat, lon]])
        
        # Distance Euclidienne rapide (suffisant pour trouver le plus proche)
        distances = distance.cdist(coords_user, coords_ref, metric='euclidean')
        closest_idx = distances.argmin()
        neighbor = df.iloc[closest_idx]
        
        # 2. PRÉPARATION DES DONNÉES POUR XGBOOST
        prediction_val = 0
        
        if model:
            # A. On déduit le type
            type_estime = infer_type_local(surface)
            
            # B. On prépare un DataFrame vide avec TOUTES les colonnes attendues par le modèle
            expected_cols = model.feature_names_in_
            model_input = pd.DataFrame(0, index=[0], columns=expected_cols)
            
            # C. On remplit les données de base
            if 'surface' in expected_cols: model_input['surface'] = surface
            if 'latitude' in expected_cols: model_input['latitude'] = lat
            if 'longitude' in expected_cols: model_input['longitude'] = lon
            
            # D. On remplit les distances (en copiant celles du voisin !)
            # C'est l'astuce : on assume que l'appart cible a le même environnement que son voisin
            for col in expected_cols:
                if col.startswith('dist_') and col in neighbor:
                    model_input[col] = neighbor[col]
            
            # E. On active le One-Hot Encoding pour le TYPE
            col_type = f"type_local_{type_estime}" # ex: type_local_T2
            if col_type in expected_cols:
                model_input[col_type] = 1
                
            # F. On active le One-Hot Encoding pour le CODE POSTAL (celui du voisin)
            cp_voisin = neighbor.get('code_postal', '69000') # ex: 69003
            col_cp = f"code_postal_{cp_voisin}"
            if col_cp in expected_cols:
                model_input[col_cp] = 1
            elif f"code_postal_{float(cp_voisin)}" in expected_cols: # Gestion du format float parfois
                 model_input[f"code_postal_{float(cp_voisin)}"] = 1

            # G. Prédiction
            try:
                prediction_val = model.predict(model_input)[0]
            except Exception as e:
                print(f"⚠️ Erreur XGBoost : {e}")
                prediction_val = 0

        # --- FALLBACK / STATS ---
        # Si le modèle échoue ou donne 0, on utilise la moyenne du quartier
        # On prend les 10 voisins les plus proches pour une stat locale
        closest_indices = distances.argsort()[0][:10]
        neighbors_df = df.iloc[closest_indices]
        avg_price_local = neighbors_df['prix'].mean()
        
        final_price = prediction_val if prediction_val > 100 else avg_price_local
        
        # Calcul prix m²
        price_m2 = final_price / surface if surface > 0 else 0

        return jsonify({
            "estimated_price": round(float(final_price), 0),
            "currency": "€",
            "analysis": generate_analysis_text(neighbor),
            "stats": {
                "prix_moyen": round(float(final_price), 0),
                "prix_m2": round(float(price_m2), 0),
                "nb_biens_analyse": 10 # Nombre de voisins consultés pour cohérence
            },
            "details": {
                "type_estime": infer_type_local(surface),
                "quartier_ref": str(neighbor.get('code_postal', 'Inconnu'))
            }
        })

    except Exception as e:
        print(f"❌ Erreur API Predict : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/listings', methods=['GET'])
def get_listings():
    """Renvoie les points pour la carte (filtrage optionnel)"""
    try:
        # On peut filtrer par type si un paramètre ?type=T2 est passé
        filter_type = request.args.get('type')
        
        data_to_send = df.copy()
        
        if filter_type and filter_type != 'all':
            # On utilise la colonne type_local si elle existe
            if 'type_local' in data_to_send.columns:
                data_to_send = data_to_send[data_to_send['type_local'] == filter_type]
        
        # Optimisation : on n'envoie que ce qui sert à la carte
        cols_map = ['latitude', 'longitude', 'prix', 'surface', 'type_local', 'id_annonce']
        # On vérifie que les colonnes existent
        cols_exist = [c for c in cols_map if c in data_to_send.columns]
        
        return jsonify(data_to_send[cols_exist].fillna(0).to_dict(orient='records'))
    except Exception as e:
        print(f"Erreur Listings: {e}")
        return jsonify([])

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True, port=8000)