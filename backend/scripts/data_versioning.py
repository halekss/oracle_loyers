import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone


def _sha256_of_file(path, chunk_size=65536):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_dataset(csv_path, snapshots_dir):
    """Archive un instantané content-addressé de `csv_path` dans `snapshots_dir` et
    enregistre son empreinte dans `snapshots_dir/manifest.csv`, pour pouvoir retrouver
    et rejouer exactement les données ayant servi à un entraînement donné (ORA-28).

    Un re-run sur des données identiques ne duplique pas le fichier (même sha256 =>
    snapshot déjà présent) mais ajoute quand même une ligne au manifeste pour tracer
    quand ce jeu de données a été (ré)utilisé.

    Renvoie le sha256 complet du contenu de `csv_path`.
    """
    os.makedirs(snapshots_dir, exist_ok=True)

    file_hash = _sha256_of_file(csv_path)
    snapshot_filename = f"master_immo_final_{file_hash[:12]}.csv"
    snapshot_path = os.path.join(snapshots_dir, snapshot_filename)

    if not os.path.exists(snapshot_path):
        shutil.copy2(csv_path, snapshot_path)

    with open(csv_path, encoding='utf-8-sig') as f:
        row_count = sum(1 for _ in f) - 1  # -1 pour l'en-tête

    manifest_path = os.path.join(snapshots_dir, "manifest.csv")
    manifest_exists = os.path.exists(manifest_path)
    with open(manifest_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not manifest_exists:
            writer.writerow(['timestamp', 'sha256', 'snapshot_file', 'row_count'])
        writer.writerow([datetime.now(timezone.utc).isoformat(), file_hash, snapshot_filename, row_count])

    return file_hash


def record_model_metadata(
    model_path,
    *,
    data_snapshot_sha256,
    data_snapshot_file,
    metrics,
    model_version=None,
    hyperparameters=None,
):
    """Écrit `<model_path>.meta.json`, référençant explicitement la version des données
    utilisée pour entraîner ce modèle (ORA-28) ainsi que ses métriques, pour pouvoir
    reproduire un ancien modèle à partir de son snapshot de données.

    `model_version` (hash du binaire du modèle) et `hyperparameters` sont optionnels
    (ORA-31) : un appelant qui ne les fournit pas obtient le même comportement qu'avant.
    """
    meta_path = f"{model_path}.meta.json"
    metadata = {
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'data_snapshot_sha256': data_snapshot_sha256,
        'data_snapshot_file': data_snapshot_file,
        'metrics': metrics,
    }
    if model_version is not None:
        metadata['model_version'] = model_version
    if hyperparameters is not None:
        metadata['hyperparameters'] = hyperparameters
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    return meta_path


def archive_model_version(model_path, model_bytes, model_version, versions_dir=None):
    """Conserve une copie du modèle sous un nom versionné (hash du binaire), pour
    pouvoir revenir à une version antérieure sans réentraîner (ORA-31, voir
    rollback_model.py). N'écrase pas une version déjà archivée (contenu identique
    => hash identique => fichier déjà présent).

    Renvoie le chemin du fichier versionné.
    """
    if versions_dir is None:
        versions_dir = os.path.join(os.path.dirname(model_path), 'versions')
    os.makedirs(versions_dir, exist_ok=True)

    name, ext = os.path.splitext(os.path.basename(model_path))
    versioned_path = os.path.join(versions_dir, f"{name}_{model_version}{ext}")

    if not os.path.exists(versioned_path):
        with open(versioned_path, 'wb') as f:
            f.write(model_bytes)

    return versioned_path
