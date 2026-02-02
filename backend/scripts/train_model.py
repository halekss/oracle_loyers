import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Vérification XGBoost
try:
    from xgboost import XGBRegressor
except ImportError:
    print("❌ Erreur : XGBoost n'est pas installé. (pip install xgboost)")
    exit()

# --- 1. CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(script_dir, '..', 'data', 'master_immo_final.csv')
models_dir = os.path.join(script_dir, '..', 'models')

# Chemins de sauvegarde
model_save_path = os.path.join(models_dir, 'price_predictor.pkl')
features_save_path = os.path.join(models_dir, 'model_features.pkl') # <--- LE FICHIER IMPORTANT

os.makedirs(models_dir, exist_ok=True)

print("🚀 Démarrage de l'entraînement (XGBoost - LOCATIONS)...")

# --- 2. CHARGEMENT ---
if not os.path.exists(data_path):
    print(f"❌ Erreur : Fichier introuvable {data_path}")
    exit()

df = pd.read_csv(data_path)

# 🚨 FILTRAGE LOCATIONS (Garde-fou)
# On exclut les prix > 10 000€ qui sont sûrement des ventes
df = df[df['prix'] <= 10000]

print(f"✅ Dataset chargé : {len(df)} annonces (Locations uniquement)")

# CIBLE
y = df['prix']

# --- 3. NETTOYAGE AGRESSIF ---
# On vire les colonnes qui ne servent pas à prédire
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'ville', 'titre', 'date']
X = df.drop(columns=features_to_drop, errors='ignore')

# On vire les colonnes 'nb_' pour ne garder que les distances 'dist_'
# (C'est ce qui donnait tes bons résultats précédents)
cols_nb = [c for c in X.columns if c.startswith('nb_')]
X = X.drop(columns=cols_nb)

# --- 4. ENCODAGE AUTOMATIQUE ---
# Conversion du texte (ex: Type de bien) en chiffres (0 ou 1)
cols_text = X.select_dtypes(include=['object']).columns

if len(cols_text) > 0:
    print(f"🔧 Encodage des colonnes texte : {list(cols_text)}")
    X = pd.get_dummies(X, columns=cols_text, drop_first=True)

# Sécurité : tout en numérique
X = X.apply(pd.to_numeric, errors='coerce').fillna(0)

print(f"📊 Données prêtes pour l'IA : {X.shape[0]} lignes x {X.shape[1]} colonnes.")

# --- 5. TRAIN / TEST SPLIT ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- 6. ENTRAÎNEMENT XGBOOST ---
print("\n🧠 Entraînement du cerveau (XGBoost)...")

model = XGBRegressor(
    n_estimators=1500,
    learning_rate=0.01,
    max_depth=7,
    subsample=0.7,
    colsample_bytree=0.6,
    n_jobs=-1,
    random_state=42
)

model.fit(X_train, y_train)

# --- 7. ÉVALUATION ---
predictions = model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("\n" + "="*40)
print(f"🏆 RÉSULTATS")
print("="*40)
print(f"💰 Marge d'erreur : ± {mae:.0f} €")
print(f"📈 Précision (R²) : {r2:.2f} / 1.0")

# --- 8. SAUVEGARDE (CRITIQUE POUR APP.PY) ---
print("\n💾 Sauvegarde des fichiers système...")

# A. Le Modèle
joblib.dump(model, model_save_path)

# B. La liste EXACTE des colonnes (C'est ça qui manquait !)
# L'application en a besoin pour savoir dans quel ordre mettre les infos
feature_list = X.columns.tolist()
joblib.dump(feature_list, features_save_path)

print(f"✅ Modèle sauvegardé : {model_save_path}")
print(f"✅ Features sauvegardées : {features_save_path} ({len(feature_list)} colonnes)")
print("\n🚀 TERMINÉ. Tu peux relancer le backend !")