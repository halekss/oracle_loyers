"""
Revenir à une version antérieure du modèle price_predictor.pkl sans
réentraîner (ORA-31). Chaque entraînement archive une copie versionnée
(hash du binaire) dans backend/models/versions/ ; ce script restaure
l'une d'elles comme modèle actif.

Usage :
    python rollback_model.py <model_version>

`model_version` est le hash (12 caractères) affiché par train_model.py
au moment de l'entraînement, ou visible dans price_predictor.pkl.meta.json
/ training_metrics.jsonl / GET /api/health.
"""

import argparse
import json
import os
import shutil
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, '..', 'models')
MODEL_PATH = os.path.join(MODELS_DIR, 'price_predictor.pkl')
VERSIONS_DIR = os.path.join(MODELS_DIR, 'versions')


def rollback_to(model_version):
    versioned_path = os.path.join(VERSIONS_DIR, f"price_predictor_{model_version}.pkl")
    if not os.path.exists(versioned_path):
        raise SystemExit(f"❌ Version introuvable : {versioned_path}")

    shutil.copyfile(versioned_path, MODEL_PATH)

    meta_path = f"{MODEL_PATH}.meta.json"
    metadata = {}
    if os.path.exists(meta_path):
        with open(meta_path, encoding='utf-8') as f:
            metadata = json.load(f)

    metadata['model_version'] = model_version
    metadata['rolled_back_at'] = datetime.now(timezone.utc).isoformat()

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"✅ Modèle actif restauré à la version {model_version} (depuis {versioned_path}).")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('model_version', help="Hash de version du modèle à restaurer (ex: a1b2c3d4e5f6)")
    args = parser.parse_args()
    rollback_to(args.model_version)
