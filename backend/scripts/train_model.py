import hashlib
import io
import json
import pandas as pd
import numpy as np
import os
from datetime import datetime, timezone
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

from data_versioning import archive_model_version, record_model_metadata, snapshot_dataset

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
metrics_log_path = os.path.join(models_dir, 'training_metrics.jsonl')

os.makedirs(models_dir, exist_ok=True)

print("🚀 Démarrage de l'entraînement (Mode : XGBoost Blindé)...")

# --- 2. CHARGEMENT ---
if not os.path.exists(data_path):
    print(f"❌ Erreur : Fichier introuvable {data_path}")
    exit()

df = pd.read_csv(data_path)

# CIBLE
y = df['prix']

# --- 3. NETTOYAGE AGRESSIF ---
# On vire les colonnes d'identification pure. `ville` est INTENTIONNELLEMENT
# gardée (pas dans cette liste) : encodée automatiquement par le one-hot plus
# bas comme `quartier`/`type_local`, elle permet au modèle d'apprendre un
# effet prix par ville dès qu'il y en a plus d'une dans les données (ORA-71).
# Tant qu'une seule ville existe, `drop_first=True` supprime cette unique
# catégorie : aucun changement de comportement avec les données actuelles.
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'titre', 'date']
X = df.drop(columns=features_to_drop, errors='ignore')

# On vire les colonnes 'nb_' (Nombres) pour ne garder que les 'dist_'
cols_nb = [c for c in X.columns if c.startswith('nb_')]
X = X.drop(columns=cols_nb)

# --- 4. ENCODAGE AUTOMATIQUE (Le Fix) ---
# On cherche TOUTES les colonnes qui sont encore du texte (object)
cols_text = X.select_dtypes(include=['object']).columns

if len(cols_text) > 0:
    print(f"🔧 Conversion automatique des colonnes texte en chiffres : {list(cols_text)}")
    # On transforme le texte en colonnes binaires (0/1)
    X = pd.get_dummies(X, columns=cols_text, drop_first=True)

# Sécurité finale : on force tout en numérique et on remplit les trous
X = X.apply(pd.to_numeric, errors='coerce') # Force tout en nombre
X = X.fillna(0)

print(f"📊 Données prêtes : {X.shape[0]} annonces x {X.shape[1]} critères.")

# --- 5. TRAIN / TEST ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- 6. ENTRAÎNEMENT XGBOOST ---
hyperparameters = {
    'n_estimators': 1500,
    'learning_rate': 0.01,
    'max_depth': 7,
    'subsample': 0.7,
    'colsample_bytree': 0.6,
    'random_state': 42,
}
model = XGBRegressor(n_jobs=-1, **hyperparameters)

model.fit(X_train, y_train)

# --- 7. ÉVALUATION ---
predictions = model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("\n" + "="*40)
print(f"🏆 RÉSULTATS XGBOOST (Contextualisé)")
print("="*40)
print(f"💰 Marge d'erreur moyenne : ± {mae:.2f} €")
print(f"📈 Précision (R²)       : {r2:.2f} / 1.0")

# --- 7bis. PERSISTANCE DES MÉTRIQUES (historique comparable d'un run à l'autre) ---
metrics_entry = {
    "trained_at": datetime.now(timezone.utc).isoformat(),
    "mae": round(float(mae), 2),
    "r2": round(float(r2), 4),
    "dataset_size": int(X.shape[0]),
    "n_features": int(X.shape[1]),
}
with open(metrics_log_path, 'a', encoding='utf-8') as f:
    f.write(json.dumps(metrics_entry, ensure_ascii=False) + "\n")
print(f"📈 Métriques ajoutées à l'historique : {metrics_log_path}")

# --- 8. IMPORTANCE DES CRITÈRES ---
importances = pd.DataFrame({
    'Feature': X.columns,
    'Importance': model.feature_importances_
}).sort_values(by='Importance', ascending=False)

print("\n🔍 Top 12 des critères décisifs :")
print(importances.head(12).to_string(index=False))

# --- 9. SAUVEGARDE ---
# Sérialisé en mémoire d'abord pour pouvoir hasher le binaire exact écrit sur
# disque (ORA-31 : identifie chaque modèle entraîné par un hash de version).
model_buffer = io.BytesIO()
joblib.dump(model, model_buffer)
model_bytes = model_buffer.getvalue()
model_version = hashlib.sha256(model_bytes).hexdigest()[:12]

with open(model_save_path, 'wb') as f:
    f.write(model_bytes)
print(f"\n💾 Modèle sauvegardé : {model_save_path} (version {model_version})")

versioned_path = archive_model_version(model_save_path, model_bytes, model_version)
print(f"🗂️  Version archivée : {versioned_path} — voir rollback_model.py pour y revenir sans réentraîner.")

# --- 10. VERSIONING DES DONNÉES (ORA-28) ET MÉTADONNÉES DU MODÈLE (ORA-31) ---
# Trace quelle version de master_immo_final.csv a servi à entraîner ce modèle,
# pour pouvoir reproduire un ancien modèle à partir de son snapshot.
snapshots_dir = os.path.join(script_dir, '..', 'data', 'snapshots')
data_snapshot_sha256 = snapshot_dataset(data_path, snapshots_dir)
data_snapshot_file = f"master_immo_final_{data_snapshot_sha256[:12]}.csv"
meta_path = record_model_metadata(
    model_save_path,
    data_snapshot_sha256=data_snapshot_sha256,
    data_snapshot_file=data_snapshot_file,
    metrics={'mae': float(mae), 'r2': float(r2)},
    model_version=model_version,
    hyperparameters=hyperparameters,
)
print(f"📌 Snapshot des données : {data_snapshot_file} ({data_snapshot_sha256[:12]}...)")
print(f"📎 Métadonnées du modèle : {meta_path}")