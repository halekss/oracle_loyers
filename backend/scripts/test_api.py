import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

# --- 1. CONFIGURATION DES CHEMINS (Compatibilité Docker) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# On remonte d'un cran pour aller dans 'backend' puis 'data'
DATA_PATH = os.path.join(BASE_DIR, '..', 'data', 'master_immo_final.csv')
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')
MODEL_SAVE_PATH = os.path.join(MODELS_DIR, 'price_predictor.pkl')

os.makedirs(MODELS_DIR, exist_ok=True)

print("🚀 Démarrage de l'entraînement (Version Simplifiée : Distances)...")

# --- 2. CHARGEMENT ET PRÉPARATION ---
if not os.path.exists(DATA_PATH):
    print(f"❌ Erreur : Fichier introuvable {DATA_PATH}")
    # On tente le chemin absolu Docker au cas où
    DATA_PATH = "/app/data/master_immo_final.csv"
    if not os.path.exists(DATA_PATH):
        print("❌ Echec définitif : Aucune donnée trouvée.")
        exit()

df = pd.read_csv(DATA_PATH)
print(f"📊 Données chargées : {len(df)} lignes.")

# Nettoyage de base (suppression des lignes vides critiques)
df = df.dropna(subset=['prix', 'surface'])
df = df[df['prix'] > 0]

# CIBLE
y = df['prix']

# FEATURES : Nettoyage violent
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'ville', 'type', 'code_postal', 'titre', 'date']
X = df.drop(columns=features_to_drop, errors='ignore')

# On supprime les colonnes 'nb_' comme tu le voulais
cols_nb = [c for c in X.columns if c.startswith('nb_')]
X = X.drop(columns=cols_nb)
print(f"🧹 Suppression de {len(cols_nb)} colonnes 'Compteurs' (nb_*) pour focus Distances.")

# On ne garde que les chiffres (Surface, Lat, Lon, Dist_*)
X = X.select_dtypes(include=[np.number])
X = X.fillna(0)

print(f"🧠 Features utilisées ({X.shape[1]}) : {list(X.columns)}")

# --- 3. ENTRAÎNEMENT ---
if len(X) > 10:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # --- 4. ÉVALUATION ---
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    print("\n" + "="*40)
    print(f"🏆 RÉSULTATS DU MODÈLE")
    print("="*40)
    print(f"💰 Marge d'erreur : ± {mae:.0f} €")
    print(f"📈 Précision (R²) : {r2:.2f}")

    # --- 5. SAUVEGARDE ---
    joblib.dump(model, MODEL_SAVE_PATH)
    print(f"\n💾 Modèle sauvegardé dans : {MODEL_SAVE_PATH}")
else:
    print("⚠️ Pas assez de données pour entraîner.")