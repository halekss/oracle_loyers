from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import joblib
import os
import json
import requests
from geopy.distance import geodesic

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Chemins des fichiers
IMMO_CSV = os.path.join(DATA_DIR, 'master_immo_final.csv')
POI_CSV = os.path.join(DATA_DIR, 'cavaliers_lyon.csv')
METRO_JSON = os.path.join(DATA_DIR, 'metro_lyon.json')
MODEL_PATH = os.path.join(MODELS_DIR, 'price_predictor.pkl')
SYSTEM_PROMPT_PATH = os.path.join(BASE_DIR, 'oracle_system_prompt.md')

# Configuration LM Studio
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1/chat/completions")

# --- CHARGEMENT DES DONNÉES ---
print("🔮 Chargement de l'Oracle...")

try:
    df_immo = pd.read_csv(IMMO_CSV)
    print(f"✅ IMMO : {len(df_immo)} annonces chargées.")
except Exception as e:
    print(f"❌ IMMO ERREUR : {e}")
    df_immo = pd.DataFrame()

try:
    df_poi = pd.read_csv(POI_CSV)
    print(f"✅ POI : {len(df_poi)} lieux chargés.")
except Exception as e:
    print(f"❌ POI ERREUR : {e}")
    df_poi = pd.DataFrame()

try:
    model = joblib.load(MODEL_PATH)
    print(f"✅ MODÈLE ML : Chargé depuis {MODEL_PATH}")
except Exception as e:
    print(f"❌ MODÈLE ERREUR : {e}")
    model = None

try:
    with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
        BASE_SYSTEM_PROMPT = f.read()
    print(f"✅ SYSTEM PROMPT : Chargé depuis {SYSTEM_PROMPT_PATH}")
except Exception as e:
    print(f"❌ SYSTEM PROMPT ERREUR : {e}")
    BASE_SYSTEM_PROMPT = "Tu es l'Oracle des Loyers de Lyon."

print("🎉 Oracle prêt !\n")


# --- FONCTIONS UTILITAIRES ---

def get_arrondissement(lat, lon):
    """Détermine l'arrondissement de Lyon basé sur les coordonnées"""
    # Simplification (à améliorer avec un vrai GeoJSON des arrondissements)
    if lat > 45.77 and lon < 4.84:
        return "4ème arrondissement"
    elif lat > 45.76 and lon > 4.85:
        return "3ème arrondissement"
    elif lat > 45.75 and lat < 45.77 and lon > 4.82 and lon < 4.85:
        return "2ème arrondissement"
    elif lat < 45.75 and lon < 4.83:
        return "2ème arrondissement"
    elif lat < 45.74:
        return "7ème arrondissement"
    else:
        return "Arrondissement inconnu"


def get_neighborhood_name(lat, lon):
    """Devine le nom du quartier basé sur les coordonnées"""
    # Table simplifiée (à enrichir)
    neighborhoods = {
        (45.774, 4.832): "Croix-Rousse",
        (45.758, 4.832): "Bellecour",
        (45.760, 4.859): "Part-Dieu",
        (45.767, 4.835): "Hôtel de Ville",
        (45.780, 4.805): "Vaise",
        (45.705, 4.888): "Vénissieux",
        (45.760, 4.827): "Vieux Lyon"
    }
    
    # Trouver le quartier le plus proche
    min_dist = float('inf')
    closest_name = "Lyon"
    
    for (ref_lat, ref_lon), name in neighborhoods.items():
        dist = geodesic((lat, lon), (ref_lat, ref_lon)).meters
        if dist < min_dist:
            min_dist = dist
            closest_name = name
    
    return closest_name if min_dist < 1000 else "Lyon"


def get_nearest_metro(lat, lon):
    """Trouve la station de métro la plus proche"""
    metro_stations = [
        {"nom": "Bellecour", "lat": 45.7577, "lon": 4.8322},
        {"nom": "Part-Dieu", "lat": 45.7601, "lon": 4.8590},
        {"nom": "Hôtel de Ville", "lat": 45.7674, "lon": 4.8335},
        {"nom": "Perrache", "lat": 45.7485, "lon": 4.8266},
        {"nom": "Charpennes", "lat": 45.7710, "lon": 4.8636},
        {"nom": "Gare de Vaise", "lat": 45.7797, "lon": 4.8051},
        {"nom": "Vieux Lyon", "lat": 45.7598, "lon": 4.8268},
        {"nom": "Saxe-Gambetta", "lat": 45.7516, "lon": 4.8486},
        {"nom": "Croix-Rousse", "lat": 45.7740, "lon": 4.8320},
        {"nom": "Guillotière", "lat": 45.7543, "lon": 4.8427}
    ]
    
    min_dist = float('inf')
    nearest = "Métro inconnu"
    
    for station in metro_stations:
        dist = geodesic((lat, lon), (station['lat'], station['lon'])).meters
        if dist < min_dist:
            min_dist = dist
            nearest = station['nom']
    
    return nearest, int(min_dist)


def count_pois_nearby(lat, lon, radius_m=500):
    """Compte les POIs dans un rayon donné"""
    counts = {"vice": 0, "gentrification": 0, "nuisance": 0, "superstition": 0}
    
    if df_poi.empty:
        return counts
    
    for _, poi in df_poi.iterrows():
        if pd.notnull(poi.get('latitude')) and pd.notnull(poi.get('longitude')):
            dist = geodesic((lat, lon), (poi['latitude'], poi['longitude'])).meters
            
            if dist <= radius_m:
                poi_type = str(poi.get('type', '')).lower()
                
                # Classification
                if any(x in poi_type for x in ['bar', 'sex', 'casino', 'tabac', 'cbd']):
                    counts['vice'] += 1
                elif any(x in poi_type for x in ['sport', 'yoga', 'crèche', 'épicerie', 'torréfacteur', 'vélo', 'fleuriste', 'concept']):
                    counts['gentrification'] += 1
                elif any(x in poi_type for x in ['école', 'aire', 'concert', 'discothèque', 'station']):
                    counts['nuisance'] += 1
                elif any(x in poi_type for x in ['pompes', 'cimetière', 'culte', 'église']):
                    counts['superstition'] += 1
    
    return counts


def get_zone_median_price(neighborhood, type_local="T2"):
    """Calcule le prix médian d'une zone pour un type de bien"""
    if df_immo.empty:
        return 750  # Valeur par défaut
    
    # Filtrer par type de bien si possible
    zone_data = df_immo[df_immo['type_local'] == type_local] if 'type_local' in df_immo.columns else df_immo
    
    if len(zone_data) > 20:  # Besoin d'un minimum de données
        return int(zone_data['prix'].median())
    else:
        return int(df_immo['prix'].median())


def determine_type_from_surface(surface):
    """Détermine le type de bien basé sur la surface"""
    if surface < 35:
        return "Studio/T1"
    elif surface < 55:
        return "T2"
    elif surface < 75:
        return "T3"
    else:
        return "Grand (T4+)"


# --- ROUTES API ---

@app.route('/api/predict', methods=['POST'])
def predict():
    """
    🎯 ROUTE PRINCIPALE : Prédiction ML + Contexte enrichi
    """
    try:
        data = request.json
        lat = float(data.get('latitude'))
        lon = float(data.get('longitude'))
        surface = float(data.get('surface', 45))
        
        if model is None:
            return jsonify({"error": "Modèle ML non disponible"}), 500
        
        # --- 1. PRÉDICTION ML ---
        # Préparer les features (comme dans train_model.py)
        features_dict = {
            'latitude': lat,
            'longitude': lon,
            'surface': surface
        }
        
        # Ajouter les distances aux POIs (à calculer)
        pois = count_pois_nearby(lat, lon, radius_m=500)
        
        # Créer le DataFrame de prédiction
        X_pred = pd.DataFrame([features_dict])
        
        # Encoder les colonnes catégorielles si nécessaire
        # (Simplifié ici, à adapter selon ton modèle exact)
        for col in model.feature_names_in_:
            if col not in X_pred.columns:
                X_pred[col] = 0
        
        X_pred = X_pred[model.feature_names_in_]
        
        # Prédiction
        predicted_price = int(model.predict(X_pred)[0])
        prix_m2 = int(predicted_price / surface)
        
        # --- 2. CONTEXTE ENRICHI ---
        neighborhood = get_neighborhood_name(lat, lon)
        arrondissement = get_arrondissement(lat, lon)
        type_estime = determine_type_from_surface(surface)
        metro_name, metro_dist = get_nearest_metro(lat, lon)
        zone_median = get_zone_median_price(neighborhood, type_estime)
        
        ecart = predicted_price - zone_median
        ecart_percent = (ecart / zone_median * 100) if zone_median > 0 else 0
        tendance = "au-dessus" if ecart > 0 else "en-dessous"
        
        # --- 3. FACTEURS CLÉS (Top 3) ---
        facteurs_cles = [
            {
                "nom": "Surface",
                "impact": "+12%",  # À calculer dynamiquement si possible
                "valeur": f"{surface}m²",
                "explication": f"Surface de {surface}m² adaptée pour un {type_estime}"
            },
            {
                "nom": "Proximité métro",
                "impact": "+8%" if metro_dist < 400 else "+3%",
                "valeur": f"{metro_dist}m",
                "explication": f"Métro {metro_name} à {metro_dist}m, accès {'excellent' if metro_dist < 400 else 'correct'}"
            },
            {
                "nom": "Environnement",
                "impact": "+5%" if pois['gentrification'] > 2 else "+2%",
                "valeur": f"{pois['gentrification']} commerces",
                "explication": f"Zone {'en gentrification' if pois['gentrification'] > 2 else 'stable'} avec {pois['vice']} bars"            }
        ]
        
        # --- 4. CONSTRUCTION DE LA RÉPONSE ---
        response = {
            "prediction": {
                "loyer_estime": predicted_price,
                "prix_m2": prix_m2,
                "confiance": 85,  # À calculer dynamiquement si possible
                "type_logement": type_estime
            },
            "localisation": {
                "zone": neighborhood,
                "latitude": lat,
                "longitude": lon,
                "arrondissement": arrondissement
            },
            "contexte_marche": {
                "prix_median_zone": zone_median,
                "ecart_median": f"{ecart_percent:+.1f}%",
                "ecart_euros": ecart,
                "tendance": tendance
            },
            "proximite": {
                "metro_proche": metro_name,
                "distance_metro": f"{metro_dist}m",
                "pois_vice": pois['vice'],
                "pois_gentrification": pois['gentrification'],
                "pois_nuisance": pois['nuisance'],
                "pois_superstition": pois['superstition']
            },
            "facteurs_cles": facteurs_cles,
            
            # --- COMPATIBILITÉ AVEC ANCIEN FORMAT ---
            "estimated_price": predicted_price,
            "currency": "EUR",
            "stats": {
                "prix_m2": prix_m2
            },
            "details": {
                "prix_estime": predicted_price,
                "prix_m2": prix_m2,
                "zone": neighborhood,
                "type_estime": type_estime,
                "confiance": 85,
                "arrondissement": arrondissement,
                "prix_median_zone": zone_median,
                "ecart_median": f"{ecart_percent:+.1f}%",
                "tendance": tendance,
                "metro_proche": metro_name,
                "distance_metro": f"{metro_dist}m",
                "nb_vice": pois['vice'],
                "nb_gentri": pois['gentrification'],
                "nb_nuisance": pois['nuisance'],
                "facteurs_cles": facteurs_cles
            },
            "analysis": f"Scan terminé : {neighborhood}, {type_estime}, {predicted_price}€. Demande une analyse détaillée pour plus d'infos."
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ ERREUR PREDICT : {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    🤖 ROUTE CHAT : LLM avec contexte ML structuré
    """
    try:
        data = request.json
        user_message = data.get('message', '')
        ml_context = data.get('ml_context', None)
        
        if not user_message:
            return jsonify({"error": "Message vide"}), 400
        
        # --- CONSTRUCTION DU PROMPT SYSTÈME ---
        system_prompt = BASE_SYSTEM_PROMPT
        
        if ml_context and ml_context.get('ml_ready'):
            # 🔥 INJECTION STRUCTURÉE DES DONNÉES ML
            ml_injection = f"""

---

## 📊 CONTEXTE ML ACTUEL (Scan en cours)

**Tu DOIS utiliser ces données pour répondre. Ne les ignore JAMAIS.**

```json
{{
  "prediction": {{
    "loyer_estime": {ml_context.get('prix_estime', 'N/A')} €,
    "prix_m2": {ml_context.get('prix_m2', 'N/A')} €/m²,
    "confiance": {ml_context.get('confiance', 85)}%,
    "type_logement": "{ml_context.get('type_estime', 'N/A')}"
  }},
  "localisation": {{
    "zone": "{ml_context.get('zone', 'N/A')}",
    "arrondissement": "{ml_context.get('arrondissement', 'N/A')}"
  }},
  "contexte_marche": {{
    "prix_median_zone": {ml_context.get('prix_median_zone', 'N/A')} €,
    "ecart_median": "{ml_context.get('ecart_median', 'N/A')}",
    "ecart_euros": {ml_context.get('ecart_euros', 0)} €,
    "tendance": "{ml_context.get('tendance', 'N/A')}"
  }},
  "proximite": {{
    "metro_proche": "{ml_context.get('metro_proche', 'N/A')}",
    "distance_metro": "{ml_context.get('distance_metro', 'N/A')}",
    "pois_vice": {ml_context.get('nb_vice', 0)},
    "pois_gentrification": {ml_context.get('nb_gentri', 0)},
    "pois_nuisance": {ml_context.get('nb_nuisance', 0)}
  }},
  "facteurs_cles": {json.dumps(ml_context.get('facteurs_cles', []), ensure_ascii=False, indent=2)}
}}
```

**RÈGLE ABSOLUE** : Ces chiffres viennent du modèle ML entraîné sur 10 000+ annonces réelles. 
- Cite-les EXACTEMENT
- Ne les modifie PAS
- Ne les arrondis PAS (sauf si demandé explicitement)
- Construis ton raisonnement AUTOUR de ces données

---
"""
            system_prompt += ml_injection
        else:
            # Pas de contexte ML disponible
            system_prompt += "\n\n⚠️ ATTENTION : Aucun scan ML actif. L'utilisateur doit lancer un scan d'abord.\n"
        
# --- APPEL À LM STUDIO ---
        payload = {
            # ⚠️ Si l'erreur 400 persiste, essaye de changer le nom du modèle par "local-model"
            "model": "mistralai/mistral-7b-instruct-v0.3",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "temperature": 0.3,
            "max_tokens": 800,
            "top_p": 0.9,
            "frequency_penalty": 0.2,
            "presence_penalty": 0.1
        }
        
        print(f"💬 CHAT : Envoi à LM Studio...")
        print(f"   - Message : {user_message[:50]}...")
        # ✅ CORRECTION GUILLEMETS ICI :
        print(f"   - ML Context : {'Oui' if ml_context and ml_context.get('ml_ready') else 'Non'}")
        
        # 🛠️ DEBUG : Affiche ce qu'on envoie exactement
        # print(f"📡 DEBUG PAYLOAD: {json.dumps(payload, indent=2)}")

        response = requests.post(
            LM_STUDIO_URL,
            json=payload,
            timeout=30
        )
        
        # 🛠️ DEBUG : Si erreur 400, on affiche pourquoi
        if response.status_code != 200:
            print(f"❌ ERREUR LM STUDIO BODY: {response.text}")

        if response.status_code == 200:
            llm_response = response.json()['choices'][0]['message']['content']
            print(f"✅ CHAT : Réponse reçue ({len(llm_response)} chars)")
            return jsonify({"response": llm_response})
        else:
            print(f"❌ CHAT : Erreur LM Studio {response.status_code}")
            return jsonify({"error": f"LM Studio error: {response.status_code}"}), 500
            
    except requests.exceptions.ConnectionError:
        print("❌ CHAT : Impossible de joindre LM Studio")
        return jsonify({"error": "Impossible de joindre LM Studio. Vérifie qu'il tourne sur le port 1234."}), 503
    except Exception as e:
        print(f"❌ CHAT : Erreur {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/listings', methods=['GET'])
def get_listings():
    """
    📊 ROUTE : Récupérer les annonces pour la carte
    """
    try:
        if df_immo.empty:
            return jsonify([])
        
        # Limiter à 200 annonces pour la performance
        listings = df_immo.head(200)[['latitude', 'longitude', 'prix', 'surface', 'type_local']].to_dict('records')
        return jsonify(listings)
    except Exception as e:
        print(f"❌ LISTINGS ERREUR : {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/static/<path:filename>')
def serve_static(filename):
    """
    📁 ROUTE : Servir les fichiers statiques (carte HTML)
    """
    return send_from_directory(STATIC_DIR, filename)


@app.route('/health', methods=['GET'])
def health():
    """
    ❤️ ROUTE : Vérifier que le serveur est vivant
    """
    return jsonify({
        "status": "alive",
        "model_loaded": model is not None,
        "immo_data": len(df_immo),
        "poi_data": len(df_poi)
    })


# --- DÉMARRAGE ---
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🔮 ORACLE LOYERS - Backend Flask")
    print("="*50)
    print(f"📡 LM Studio URL : {LM_STUDIO_URL}")
    print(f"📊 Données IMMO : {len(df_immo)} annonces")
    print(f"📍 Données POI : {len(df_poi)} lieux")
    # ✅ CORRECTION GUILLEMETS ICI AUSSI (Celle qui faisait planter Docker) :
    print(f"🤖 Modèle ML : {'✅ Chargé' if model else '❌ Absent'}")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)