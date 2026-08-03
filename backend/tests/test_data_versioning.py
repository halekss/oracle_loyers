import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from data_versioning import archive_model_version, record_model_metadata, snapshot_dataset


class SnapshotDatasetTest(unittest.TestCase):
    def test_creates_snapshot_file_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "master_immo_final.csv")
            with open(csv_path, "w", encoding="utf-8-sig") as f:
                f.write("prix,surface\n800,45\n1200,60\n")

            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            file_hash = snapshot_dataset(csv_path, snapshots_dir)

            snapshot_files = [f for f in os.listdir(snapshots_dir) if f != "manifest.csv"]
            self.assertEqual(len(snapshot_files), 1)
            self.assertIn(file_hash[:12], snapshot_files[0])

            with open(os.path.join(snapshots_dir, "manifest.csv"), encoding="utf-8-sig") as f:
                lines = f.read().strip().splitlines()
            self.assertEqual(lines[0], "timestamp,sha256,snapshot_file,row_count")
            self.assertIn(file_hash, lines[1])
            self.assertIn("2", lines[1])  # row_count

    def test_identical_content_does_not_duplicate_snapshot_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "master_immo_final.csv")
            with open(csv_path, "w", encoding="utf-8-sig") as f:
                f.write("prix,surface\n800,45\n")

            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            hash_1 = snapshot_dataset(csv_path, snapshots_dir)
            hash_2 = snapshot_dataset(csv_path, snapshots_dir)

            self.assertEqual(hash_1, hash_2)
            snapshot_files = [f for f in os.listdir(snapshots_dir) if f != "manifest.csv"]
            self.assertEqual(len(snapshot_files), 1)

            with open(os.path.join(snapshots_dir, "manifest.csv"), encoding="utf-8-sig") as f:
                lines = f.read().strip().splitlines()
            # 1 en-tête + 2 lignes (une par appel), même si le fichier n'est pas dupliqué
            self.assertEqual(len(lines), 3)

    def test_different_content_creates_a_second_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = os.path.join(tmp_dir, "master_immo_final.csv")
            snapshots_dir = os.path.join(tmp_dir, "snapshots")

            with open(csv_path, "w", encoding="utf-8-sig") as f:
                f.write("prix,surface\n800,45\n")
            hash_1 = snapshot_dataset(csv_path, snapshots_dir)

            with open(csv_path, "w", encoding="utf-8-sig") as f:
                f.write("prix,surface\n900,50\n")
            hash_2 = snapshot_dataset(csv_path, snapshots_dir)

            self.assertNotEqual(hash_1, hash_2)
            snapshot_files = [f for f in os.listdir(snapshots_dir) if f != "manifest.csv"]
            self.assertEqual(len(snapshot_files), 2)


class RecordModelMetadataTest(unittest.TestCase):
    def test_writes_sidecar_json_referencing_data_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = os.path.join(tmp_dir, "price_predictor.pkl")

            meta_path = record_model_metadata(
                model_path,
                data_snapshot_sha256="abc123",
                data_snapshot_file="master_immo_final_abc123.csv",
                metrics={"mae": 42.5, "r2": 0.87},
            )

            self.assertEqual(meta_path, f"{model_path}.meta.json")
            with open(meta_path, encoding="utf-8") as f:
                metadata = json.load(f)

            self.assertEqual(metadata["data_snapshot_sha256"], "abc123")
            self.assertEqual(metadata["data_snapshot_file"], "master_immo_final_abc123.csv")
            self.assertEqual(metadata["metrics"]["mae"], 42.5)
            self.assertIn("trained_at", metadata)
            self.assertNotIn("model_version", metadata)
            self.assertNotIn("hyperparameters", metadata)

    def test_includes_model_version_and_hyperparameters_when_provided(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = os.path.join(tmp_dir, "price_predictor.pkl")

            meta_path = record_model_metadata(
                model_path,
                data_snapshot_sha256="abc123",
                data_snapshot_file="master_immo_final_abc123.csv",
                metrics={"mae": 42.5, "r2": 0.87},
                model_version="deadbeef1234",
                hyperparameters={"n_estimators": 1500, "random_state": 42},
            )

            with open(meta_path, encoding="utf-8") as f:
                metadata = json.load(f)

            self.assertEqual(metadata["model_version"], "deadbeef1234")
            self.assertEqual(metadata["hyperparameters"]["n_estimators"], 1500)


class ArchiveModelVersionTest(unittest.TestCase):
    def test_archives_a_versioned_copy_of_the_model(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = os.path.join(tmp_dir, "price_predictor.pkl")
            model_bytes = b"fake-model-bytes"

            versioned_path = archive_model_version(model_path, model_bytes, "abc123def456")

            self.assertTrue(os.path.exists(versioned_path))
            self.assertIn("abc123def456", versioned_path)
            with open(versioned_path, "rb") as f:
                self.assertEqual(f.read(), model_bytes)

    def test_does_not_duplicate_an_already_archived_version(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = os.path.join(tmp_dir, "price_predictor.pkl")
            versions_dir = os.path.join(tmp_dir, "versions")

            path_1 = archive_model_version(model_path, b"v1", "hash1", versions_dir=versions_dir)
            # Une archive identique (même hash) ne doit pas être ré-écrite avec un
            # contenu différent, même si on lui passe (par erreur) d'autres octets.
            path_2 = archive_model_version(model_path, b"different-bytes", "hash1", versions_dir=versions_dir)

            self.assertEqual(path_1, path_2)
            with open(path_1, "rb") as f:
                self.assertEqual(f.read(), b"v1")


if __name__ == "__main__":
    unittest.main()
