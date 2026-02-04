import os
import requests
import pandas as pd
import joblib
import re
from flask import Flask, request, jsonify, send_from_directory 
from flask_cors import CORS

# --- SERVICES ---
from services.data_loader import DataLoader
from services.map_generator import MapGenerator

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DATA_PATH = os.path.join(DATA_DIR, 'master_immo_final.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'price_predictor.pkl')

# 🆕 CHEMIN DU FICHIER TXT
TXT_PATH = os.path.join(DATA_DIR, 'base_connaissance_immo.txt')

LM_STUDIO_URL = os.getenv('LM_STUDIO_URL', "http://host.docker.internal:1234/v1/chat/completions")

# ============================================================================
# 🧠 CHARGEMENT DU FICHIER TXT EN MÉMOIRE
# ============================================================================

print("📚 Chargement de la base de connaissances...")
knowledge_base = ""
try:
    with open(TXT_PATH, 'r', encoding='utf-8') as f:
        knowledge_base = f.read()
    print(f"✅ Base chargée : {len(knowledge_base)} caractères")
except Exception as e:
    print(f"⚠️ Fichier .txt introuvable : {e}")
    knowledge_base = ""

# ============================================================================
# 🔍 FONCTION DE RECHERCHE DANS LE FICHIER TXT
# ============================================================================

def search_in_knowledge_base(user_query):
    """
    Cherche les annonces pertinentes dans le fichier txt
    selon la question de l'utilisateur
    """
    if not knowledge_base:
        return "Pas de données disponibles."
    
    query_lower = user_query.lower()
    
    # Détection de critères
    quartiers_detectes = []
    prix_max = None
    type_bien = None
    
    # QUARTIERS DE LYON
    quartiers = [
        'croix-rousse', 'croix rousse', 'part-dieu', 'part dieu',
        'guillotière', 'guillotiere', 'ainay', 'confluence',
        'bellecour', 'vieux lyon', 'fourvière', 'fourviere',
        'gerland', 'monplaisir', 'bachut', 'jean macé', 'jean mace',
        'saxe', 'garibaldi', 'vaise', 'valmy'
    ]
    
    for q in quartiers:
        if q in query_lower:
            quartiers_detectes.append(q)
    
    # PRIX
    prix_match = re.search(r'(\d+)\s*(?:€|euros?|balles?)', query_lower)
    if prix_match:
        prix_max = int(prix_match.group(1))
    
    # TYPE (T1, T2, T3...)
    if 't1' in query_lower or 'studio' in query_lower:
        type_bien = 'T1'
    elif 't2' in query_lower:
        type_bien = 'T2'
    elif 't3' in query_lower:
        type_bien = 'T3'
    
    # RECHERCHE DANS LE FICHIER
    annonces_trouvees = []
    
    # Découper le fichier en annonces
    annonces_blocs = knowledge_base.split('═══════════════════════════════════════════════════════════════')
    
    for bloc in annonces_blocs:
        if 'ANNONCE #' not in bloc:
            continue
        
        # Extraire infos
        match_id = re.search(r'ANNONCE #(\d+)', bloc)
        match_quartier = re.search(r'Quartier : (.+)', bloc)
        match_prix = re.search(r'Prix : ([\d.]+) €/mois', bloc)
        match_surface = re.search(r'Surface : ([\d.]+) m²', bloc)
        match_prix_m2 = re.search(r'Prix au m² : ([\d.]+) €/m²', bloc)
        
        if not all([match_id, match_quartier, match_prix, match_surface]):
            continue
        
        annonce_id = match_id.group(1)
        quartier = match_quartier.group(1).strip()
        prix = float(match_prix.group(1))
        surface = float(match_surface.group(1))
        prix_m2 = float(match_prix_m2.group(1)) if match_prix_m2 else prix/surface
        
        # FILTRAGE
        valide = True
        
        # Filtre quartier
        if quartiers_detectes:
            quartier_lower = quartier.lower()
            if not any(q in quartier_lower for q in quartiers_detectes):
                valide = False
        
        # Filtre prix
        if prix_max and prix > prix_max:
            valide = False
        
        # Si valide, ajouter
        if valide:
            annonces_trouvees.append({
                'id': annonce_id,
                'quartier': quartier,
                'prix': prix,
                'surface': surface,
                'prix_m2': prix_m2,
                'bloc': bloc[:500]  # Garder un extrait
            })
    
    # Limiter à 5 résultats
    annonces_trouvees = annonces_trouvees[:5]
    
    # FORMATER LE CONTEXTE
    if not annonces_trouvees:
        return "Aucune annonce trouvée avec ces critères."
    
    context = f"📊 {len(annonces_trouvees)} annonce(s) trouvée(s) :\n\n"
    
    for annonce in annonces_trouvees:
        context += f"""ANNONCE #{annonce['id']} :
- Quartier : {annonce['quartier']}
- Prix : {annonce['prix']:.0f} €/mois
- Surface : {annonce['surface']:.1f} m²
- Prix au m² : {annonce['prix_m2']:.2f} €/m²

"""
    
    return context

# ============================================================================
# ⚙️ INITIALISATION
# ============================================================================

print("🚀 Chargement des données CSV...")
data_loader = DataLoader(DATA_PATH)

print("🛠️  Génération automatique de la carte de Lyon...")
try:
    if not os.path.exists(STATIC_DIR): os.makedirs(STATIC_DIR)
    map_gen = MapGenerator(static_dir=STATIC_DIR, data_dir=DATA_DIR)
    map_gen.generate(data_loader)
    print("✅ Carte générée.")
except Exception as e:
    print(f"⚠️ Erreur Carte : {e}")

# Chargement du modèle XGBoost
model = None
try:
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print("✅ Modèle XGBoost chargé.")
    else:
        print("⚠️ Modèle .pkl introuvable.")
except Exception as e:
    print(f"❌ Erreur chargement modèle : {e}")

# ============================================================================
# 🌐 ROUTES API
# ============================================================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route('/api/listings', methods=['GET'])
def get_listings():
    df = data_loader.get_data()
    if df is None: return jsonify([])
    return jsonify(df[['latitude', 'longitude', 'prix', 'type_local', 'quartier']].fillna('').to_dict(orient='records'))

@app.route('/api/quartier-stats', methods=['POST'])
def get_quartier_stats():
    try:
        data = request.json
        quartier_input = data.get('quartier', '').strip()
        df = data_loader.get_data()
        
        mask = df['quartier'].str.contains(quartier_input, case=False, na=False)
        res = df[mask].dropna(subset=['prix', 'surface'])

        if res.empty: return jsonify({"found": False}), 200

        avg_price = res['prix'].mean()
        avg_m2 = (res['prix'] / res['surface']).mean()
        
        return jsonify({
            "found": True,
            "quartier_detecte": res['quartier'].mode()[0],
            "count": int(len(res)),
            "prix_moyen": round(float(avg_price)),
            "prix_m2_moyen": round(float(avg_m2))
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    🆕 L'Oracle de Lyon avec RAG MANUEL
    Cherche dans le fichier .txt et envoie le contexte à LM Studio
    """
    try:
        data = request.json
        user_msg = data.get('message', '')
        
        print(f"\n📨 Question : {user_msg}")
        
        # 🔍 RECHERCHE DANS LE FICHIER TXT
        context = search_in_knowledge_base(user_msg)
        
        print(f"📚 Contexte trouvé : {len(context)} caractères")
        
        # 🆕 PROMPT SYSTÈME OPTIMISÉ
        system_prompt = f"""Tu es l'Oracle de Lyon, expert immobilier cynique et sarcastique.

🎯 TON RÔLE :
- Répondre aux questions sur les logements à Lyon
- Utiliser UNIQUEMENT les données ci-dessous (ne JAMAIS inventer)
- Citer TOUJOURS les ID d'annonces (#1, #2, etc.)
- Parler avec l'argot lyonnais (gone, "eh bè!")

⚠️ RÈGLES STRICTES :
1. Réponds UNIQUEMENT avec les données fournies ci-dessous
2. Cite les ID d'annonces (#123, #456...)
3. Si l'info n'est pas ci-dessous → dis "J'ai pas cette info dans ma base"
4. JAMAIS inventer de prix ou d'adresses
5. Maximum 6-7 lignes de réponse

📊 DONNÉES DISPONIBLES :
{context}"""

        # 🚀 APPEL À LM STUDIO
        payload = {
            "model": "meta-llama-3-8b-instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.3,  # ⬇️ Plus bas pour être factuel
            "max_tokens": 500,
            "stream": False
        }

        print("📤 Envoi à LM Studio...")
        r = requests.post(LM_STUDIO_URL, json=payload, timeout=60)
        
        if r.status_code == 200:
            response = r.json()['choices'][0]['message']['content']
            print(f"📥 Réponse reçue : {response[:100]}...")
            return jsonify({"response": response})
        else:
            print(f"❌ Erreur LM Studio : {r.status_code}")
            return jsonify({"response": "L'Oracle est au bouchon, repasse plus tard."}), 200
            
    except Exception as e:
        print(f"❌ Erreur chat : {e}")
        return jsonify({"response": "L'Oracle est en panne."}), 200

@app.route('/api/predict-price', methods=['POST'])
def predict_price():
    """Utilise le modèle XGBoost chargé au démarrage"""
    if not model:
        return jsonify({"error": "Modèle non chargé"}), 503
    
    try:
        data = request.json
        features = pd.DataFrame([data['features']]) 
        prediction = model.predict(features)[0]
        
        return jsonify({
            "estimated_price": round(float(prediction), 2),
            "currency": "EUR"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 ORACLE CHATBOT v9.0 - RAG MANUEL ACTIVÉ")
    print("="*60)
    print(f"📚 Base de connaissances : {'✅ Chargée' if knowledge_base else '❌ Manquante'}")
    print(f"🤖 LM Studio : {LM_STUDIO_URL}")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)