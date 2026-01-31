import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

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
model_save_path = os.path.join(models_dir, 'price_predictor.pkl')

os.makedirs(models_dir, exist_ok=True)

print("🚀 Démarrage de l'entraînement (XGBoost - LOCATIONS UNIQUEMENT)")

# --- 2. CHARGEMENT ---
if not os.path.exists(data_path):
    print(f"❌ Erreur : Fichier introuvable {data_path}")
    exit()

df = pd.read_csv(data_path)

print(f"\n📊 STATISTIQUES DATASET:")
print(f"Total annonces : {len(df)}")
print(f"Prix MIN : {df['prix'].min():.0f} €")
print(f"Prix MAX : {df['prix'].max():.0f} €")
print(f"Prix MOYEN : {df['prix'].mean():.0f} €")
print(f"Prix MÉDIAN : {df['prix'].median():.0f} €")

# 🚨 VALIDATION CRITIQUE : Vérifier qu'on a QUE des locations
if df['prix'].max() > 10000:
    print("\n⚠️ ATTENTION : Prix > 10 000€ détectés (probablement des VENTES)")
    print("Filtrage en cours...")
    df = df[df['prix'] <= 10000]
    print(f"✅ Dataset nettoyé : {len(df)} annonces conservées")

# CIBLE
y = df['prix']

# --- 3. NETTOYAGE AGRESSIF ---
# On vire les colonnes d'identification pure
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'ville', 'titre', 'date']
X = df.drop(columns=features_to_drop, errors='ignore')

# On vire les colonnes 'nb_' (Nombres) pour ne garder que les 'dist_'
cols_nb = [c for c in X.columns if c.startswith('nb_')]
X = X.drop(columns=cols_nb)

# --- 4. ENCODAGE AUTOMATIQUE ---
cols_text = X.select_dtypes(include=['object']).columns

if len(cols_text) > 0:
    print(f"🔧 Conversion automatique des colonnes texte : {list(cols_text)}")
    X = pd.get_dummies(X, columns=cols_text, drop_first=True)

# Sécurité finale : on force tout en numérique et on remplit les trous
X = X.apply(pd.to_numeric, errors='coerce')
X = X.fillna(0)

print(f"📊 Données prêtes : {X.shape[0]} annonces x {X.shape[1]} critères.")

# --- 5. TRAIN / TEST ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- 6. ENTRAÎNEMENT XGBOOST ---
print("\n🧠 Entraînement du modèle XGBoost...")

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

print("\n" + "="*60)
print(f"🏆 RÉSULTATS XGBOOST")
print("="*60)
print(f"💰 Marge d'erreur moyenne : ± {mae:.2f} €")
print(f"📈 Précision (R²)          : {r2:.2f} / 1.0")
print(f"📊 Sur {len(y_test)} tests")

# Vérifier qu'aucune prédiction n'est aberrante
pred_min = predictions.min()
pred_max = predictions.max()
print(f"\n🔍 VALIDATION PRÉDICTIONS:")
print(f"   Min prédit : {pred_min:.0f} €")
print(f"   Max prédit : {pred_max:.0f} €")

if pred_max > 10000:
    print("\n⚠️ ALERTE : Le modèle prédit des prix > 10 000€ !")
    print("   → Vérifiez vos données d'entraînement")
else:
    print("   ✅ Toutes les prédictions sont cohérentes (locations)")

# --- 8. IMPORTANCE DES CRITÈRES ---
importances = pd.DataFrame({
    'Feature': X.columns,
    'Importance': model.feature_importances_
}).sort_values(by='Importance', ascending=False)

print("\n📊 Top 12 des critères décisifs :")
print(importances.head(12).to_string(index=False))

# --- 9. SAUVEGARDE ---
joblib.dump(model, model_save_path)
print(f"\n💾 Modèle sauvegardé : {model_save_path}")
print("\n" + "="*60)
print("✅ ENTRAÎNEMENT TERMINÉ")
print("="*60)
print(f"🎯 Le modèle est maintenant calibré pour des LOCATIONS")
print(f"   Prix attendus : {y.min():.0f}€ - {y.max():.0f}€")