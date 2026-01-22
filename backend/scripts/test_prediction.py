import pandas as pd
import joblib
import os
import random

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, '..', 'models', 'price_predictor.pkl')
data_path = os.path.join(script_dir, '..', 'data', 'master_immo_final.csv')

# --- CHARGEMENT ---
print("🔮 Chargement de l'Oracle (le modèle)...")
model = joblib.load(model_path)
df = pd.read_csv(data_path)

# On prépare les données comme pour l'entraînement
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'ville', 'type']
X = df.drop(columns=features_to_drop, errors='ignore')
X = X.fillna(0) # Sécurité

# --- LE JEU DE LA DIVINATION ---
print("\n🎲 Pioche de 5 appartements au hasard...")
random_indices = random.sample(range(len(df)), 5)

for i in random_indices:
    # Les infos de l'appart
    appart_data = X.iloc[[i]] # Double crochet pour garder le format DataFrame
    surface = appart_data['surface'].values[0]
    
    # Le vrai prix
    vrai_prix = df.iloc[i]['prix']
    
    # La prédiction
    prix_estime = model.predict(appart_data)[0]
    
    # Calcul de l'écart
    ecart = prix_estime - vrai_prix
    ecart_percent = (abs(ecart) / vrai_prix) * 100
    
    # Résultat visuel
    print(f"\n🏠 Appartement n°{df.iloc[i]['id_annonce']} ({surface} m²)")
    print(f"   💰 Vrai Loyer      : {vrai_prix:.0f} €")
    print(f"   🤖 Loyer Estimé    : {prix_estime:.0f} €")
    
    if abs(ecart_percent) < 10:
        print(f"   ✅ Bravo ! (Écart : {ecart:+.0f} € / {ecart_percent:.1f}%)")
    elif abs(ecart_percent) < 20:
        print(f"   ⚠️ Pas mal... (Écart : {ecart:+.0f} € / {ecart_percent:.1f}%)")
    else:
        print(f"   ❌ Aïe, raté. (Écart : {ecart:+.0f} € / {ecart_percent:.1f}%)")
        print(f"      (Lien : {df.iloc[i]['url']})")

print("\n✨ Fin du test.")