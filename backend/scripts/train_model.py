import hashlib
import io
import json
import pandas as pd
import numpy as np
import os
import sys
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

# backend/services (outlier_detection) n'est pas sur sys.path par défaut quand
# ce script est lancé directement (`python train_model.py`, sys.path[0] =
# scripts/) — même garde que clean_immo.py/generate_map.py.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from services import outlier_detection  # noqa: E402 (après le sys.path.insert nécessaire)

# Vérification XGBoost
try:
    from xgboost import XGBRegressor
except ImportError:
    print("❌ Erreur : XGBoost n'est pas installé. (pip install xgboost)")
    exit()


def resolve_ville_nom(ville_slug):
    return load_declared_villes()[ville_slug]['nom']


# ponytail: seuil fixe ; sous ce nombre de lignes communes, R²/MAE trop bruités
# pour départager -> repli sur les métriques stockées de l'actif.
MIN_COMMON_TEST_ROWS = 20


def split_train_test(*arrays):
    """Split unique, partagé par l'entraînement et `active_training_urls` pour que
    les lignes d'entraînement d'un ancien modèle soient reconstituables."""
    return train_test_split(*arrays, test_size=0.2, random_state=42)


def _metrics(y_true, y_pred):
    return {'mae': float(mean_absolute_error(y_true, y_pred)), 'r2': float(r2_score(y_true, y_pred))}


def active_training_urls(snapshot_path, ville_nom):
    """URLs des annonces ayant servi à entraîner le modèle actif : même filtre ville
    et même split que `train`, rejoués sur le snapshot de ses métadonnées. L'url et
    non id_annonce : ce dernier est un numéro de ligne réattribué à chaque run."""
    df = pd.read_csv(snapshot_path)
    train_df, _ = split_train_test(df[df['ville'] == ville_nom])
    return set(train_df['url'])


def compare_on_common_test(candidate, X_test, y_test, test_urls, active_model_path,
                           active_train_urls, min_rows=MIN_COMMON_TEST_ROWS):
    """Évalue candidat ET modèle actif sur le même jeu : le test du candidat privé
    des annonces vues par l'actif à l'entraînement. Renvoie
    `(metriques_candidat, metriques_actif, n_lignes)`, ou None si l'actif est
    introuvable ou s'il reste moins de `min_rows` lignes."""
    if not os.path.exists(active_model_path):
        return None
    unseen = ~test_urls.isin(active_train_urls).to_numpy()
    if unseen.sum() < min_rows:
        return None
    X, y = X_test[unseen], y_test[unseen]
    active = joblib.load(active_model_path)
    # Dummies d'un autre run : colonnes absentes -> 0 (même règle que fillna(0)).
    X_active = X.reindex(columns=active.feature_names_in_, fill_value=0)
    return _metrics(y, candidate.predict(X)), _metrics(y, active.predict(X_active)), int(unseen.sum())


# ORA-181 : statuts d'archive exclus de l'entraînement — une annonce archivée
# 'inactive' (confirmée morte/retirée, cf. ORA-134) n'est pas un signal marché
# fiable ; 'active'/'a_verifier' restent valables (prix historique réel, juste
# plus ancien que le master, sorti par step_archive_hors_master).
ARCHIVE_EXCLUDED_STATUTS = {'inactive'}

HYPERPARAMETERS = {
    'n_estimators': 1500,
    'learning_rate': 0.01,
    'max_depth': 7,
    'subsample': 0.7,
    'colsample_bytree': 0.6,
    'random_state': 42,
}


def load_source_dataframe(ville_slug, source='master', data_dir=None):
    """Charge le jeu d'entraînement d'UNE ville depuis `source` (ORA-181) :

    - 'master' (comportement historique, inchangé) : master_immo_final.csv
      seul, filtré sur la ville.
    - 'master_archive' : ajoute backend/data/master_archive.csv (annonces
      sorties du master, cf. clean_immo.step_archive_hors_master) — plus de
      données, mais plus anciennes en moyenne.

    Points tranchés (voir description ORA-181) :
    - une annonce présente plusieurs fois dans l'archive (même url) ne garde
      que sa ligne la plus récente (`archive_le` le plus grand) ;
    - une url déjà dans le master garde sa version master (plus fraîche),
      même si elle apparaît aussi dans l'archive (ne devrait pas arriver vu
      step_archive_hors_master, mais pas garanti dans le temps) ;
    - les lignes d'archive au statut 'inactive' sont exclues
      (ARCHIVE_EXCLUDED_STATUTS ci-dessus).

    Exclut aussi les annonces suspectes (ORA-195, outlier_detection — même
    règle unique que partout ailleurs), quelle que soit `source` : un prix/m²
    ou une surface aberrante ne doit jamais entraîner le modèle.

    `data_dir` (optionnel, pour les tests) : dossier `data/` à utiliser au
    lieu de `backend/data/` réel."""
    ville_nom = resolve_ville_nom(ville_slug)
    data_dir = data_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    master_path = os.path.join(data_dir, 'master_immo_final.csv')
    df_master = pd.read_csv(master_path)
    df_master = df_master[df_master['ville'] == ville_nom]

    if source == 'master':
        result = df_master
    elif source == 'master_archive':
        archive_path = os.path.join(data_dir, 'master_archive.csv')
        if not os.path.exists(archive_path):
            result = df_master
        else:
            df_archive = pd.read_csv(archive_path)
            df_archive = df_archive[df_archive['ville'] == ville_nom]

            if 'statut' in df_archive.columns:
                df_archive = df_archive[~df_archive['statut'].isin(ARCHIVE_EXCLUDED_STATUTS)]

            if 'archive_le' in df_archive.columns:
                df_archive = df_archive.sort_values('archive_le').drop_duplicates(subset='url', keep='last')
            else:
                df_archive = df_archive.drop_duplicates(subset='url', keep='last')

            df_archive = df_archive[~df_archive['url'].isin(df_master['url'])]

            result = pd.concat([df_master, df_archive], ignore_index=True, sort=False)
    else:
        raise ValueError(f"source inconnue : {source!r} (attendu 'master' ou 'master_archive')")

    return outlier_detection.exclude_suspects(result)


def prepare_features_and_target(df):
    """Prétraitement partagé par `train()` et `compare_sources()` (ORA-181) :
    même nettoyage/encodage quelle que soit la source, pour une comparaison
    MAE/R² qui isole vraiment l'effet des données, pas celui du pipeline."""
    y = df['prix']

    features_to_drop = [
        'id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'titre',
        'date', 'image', 'ville', 'source_localisation', 'precision_localisation', 'description_detail',
    ]
    X = df.drop(columns=features_to_drop, errors='ignore')

    cols_nb = [c for c in X.columns if c.startswith('nb_')]
    X = X.drop(columns=cols_nb, errors='ignore')

    cols_text = X.select_dtypes(include=['object']).columns
    if len(cols_text) > 0:
        X = pd.get_dummies(X, columns=cols_text, drop_first=True)

    X = X.apply(pd.to_numeric, errors='coerce').fillna(0)
    return X, y


def compare_sources(ville_slug, data_dir=None):
    """ORA-181 : compare MAE/R² 'master' vs 'master_archive' sans rien
    entraîner "pour de vrai" — aucune sauvegarde, promotion, ni mise à jour
    des métadonnées/snapshots. Sert à décider s'il faut un jour changer le
    défaut d'entraînement, pas à le changer directement.

    Même split/hyperparamètres que `train()` (HYPERPARAMETERS, random_state
    42) pour une comparaison qui isole l'effet des données."""
    ville_nom = resolve_ville_nom(ville_slug)
    results = {}
    for source in ('master', 'master_archive'):
        df = load_source_dataframe(ville_slug, source=source, data_dir=data_dir)
        X, y = prepare_features_and_target(df)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = XGBRegressor(n_jobs=-1, **HYPERPARAMETERS)
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        results[source] = {
            'mae': float(mean_absolute_error(y_test, predictions)),
            'r2': float(r2_score(y_test, predictions)),
            'dataset_size': int(X.shape[0]),
        }

    print(f"\n{'=' * 50}")
    print(f"📊 COMPARAISON DES SOURCES D'ENTRAÎNEMENT — {ville_nom}")
    print('=' * 50)
    for source, metrics in results.items():
        print(f"  {source:16s} : {metrics['dataset_size']:4d} annonces · MAE ± {metrics['mae']:.2f} € · R² {metrics['r2']:.3f}")

    return results


def train(ville_slug, source='master'):
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

    print(f"🚀 Démarrage de l'entraînement ({ville_nom}, source={source}, Mode : XGBoost Blindé)...")

    # --- 2. CHARGEMENT ---
    if not os.path.exists(data_path):
        print(f"❌ Erreur : Fichier introuvable {data_path}")
        exit()

    # ORA-181 : `source='master'` (défaut, comportement historique inchangé)
    # n'entraîne que sur les annonces du dernier run ; `source='master_archive'`
    # ajoute master_archive.csv (annonces sorties du master, cf.
    # clean_immo.step_archive_hors_master) — cf. load_source_dataframe pour les
    # règles de dédoublonnage/exclusion. Le snapshot versionné (ORA-28, étape 11
    # ci-dessous) reste celui du master seul quelle que soit `source` : c'est
    # le seul fichier qu'on a besoin de reproduire pour rejouer un ancien
    # modèle (l'archive n'est pas versionnée par snapshot).
    df = load_source_dataframe(ville_slug, source=source)
    if df.empty:
        raise SystemExit(
            f"❌ Aucune annonce pour la ville '{ville_nom}' (source={source}) — "
            "rien à entraîner."
        )

    X, y = prepare_features_and_target(df)

    print(f"📊 Données prêtes ({ville_nom}) : {X.shape[0]} annonces x {X.shape[1]} critères.")

    # --- 5. TRAIN / TEST ---
    X_train, X_test, y_train, y_test = split_train_test(X, y)

    # --- 6. ENTRAÎNEMENT XGBOOST ---
    hyperparameters = HYPERPARAMETERS
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
    #
    # Les métriques stockées de l'actif viennent du split de SON dataset : les
    # comparer à celles du candidat (autre dataset) rejetait des modèles à MAE
    # équivalente. On ré-évalue donc les deux sur le même jeu, sans les lignes
    # d'entraînement de l'actif ; repli sur les métriques stockées si impossible.
    new_metrics = {'mae': float(mae), 'r2': float(r2)}
    previous_metrics, previous_version = load_active_model_metadata(model_save_path)
    comparaison = None
    active_meta_path = f"{model_save_path}.meta.json"
    if previous_metrics and os.path.exists(active_meta_path):
        with open(active_meta_path, encoding='utf-8') as f:
            snapshot_file = json.load(f).get('data_snapshot_file')
        snapshot_path = os.path.join(script_dir, '..', 'data', 'snapshots', snapshot_file or '')
        if snapshot_file and os.path.exists(snapshot_path):
            comparaison = compare_on_common_test(
                model, X_test, y_test, df.loc[X_test.index, 'url'], model_save_path,
                active_training_urls(snapshot_path, ville_nom),
            )
    if comparaison:
        candidate_common, active_common, n_common = comparaison
        print(f"⚖️  Jeu de test commun ({n_common} annonces jamais vues par l'actif) : "
              f"candidat MAE {candidate_common['mae']:.2f} € / R² {candidate_common['r2']:.3f} — "
              f"actif MAE {active_common['mae']:.2f} € / R² {active_common['r2']:.3f}")
        promote, regression_reasons = decide_promotion(candidate_common, active_common)
    else:
        if previous_metrics:
            print("⚠️  Comparaison sur jeu commun impossible (snapshot/modèle actif absent ou "
                  "trop peu d'annonces inédites) : repli sur les métriques stockées de l'actif.")
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
        "source": source,
        "mae": round(float(mae), 2),
        "r2": round(float(r2), 4),
        "dataset_size": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "model_version": model_version,
        "promoted": promote,
    }
    if comparaison:
        metrics_entry["jeu_commun"] = {
            "n": n_common,
            "candidat": {k: round(v, 4) for k, v in candidate_common.items()},
            "actif": {k: round(v, 4) for k, v in active_common.items()},
        }
    with open(metrics_log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(metrics_entry, ensure_ascii=False) + "\n")
    print(f"📈 Métriques ajoutées à l'historique : {metrics_log_path}")

    # --- 13. ÉCHEC EXPLICITE POUR AIRFLOW EN CAS DE RÉGRESSION (ORA-34) ---
    # Code de sortie non nul => la tâche BashOperator `train_model_<ville>` du DAG
    # échoue (sans réessai : un rejet est déterministe), ce qui empêche ce run-ci de
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
    parser.add_argument(
        '--source', choices=['master', 'master_archive'], default='master',
        help="ORA-181 : jeu d'entraînement — 'master' (défaut, comportement historique) ou "
             "'master_archive' (ajoute les annonces archivées, plus de données mais plus anciennes).",
    )
    parser.add_argument(
        '--compare', action='store_true',
        help="ORA-181 : compare MAE/R² master vs master_archive sans rien entraîner/sauvegarder "
             "pour de vrai (ignore --source).",
    )
    args = parser.parse_args()

    if args.compare:
        compare_sources(args.ville)
    else:
        train(args.ville, source=args.source)
