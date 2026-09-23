"""
Revenir à une version antérieure du modèle price_predictor_<ville>.pkl sans
réentraîner (ORA-31). Chaque entraînement archive une copie versionnée
(hash du binaire) dans backend/models/versions/ ; ce script restaure
l'une d'elles comme modèle actif.

Usage :
    python rollback_model.py <model_version> --ville <slug>

`model_version` est le hash (12 caractères) affiché par train_model.py
au moment de l'entraînement, ou visible dans price_predictor_<ville>.pkl.meta.json
/ training_metrics_<ville>.jsonl / GET /api/health.
"""

import argparse
import json
import os
import shutil
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, '..', 'models')


def resolve_model_path(ville_slug):
    """price_predictor_<ville>.pkl pour le slug donné — un modèle distinct par
    ville (ORA-154)."""
    return os.path.join(MODELS_DIR, f'price_predictor_{ville_slug}.pkl')


def rollback_to(model_version, model_path, versions_dir=None):
    """Restaure `model_path` à la version archivée `model_version`.

    `versions_dir` suit la même convention que `data_versioning.archive_model_version`
    (par défaut : `versions/` à côté de `model_path`) — pas de paramètre
    séparé à synchroniser entre les deux."""
    if versions_dir is None:
        versions_dir = os.path.join(os.path.dirname(model_path), 'versions')

    name, ext = os.path.splitext(os.path.basename(model_path))
    versioned_path = os.path.join(versions_dir, f"{name}_{model_version}{ext}")
    if not os.path.exists(versioned_path):
        raise SystemExit(f"❌ Version introuvable : {versioned_path}")

    shutil.copyfile(versioned_path, model_path)

    meta_path = f"{model_path}.meta.json"
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
    parser.add_argument('--ville', default='lyon', help="Slug de la ville (ex: lyon, lille).")
    args = parser.parse_args()
    rollback_to(args.model_version, resolve_model_path(args.ville))
