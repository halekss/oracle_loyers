import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

# --- 1. CONFIGURATION DES CHEMINS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, '..', 'data', 'master_immo_final.csv')
models_dir = os.path.join(script_dir, '..', 'models')
model_save_path = os.path.join(models_dir, 'price_predictor.pkl')

os.makedirs(models_dir, exist_ok=True)

print("🚀 Démarrage de l'entraînement (Version Simplifiée : Distances uniquement)...")

# --- 2. CHARGEMENT ET PRÉPARATION ---
if not os.path.exists(data_path):
    print(f"❌ Erreur : Fichier introuvable {data_path}")
    exit()

df = pd.read_csv(data_path)

# CIBLE : Le Prix du Loyer
y = df['prix']

# FEATURES : On nettoie
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'ville', 'type', 'code_postal']
X = df.drop(columns=features_to_drop, errors='ignore')

# --- MODIFICATION IMPORTANTE ICI ---
# On supprime toutes les colonnes qui commencent par 'nb_' (Nombre de...)
# On ne garde que les 'dist_' (Distance vers...), la Surface, et Lat/Lon.
cols_nb = [c for c in X.columns if c.startswith('nb_')]
X = X.drop(columns=cols_nb)

print(f"🧹 Suppression de {len(cols_nb)} colonnes 'Nombre' pour éviter la redondance.")

# On s'assure de ne garder que des chiffres
X = X.select_dtypes(include=[np.number])
X = X.fillna(0)

print(f"📊 Données prêtes : {X.shape[0]} annonces avec {X.shape[1]} critères (Surface + Distances).")

# --- 3. SÉPARATION (TRAIN / TEST) ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- 4. ENTRAÎNEMENT ---
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# --- 5. ÉVALUATION ---
predictions = model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("\n" + "="*40)
print(f"🏆 RÉSULTATS DU MODÈLE (PURE DISTANCE)")
print("="*40)
print(f"💰 Marge d'erreur moyenne : ± {mae:.2f} €")
print(f"📈 Précision (R²) : {r2:.2f} / 1.0")

# --- 6. IMPORTANCE DES CRITÈRES ---
importances = pd.DataFrame({
    'Feature': X.columns,
    'Importance': model.feature_importances_
}).sort_values(by='Importance', ascending=False)

print("\n🔍 Top 5 des critères qui décident du prix :")
print(importances.head(5))

# --- 7. SAUVEGARDE ---
joblib.dump(model, model_save_path)
print(f"\n💾 Modèle sauvegardé dans : {model_save_path}")