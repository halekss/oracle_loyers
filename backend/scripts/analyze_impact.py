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

print("🕵️‍♀️ Démarrage de l'enquête LOCATAIRE (Calibrage LOYER)...")

# 1. Chargement
if not os.path.exists(data_path):
    print(f"❌ Erreur : Fichier introuvable {data_path}")
    exit()

df = pd.read_csv(data_path)

# 2. Préparation
# On nettoie les NaN critiques pour l'analyse
df = df.dropna(subset=['prix_m2'])

y = df['prix_m2']

# On retire les infos administratives
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'surface', 'url', 'description', 'ville', 'type', 'code_postal', 'quartier', 'type_local']
X = df.drop(columns=features_to_drop, errors='ignore')

# On ne garde que les colonnes numériques et on vire les 'nb_'
X = X.select_dtypes(include=[np.number])
cols_nb = [c for c in X.columns if c.startswith('nb_')]
X = X.drop(columns=cols_nb)

# 3. Entraînement Rapide (Random Forest)
model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
X = X.fillna(0)
model.fit(X, y)
score = model.score(X, y)

print(f"🧠 Analyse basée sur {len(X)} annonces (Précision du modèle : {score*100:.1f}%)")

# 4. ANALYSE DÉTAILLÉE (Comparaison Proche vs Loin)
results = []
SEUIL_PROXIMITE = 400  # On considère "Proche" tout ce qui est à moins de 400m
SEUIL_SENSIBILITE = 0.5 # 50 centimes d'écart suffit pour être significatif en location

for col in X.columns:
    # L'importance donnée par l'IA (0 à 1) convertie en %
    importance = model.feature_importances_[X.columns.get_loc(col)] * 100
    
    # Calcul de l'impact CONCRET (en Euros)
    if "dist_" in col:
        # On divise les données en deux groupes
        mask_proche = df[col] < SEUIL_PROXIMITE
        prix_proche = df[mask_proche]['prix_m2'].mean()
        prix_loin = df[~mask_proche]['prix_m2'].mean()
        
        if pd.isna(prix_proche) or pd.isna(prix_loin):
            delta = 0
        else:
            delta = prix_proche - prix_loin
            
        # Interprétation Humaine (Calibrée Loyer)
        if delta > SEUIL_SENSIBILITE:
            verdict = f"📈 +{delta:.2f}€/m² (Plus cher si proche)"
        elif delta < -SEUIL_SENSIBILITE:
            verdict = f"📉 {delta:.2f}€/m² (Moins cher si proche)"
        else:
            verdict = f"😐 Neutre ({delta:+.2f}€)"
            
    elif col in ['latitude', 'longitude']:
        delta = 0
        verdict = "📍 Position GPS pure"
    else:
        delta = 0
        verdict = "❓ Autre critère"

    results.append({
        "Critère": col.replace("dist_", "").replace("gentrification_", "G:").replace("vice_", "V:").replace("nuisance_", "N:").replace("superstition_", "S:"),
        "Impact IA (%)": round(importance, 2),
        "Effet Proximité": verdict,
        "delta_val": delta
    })

# Création du DataFrame de résultats
res_df = pd.DataFrame(results)

# On trie par Importance IA
res_df = res_df.sort_values(by="Impact IA (%)", ascending=False)

print("\n" + "="*100)
print(f"🏆 GUIDE DU LOCATAIRE (Analyse < {SEUIL_PROXIMITE}m)")
print("="*100)
print(f"{'CRITÈRE':<35} | {'IMPACT':<8} | {'ANALYSE PRIX (Loyer)'}")
print("-" * 100)

for index, row in res_df.head(25).iterrows():
    print(f"{row['Critère']:<35} | {row['Impact IA (%)']:<5}%   | {row['Effet Proximité']}")

print("-" * 100)
print("💡 LECTURE :")
print(f"- Un écart de +1.00€/m² sur un T2 de 45m² = +45€ de loyer par mois.")