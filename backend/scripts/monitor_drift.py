import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
from scipy.stats import ks_2samp

# Mêmes colonnes exclues que train_model.py (identifiants, texte libre, cible,
# `prix_m2` dérivé du prix) : on compare la dérive sur l'espace de features
# réellement vu par le modèle, pas sur des colonnes qu'il ignore.
FEATURES_TO_DROP = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'ville', 'titre', 'date']
TARGET_COLUMN = 'prix'

# Statistique D du test de Kolmogorov-Smirnov au-delà de laquelle on considère
# un vrai décalage de distribution. On se base sur la taille d'effet (D), pas
# uniquement la p-value : avec ~1000+ lignes, la p-value devient quasi toujours
# significative même pour un écart négligeable en pratique.
KS_DRIFT_THRESHOLD = 0.15

# Référence "glissante" : on compare aux données d'il y a N runs de snapshot,
# pas au tout premier snapshot du projet — sinon, le marché immobilier évoluant
# naturellement sur plusieurs mois, la comparaison finirait par toujours
# signaler une dérive de façon permanente (non actionnable, cf. le même
# raisonnement pour le canari Playwright sur PAP/SeLoger).
DRIFT_WINDOW_SNAPSHOTS = 7


def _numeric_feature_columns(df):
    cols = df.drop(columns=FEATURES_TO_DROP, errors='ignore')
    cols = cols.drop(columns=[c for c in cols.columns if c.startswith('nb_')], errors='ignore')
    return list(cols.select_dtypes(include='number').columns)


def _ks_result(reference_series, current_series, feature_name, ks_threshold):
    ref_vals = reference_series.dropna()
    cur_vals = current_series.dropna()
    if len(ref_vals) < 2 or len(cur_vals) < 2:
        return None
    stat, pvalue = ks_2samp(ref_vals, cur_vals)
    return {
        'feature': feature_name,
        'ks_statistic': round(float(stat), 4),
        'p_value': round(float(pvalue), 6),
        'drifted': bool(stat > ks_threshold),
    }


def compute_drift(reference_df, current_df, ks_threshold=KS_DRIFT_THRESHOLD):
    """Compare chaque feature numérique du modèle (et la cible `prix`, en proxy de
    dérive des prédictions en l'absence de journal de prédictions live) entre
    `reference_df` et `current_df` via un test de Kolmogorov-Smirnov à deux
    échantillons.

    Renvoie (feature_results: list[dict], target_drift: dict | None) — `target_drift`
    vaut None si la colonne `prix` est absente de l'un des deux jeux de données.
    """
    feature_cols = [c for c in _numeric_feature_columns(reference_df) if c in current_df.columns]
    results = []
    for col in feature_cols:
        result = _ks_result(reference_df[col], current_df[col], col, ks_threshold)
        if result is not None:
            results.append(result)

    target_drift = None
    if TARGET_COLUMN in reference_df.columns and TARGET_COLUMN in current_df.columns:
        target_drift = _ks_result(reference_df[TARGET_COLUMN], current_df[TARGET_COLUMN], TARGET_COLUMN, ks_threshold)

    return results, target_drift


def select_reference_snapshot(manifest_df, window=DRIFT_WINDOW_SNAPSHOTS):
    """Choisit la ligne du manifest à utiliser comme référence : celle d'il y a
    `window` runs, avec repli sur le plus ancien snapshot disponible s'il y a
    moins de `window` runs d'historique. Renvoie None si moins de 2 snapshots
    existent au total (pas assez d'historique pour comparer quoi que ce soit).
    """
    if len(manifest_df) < 2:
        return None
    idx = max(0, len(manifest_df) - 1 - window)
    return manifest_df.iloc[idx]


def build_drift_report(reference_df, current_df, *, reference_row, ks_threshold=KS_DRIFT_THRESHOLD):
    feature_results, target_drift = compute_drift(reference_df, current_df, ks_threshold=ks_threshold)
    any_drift = any(r['drifted'] for r in feature_results) or bool(target_drift and target_drift['drifted'])

    return {
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'status': 'drift_detected' if any_drift else 'ok',
        'reference_snapshot': reference_row['snapshot_file'],
        'reference_snapshot_timestamp': reference_row['timestamp'],
        'reference_row_count': int(reference_row['row_count']),
        'current_row_count': len(current_df),
        'ks_drift_threshold': ks_threshold,
        'features': feature_results,
        'target_drift': target_drift,
        'any_drift_detected': any_drift,
    }


def _write_report(report, latest_report_path, history_path):
    with open(latest_report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(history_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(report, ensure_ascii=False) + '\n')


def run(data_path, snapshots_dir, reports_dir, window=DRIFT_WINDOW_SNAPSHOTS):
    """Point d'entrée : compare `data_path` (données actuelles) au snapshot de
    référence choisi dans `snapshots_dir/manifest.csv`, écrit le rapport dans
    `reports_dir` (dernier état + historique append-only), et renvoie un code de
    sortie non nul si une dérive significative a été détectée (pour l'alerte CI).
    """
    os.makedirs(reports_dir, exist_ok=True)
    latest_report_path = os.path.join(reports_dir, 'drift_report_latest.json')
    history_path = os.path.join(reports_dir, 'drift_history.jsonl')

    manifest_path = os.path.join(snapshots_dir, 'manifest.csv')
    if not os.path.exists(manifest_path):
        report = {
            'checked_at': datetime.now(timezone.utc).isoformat(),
            'status': 'insufficient_history',
            'message': "Aucun manifest de snapshot trouvé — lancez d'abord un entraînement (train_model.py).",
        }
        _write_report(report, latest_report_path, history_path)
        print(report['message'])
        return 0

    manifest = pd.read_csv(manifest_path, encoding='utf-8-sig')
    reference_row = select_reference_snapshot(manifest, window=window)
    if reference_row is None:
        report = {
            'checked_at': datetime.now(timezone.utc).isoformat(),
            'status': 'insufficient_history',
            'message': "Un seul snapshot de données enregistré à ce jour : pas assez d'historique pour détecter une dérive.",
        }
        _write_report(report, latest_report_path, history_path)
        print(report['message'])
        return 0

    reference_path = os.path.join(snapshots_dir, reference_row['snapshot_file'])
    reference_df = pd.read_csv(reference_path)
    current_df = pd.read_csv(data_path)

    report = build_drift_report(reference_df, current_df, reference_row=reference_row)
    _write_report(report, latest_report_path, history_path)

    if report['any_drift_detected']:
        drifted = [r['feature'] for r in report['features'] if r['drifted']]
        if report['target_drift'] and report['target_drift']['drifted']:
            drifted.append(report['target_drift']['feature'])
        print(f"⚠️ Dérive détectée sur : {', '.join(drifted)}")
        return 1

    print("✅ Aucune dérive significative détectée.")
    return 0


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exit_code = run(
        data_path=os.path.join(script_dir, '..', 'data', 'master_immo_final.csv'),
        snapshots_dir=os.path.join(script_dir, '..', 'data', 'snapshots'),
        reports_dir=os.path.join(script_dir, '..', 'data', 'drift_reports'),
    )
    sys.exit(exit_code)
