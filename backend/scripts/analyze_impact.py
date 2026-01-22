import pandas as pd
import numpy as np
import os
import warnings
from sklearn.ensemble import RandomForestRegressor

# On ignore les messages d'erreur techniques
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, '..', 'data', 'master_immo_final.csv')

print("🕵️‍♀️ Démarrage de l'enquête LOCATAIRE (Version Pure Distance)...")

# 1. Chargement
if not os.path.exists(data_path):
    print(f"❌ Erreur : Fichier introuvable {data_path}")
    exit()

df = pd.read_csv(data_path)

# 2. Préparation (On analyse le Prix au m²)
y = df['prix_m2']

# On retire les infos administratives ET la surface (pour isoler l'effet quartier)
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'surface', 'url', 'description', 'ville', 'type', 'code_postal']
X = df.drop(columns=features_to_drop, errors='ignore')

# --- SUPPRESSION DES COLONNES 'NOMBRE' (nb_) ---
cols_nb = [c for c in X.columns if c.startswith('nb_')]
X = X.drop(columns=cols_nb)

# Nettoyage final
X = X.fillna(0)
X = X.select_dtypes(include=[np.number])

# 3. Entraînement Rapide
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X, y)
score = model.score(X, y)
print(f"🧠 Analyse basée sur {len(X)} annonces (Précision : {score*100:.1f}%)")

# 4. ANALYSE DÉTAILLÉE
results = []

for col in X.columns:
    importance = model.feature_importances_[X.columns.get_loc(col)]
    corr = df[col].corr(df['prix_m2'])
    
    if pd.isna(corr): corr = 0.0

    # LOGIQUE LOCATAIRE (Inversée)
    if "dist_" in col:
        # Corr > 0 : Plus c'est LOIN, plus c'est CHER -> Donc PRÈS = MOINS CHER
        if corr > 0:
            verdict = "📉 BON PLAN (Loyer moins cher si tu es près)"
        # Corr < 0 : Plus c'est LOIN, moins c'est CHER -> Donc PRÈS = PLUS CHER
        else:
            verdict = "💸 SURCOÛT (Tu paies cher pour être près)"
            
    else:
        verdict = "📍 Impact Géographique pur"

    results.append({
        "Critère": col,
        "Impact Prix (%)": round(importance * 100, 2),
        "Corrélation": round(corr, 3),
        "Analyse Locataire": verdict
    })

# Création du tableau trié
res_df = pd.DataFrame(results).sort_values(by="Impact Prix (%)", ascending=False)

# Affichage
pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', None)

print("\n" + "="*110)
print(f"🏆 GUIDE DU LOCATAIRE SIMPLIFIÉ ({len(res_df)} Critères de Distance)")
print("="*110)
print(res_df.to_string(index=False))