import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import rollback_model
from data_versioning import decide_promotion, load_active_model_metadata, record_model_metadata


class DecidePromotionTest(unittest.TestCase):
    """ORA-34 : un ré-entraînement automatique (DAG Airflow quotidien) ne doit
    jamais remplacer silencieusement le modèle actif par un candidat qui régresse."""

    def test_first_training_with_no_previous_model_is_always_promoted(self):
        promote, reasons = decide_promotion({"mae": 500, "r2": 0.1}, previous_metrics=None)
        self.assertTrue(promote)
        self.assertEqual(reasons, [])

    def test_better_or_equivalent_metrics_are_promoted(self):
        previous = {"mae": 200.0, "r2": 0.75}
        new = {"mae": 190.0, "r2": 0.77}
        promote, reasons = decide_promotion(new, previous)
        self.assertTrue(promote)
        self.assertEqual(reasons, [])

    def test_small_fluctuations_within_tolerance_are_not_a_regression(self):
        previous = {"mae": 200.0, "r2": 0.75}
        new = {"mae": 205.0, "r2": 0.72}  # +2.5% MAE, -0.03 R² : dans la marge tolérée
        promote, reasons = decide_promotion(new, previous)
        self.assertTrue(promote)
        self.assertEqual(reasons, [])

    def test_mae_regression_beyond_tolerance_is_rejected(self):
        previous = {"mae": 200.0, "r2": 0.75}
        new = {"mae": 500.0, "r2": 0.75}  # +150% de MAE
        promote, reasons = decide_promotion(new, previous)
        self.assertFalse(promote)
        self.assertTrue(any("MAE" in r for r in reasons))

    def test_r2_regression_beyond_tolerance_is_rejected(self):
        previous = {"mae": 200.0, "r2": 0.75}
        new = {"mae": 200.0, "r2": 0.40}
        promote, reasons = decide_promotion(new, previous)
        self.assertFalse(promote)
        self.assertTrue(any("R²" in r for r in reasons))

    def test_custom_tolerances_are_respected(self):
        previous = {"mae": 200.0, "r2": 0.75}
        new = {"mae": 210.0, "r2": 0.75}  # +5% de MAE
        promote, _ = decide_promotion(new, previous, mae_tolerance=0.10)
        self.assertTrue(promote)
        promote, reasons = decide_promotion(new, previous, mae_tolerance=0.01)
        self.assertFalse(promote)
        self.assertTrue(reasons)


class LoadActiveModelMetadataTest(unittest.TestCase):
    def test_returns_none_when_no_model_has_ever_been_trained(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = os.path.join(tmp_dir, "price_predictor.pkl")
            metrics, version = load_active_model_metadata(model_path)
            self.assertIsNone(metrics)
            self.assertIsNone(version)

    def test_reads_metrics_and_version_from_existing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = os.path.join(tmp_dir, "price_predictor.pkl")
            record_model_metadata(
                model_path,
                data_snapshot_sha256="abc",
                data_snapshot_file="f.csv",
                metrics={"mae": 150.0, "r2": 0.8},
                model_version="deadbeef1234",
            )
            metrics, version = load_active_model_metadata(model_path)
            self.assertEqual(metrics, {"mae": 150.0, "r2": 0.8})
            self.assertEqual(version, "deadbeef1234")


class PromotionGuardTriggersRollbackTest(unittest.TestCase):
    """Reproduit le flux de décision de train_model.py au niveau des fonctions
    qu'il appelle : un candidat en régression ne doit jamais remplacer le modèle
    actif, et le rollback existant (ORA-31) doit explicitement reconfirmer la
    version précédente comme active (ORA-34)."""

    def test_worse_candidate_is_rejected_and_rollback_is_triggered(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            models_dir = tmp_dir
            model_path = os.path.join(models_dir, "price_predictor.pkl")
            versions_dir = os.path.join(models_dir, "versions")
            os.makedirs(versions_dir)

            # Modèle actif courant : bon (mae=150, r2=0.8), déjà archivé sous sa version
            # (comme le fait train_model.py à chaque entraînement promu).
            active_bytes = b"contenu-modele-actif-actuel"
            with open(model_path, "wb") as f:
                f.write(active_bytes)
            with open(os.path.join(versions_dir, "price_predictor_goodhash01.pkl"), "wb") as f:
                f.write(active_bytes)
            record_model_metadata(
                model_path,
                data_snapshot_sha256="snap1",
                data_snapshot_file="f1.csv",
                metrics={"mae": 150.0, "r2": 0.8},
                model_version="goodhash01",
            )

            # Nouveau candidat entraîné : nettement pire.
            previous_metrics, previous_version = load_active_model_metadata(model_path)
            new_metrics = {"mae": 400.0, "r2": 0.3}
            promote, reasons = decide_promotion(new_metrics, previous_metrics)

            self.assertFalse(promote)
            self.assertTrue(reasons)

            # train_model.py n'écrit PAS le candidat sur le modèle actif quand
            # `promote` est False (on ne touche donc pas model_path ici), puis
            # déclenche le rollback existant pour reconfirmer la version active.
            with patch.object(rollback_model, "MODEL_PATH", model_path), \
                    patch.object(rollback_model, "VERSIONS_DIR", versions_dir):
                rollback_model.rollback_to(previous_version)

            with open(model_path, "rb") as f:
                self.assertEqual(f.read(), active_bytes)  # toujours l'ancien modèle, jamais le candidat

            with open(f"{model_path}.meta.json", encoding="utf-8") as f:
                metadata = json.load(f)
            self.assertEqual(metadata["model_version"], "goodhash01")
            self.assertIn("rolled_back_at", metadata)

    def test_better_candidate_is_promoted_without_rollback(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = os.path.join(tmp_dir, "price_predictor.pkl")
            record_model_metadata(
                model_path,
                data_snapshot_sha256="snap1",
                data_snapshot_file="f1.csv",
                metrics={"mae": 150.0, "r2": 0.8},
                model_version="goodhash01",
            )

            previous_metrics, previous_version = load_active_model_metadata(model_path)
            new_metrics = {"mae": 120.0, "r2": 0.85}
            promote, reasons = decide_promotion(new_metrics, previous_metrics)

            self.assertTrue(promote)
            self.assertEqual(reasons, [])


if __name__ == "__main__":
    unittest.main()
