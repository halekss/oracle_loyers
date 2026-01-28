import pandas as pd
import joblib
import os
import numpy as np

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, '..', 'data', 'master_immo_final.csv')
model_path = os.path.join(script_dir, '..', 'models', 'price_predictor.pkl')

print("🔮 Chargement de l'Oracle (le modèle)...")

# 1. Charger le modèle
if not os.path.exists(model_path):
    print("❌ Erreur : Modèle introuvable. Lance train_model.py d'abord !")
    exit()

model = joblib.load(model_path)

# 2. Charger les données
if not os.path.exists(data_path):
    print("❌ Erreur : Données introuvables.")
    exit()

df = pd.read_csv(data_path)

print("\n🎲 Pioche de 5 appartements au hasard...")

# On prend 5 lignes au hasard
samples = df.sample(5)

# --- C'EST ICI QUE LA MAGIE OPÈRE ---
# On demande au modèle : "Quelles colonnes veux-tu ?"
cols_attendues = model.feature_names_in_

for index, row in samples.iterrows():
    print(f"\n🏠 Appartement n°{row['id_annonce']} ({row['ville']})")
    print(f"   Surface : {row['surface']} m² | Loyer Réel : {row['prix']} €")
    
    # Préparation des données pour la prédiction
    # 1. On transforme la ligne en DataFrame (une seule ligne)
    row_df = pd.DataFrame([row])
    
    # 2. On filtre pour ne garder QUE les colonnes que le modèle attend
    # (Ça enlève automatiquement les 'nb_', le code postal, etc.)
    row_filtered = row_df[cols_attendues]
    
    # 3. On remplace les trous par 0 (sécurité)
    row_filtered = row_filtered.fillna(0)

    # Prédiction
    prix_estime = model.predict(row_filtered)[0]
    
    ecart = prix_estime - row['prix']
    
    print(f"   🔮 L'Oracle dit : {prix_estime:.0f} €")
    print(f"   📊 Différence : {ecart:+.0f} €")