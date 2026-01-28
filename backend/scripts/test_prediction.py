import pandas as pd
import joblib
import os
import random
import numpy as np

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
# On pointe vers les dossiers parents corrects
model_path = os.path.join(script_dir, '..', 'models', 'price_predictor.pkl')
data_path = os.path.join(script_dir, '..', 'data', 'master_immo_final.csv')

# --- CHARGEMENT ---
print("🔮 Chargement de l'Oracle (le modèle)...")
if not os.path.exists(model_path):
    print("❌ Modèle introuvable ! Lancez train_model.py d'abord.")
    exit()

model = joblib.load(model_path)
df = pd.read_csv(data_path)

# --- PRÉPARATION IDENTIQUE À L'ENTRAÎNEMENT ---
# 1. On nettoie les colonnes inutiles
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'ville', 'type', 'code_postal']
X = df.drop(columns=features_to_drop, errors='ignore')

# 2. IMPORTANT : On supprime les 'nb_' comme dans le train_model.py
cols_nb = [c for c in X.columns if c.startswith('nb_')]
X = X.drop(columns=cols_nb)

# 3. Sécurité numérique
X = X.select_dtypes(include=[np.number])
X = X.fillna(0)

# --- LE JEU DE LA DIVINATION ---
print("\n🎲 Pioche de 5 appartements au hasard...")
random_indices = random.sample(range(len(df)), 5)

for i in random_indices:
    # On récupère les features de cet appart
    row = X.iloc[[i]] 
    
    # Infos pour l'affichage (Surface + Vrai Prix)
    surface = row['surface'].values[0]
    vrai_prix = df.iloc[i]['prix']
    
    # Prédiction
    try:
        prix_estime = model.predict(row)[0]
    except Exception as e:
        print(f"❌ Erreur prédiction : {e}")
        continue
    
    # Calcul de l'écart
    ecart = prix_estime - vrai_prix
    ecart_percent = (abs(ecart) / vrai_prix) * 100
    
    # Résultat visuel
    print(f"\n🏠 Appartement n°{df.iloc[i].get('id_annonce', 'Inconnu')} ({surface} m²)")
    print(f"   💰 Vrai Loyer      : {vrai_prix:.0f} €")
    print(f"   🤖 Loyer Estimé    : {prix_estime:.0f} €")
    
    if abs(ecart_percent) < 10:
        print(f"   ✅ Bravo ! (Écart : {ecart:+.0f} € / {ecart_percent:.1f}%)")
    elif abs(ecart_percent) < 20:
        print(f"   ⚠️ Pas mal... (Écart : {ecart:+.0f} € / {ecart_percent:.1f}%)")
    else:
        print(f"   ❌ Aïe, raté. (Écart : {ecart:+.0f} € / {ecart_percent:.1f}%)")

print("\n✨ Fin du test.")