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

from data_fusion import load_declared_villes
from data_versioning import (
    archive_model_version,
    decide_promotion,
    load_active_model_metadata,
    record_model_metadata,
    snapshot_dataset,
)
from rollback_model import rollback_to

# Vérification XGBoost
try:
    from xgboost import XGBRegressor
except ImportError:
    print("❌ Erreur : XGBoost n'est pas installé. (pip install xgboost)")
    exit()


def resolve_ville_nom(ville_slug):
    return load_declared_villes()[ville_slug]['nom']


def train(ville_slug):
    """Entraîne, évalue et (si le garde-fou de régression le permet) promeut
    un modèle XGBoost pour UNE ville — un modèle distinct par ville (ORA-154)
    plutôt qu'un modèle combiné avec `ville` en feature : un run Lille en
    difficulté (peu de données, dérive de features) ne peut plus casser les
    prédictions Lyon, et le garde-fou de régression compare chaque ville à
    sa propre histoire plutôt qu'à un mélange de gammes de prix différentes."""
    ville_nom = resolve_ville_nom(ville_slug)

    # --- 1. CONFIGURATION ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, '..', 'data', 'master_immo_final.csv')
    models_dir = os.path.join(script_dir, '..', 'models')
    model_save_path = os.path.join(models_dir, f'price_predictor_{ville_slug}.pkl')
    metrics_log_path = os.path.join(models_dir, f'training_metrics_{ville_slug}.jsonl')

    os.makedirs(models_dir, exist_ok=True)

    print(f"🚀 Démarrage de l'entraînement ({ville_nom}, Mode : XGBoost Blindé)...")

    # --- 2. CHARGEMENT ---
    if not os.path.exists(data_path):
        print(f"❌ Erreur : Fichier introuvable {data_path}")
        exit()

    df_all = pd.read_csv(data_path)
    df = df_all[df_all['ville'] == ville_nom]
    if df.empty:
        raise SystemExit(
            f"❌ Aucune annonce pour la ville '{ville_nom}' dans {data_path} — "
            "rien à entraîner."
        )

    # CIBLE
    y = df['prix']

    # --- 3. NETTOYAGE AGRESSIF ---
    # On vire les colonnes d'identification pure. `ville` est retirée ici :
    # constante au sein d'un modèle par ville, elle n'apporterait aucune
    # information (one-hot à une seule catégorie, supprimée par
    # drop_first=True de toute façon) — contrairement à l'ancien modèle
    # combiné (ORA-71) où elle codait un effet prix par ville. `image`
    # (ORA-155) : URL de la photo, quasi unique par ligne, ne peut
    # structurellement pas généraliser.
    features_to_drop = [
        'id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'titre',
        'date', 'image', 'ville',
    ]
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
    X = X.apply(pd.to_numeric, errors='coerce')  # Force tout en nombre
    X = X.fillna(0)

    print(f"📊 Données prêtes ({ville_nom}) : {X.shape[0]} annonces x {X.shape[1]} critères.")

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

    print("\n" + "=" * 40)
    print(f"🏆 RÉSULTATS XGBOOST — {ville_nom}")
    print("=" * 40)
    print(f"💰 Marge d'erreur moyenne : ± {mae:.2f} €")
    print(f"📈 Précision (R²)       : {r2:.2f} / 1.0")

    # --- 8. IMPORTANCE DES CRITÈRES ---
    importances = pd.DataFrame({
        'Feature': X.columns,
        'Importance': model.feature_importances_
    }).sort_values(by='Importance', ascending=False)

    print("\n🔍 Top 12 des critères décisifs :")
    print(importances.head(12).to_string(index=False))

    # --- 9. GARDE-FOU DE PROMOTION (ORA-34) ---
    # Un ré-entraînement automatique (DAG Airflow) ne doit jamais dégrader
    # silencieusement le modèle servi en production. On lit les métriques du
    # modèle ACTUELLEMENT actif POUR CETTE VILLE (avant tout écrasement) et
    # on compare à celles du nouveau modèle : chaque ville est comparée à sa
    # propre histoire, jamais à celle d'une autre (ORA-154 — comparer un
    # modèle combiné Lyon+Lille à un historique Lyon seul rendait le R² non
    # comparable, gonflant mécaniquement la variance du jeu de test).
    new_metrics = {'mae': float(mae), 'r2': float(r2)}
    previous_metrics, previous_version = load_active_model_metadata(model_save_path)
    promote, regression_reasons = decide_promotion(new_metrics, previous_metrics)

    # --- 10. SAUVEGARDE ---
    # Sérialisé en mémoire d'abord pour pouvoir hasher le binaire exact écrit sur
    # disque (ORA-31 : identifie chaque modèle entraîné par un hash de version).
    model_buffer = io.BytesIO()
    joblib.dump(model, model_buffer)
    model_bytes = model_buffer.getvalue()
    model_version = hashlib.sha256(model_bytes).hexdigest()[:12]

    # Le candidat est toujours archivé sous sa version (audit/rejeu possible), qu'il
    # soit promu ou non — mais il ne remplace le modèle actif (`model_save_path`)
    # que s'il ne régresse pas.
    versioned_path = archive_model_version(model_save_path, model_bytes, model_version)
    print(f"🗂️  Version archivée : {versioned_path} — voir rollback_model.py pour y revenir sans réentraîner.")

    if promote:
        with open(model_save_path, 'wb') as f:
            f.write(model_bytes)
        print(f"\n💾 Modèle {ville_nom} promu comme actif : {model_save_path} (version {model_version})")
    else:
        print(f"\n🚫 Modèle {ville_nom} {model_version} REJETÉ : régression détectée vs le modèle actif ({previous_version}) :")
        for reason in regression_reasons:
            print(f"   - {reason}")
        if previous_version:
            rollback_to(previous_version, model_save_path)
            print(f"↩️  Rollback déclenché : modèle {ville_nom} actif reconfirmé à la version {previous_version}.")
        else:
            print(f"⚠️  Aucun modèle {ville_nom} précédent connu : le modèle actif reste inchangé (non écrasé).")

    # --- 11. VERSIONING DES DONNÉES (ORA-28) ET MÉTADONNÉES DU MODÈLE (ORA-31) ---
    # Trace quelle version de master_immo_final.csv a servi à entraîner ce modèle,
    # pour pouvoir reproduire un ancien modèle à partir de son snapshot. Les
    # métadonnées du modèle ACTIF ne sont mises à jour que si le candidat est promu
    # (sinon `rollback_to` ci-dessus les a déjà reconfirmées pour l'ancienne version).
    # Snapshot du fichier COMPLET (toutes villes) : c'est la même source pour
    # chaque entraînement par ville, filtrée en mémoire à l'étape 2 — pas de
    # fichier par ville distinct à versionner séparément.
    snapshots_dir = os.path.join(script_dir, '..', 'data', 'snapshots')
    data_snapshot_sha256 = snapshot_dataset(data_path, snapshots_dir)
    data_snapshot_file = f"master_immo_final_{data_snapshot_sha256[:12]}.csv"

    if promote:
        meta_path = record_model_metadata(
            model_save_path,
            data_snapshot_sha256=data_snapshot_sha256,
            data_snapshot_file=data_snapshot_file,
            metrics=new_metrics,
            model_version=model_version,
            hyperparameters=hyperparameters,
        )
        print(f"📌 Snapshot des données : {data_snapshot_file} ({data_snapshot_sha256[:12]}...)")
        print(f"📎 Métadonnées du modèle : {meta_path}")

    # --- 12. PERSISTANCE DES MÉTRIQUES (historique comparable d'un run à l'autre) ---
    metrics_entry = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "ville": ville_nom,
        "mae": round(float(mae), 2),
        "r2": round(float(r2), 4),
        "dataset_size": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "model_version": model_version,
        "promoted": promote,
    }
    with open(metrics_log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(metrics_entry, ensure_ascii=False) + "\n")
    print(f"📈 Métriques ajoutées à l'historique : {metrics_log_path}")

    # --- 13. ÉCHEC EXPLICITE POUR AIRFLOW EN CAS DE RÉGRESSION (ORA-34) ---
    # Code de sortie non nul => la tâche BashOperator `train_model_<ville>` du DAG
    # échoue (et est retentée selon `default_args`), ce qui empêche ce run-ci de
    # laisser croire à un déploiement réussi pour cette ville. Les autres villes
    # du même DAG (tâches indépendantes) ne sont pas affectées par cet échec.
    if not promote:
        raise SystemExit(
            f"❌ Entraînement {ville_nom} rejeté (régression détectée) : le modèle actif "
            f"reste la version {previous_version or 'inconnue'}."
        )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Entraîne le modèle XGBoost de prédiction de prix pour une ville.")
    parser.add_argument('--ville', default='lyon', help="Slug de la ville (cf. scraping_config.json), ex: lyon, lille.")
    args = parser.parse_args()

    train(args.ville)
