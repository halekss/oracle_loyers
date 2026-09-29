import json
import os
import sys
import tempfile
import unittest

import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import rollback_model
import train_model
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
            rollback_model.rollback_to(previous_version, model_path)

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


class CommonTestSetComparisonTest(unittest.TestCase):
    """Le garde-fou compare actif et candidat sur le MÊME jeu de test, privé des
    annonces sur lesquelles l'actif a été entraîné (sinon il serait jugé sur des
    lignes déjà vues). Avant : chaque R² venait du split de son propre dataset,
    d'où des rejets pour une MAE quasi identique (Lille, 28/09)."""

    @staticmethod
    def _frame(n, offset=0):
        import numpy as np
        rng = np.random.default_rng(offset)
        a, b = rng.uniform(0, 10, n), rng.uniform(0, 10, n)
        return pd.DataFrame({
            # id_annonce = numéro de ligne, réattribué à chaque run : seule l'url
            # identifie une annonce d'un dataset à l'autre.
            "id_annonce": range(n),
            "url": [f"https://ex/{offset + i}" for i in range(n)],
            "ville": "Lyon", "a": a, "b": b, "prix": 100 * a + 20 * b,
        })

    def test_active_training_urls_reproduce_the_training_split_for_the_ville(self):
        df = self._frame(50)
        other = self._frame(10, offset=1000).assign(ville="Lille")
        with tempfile.TemporaryDirectory() as tmp_dir:
            snap = os.path.join(tmp_dir, "snap.csv")
            pd.concat([other, df]).to_csv(snap, index=False)
            urls = train_model.active_training_urls(snap, "Lyon")
        expected, _ = train_test_split(df, test_size=0.2, random_state=42)
        self.assertEqual(urls, set(expected["url"]))

    def test_both_models_are_scored_on_unseen_rows_only_with_aligned_columns(self):
        train_df, test_df = self._frame(80), self._frame(40, offset=500)
        active = LinearRegression().fit(train_df[["a", "b"]], train_df["prix"])
        # Candidat avec un jeu de colonnes différent (dummies d'un autre run).
        X_test = test_df[["a"]].assign(c=1.0)
        candidate = LinearRegression().fit(X_test, test_df["prix"])
        # 10 lignes du test ont servi à entraîner l'actif : exclues.
        seen = set(test_df["url"][:10])
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "active.pkl")
            joblib.dump(active, path)
            result = train_model.compare_on_common_test(
                candidate, X_test, test_df["prix"], test_df["url"], path, seen, min_rows=20,
            )
        new_metrics, active_metrics, n_rows = result
        self.assertEqual(n_rows, 30)
        unseen = test_df.iloc[10:]
        # b absent du jeu candidat => rempli à 0 pour l'actif.
        expected_pred = active.predict(unseen[["a"]].assign(b=0.0))
        self.assertAlmostEqual(active_metrics["mae"], mean_absolute_error(unseen["prix"], expected_pred))
        self.assertAlmostEqual(new_metrics["mae"], mean_absolute_error(
            unseen["prix"], candidate.predict(X_test.iloc[10:])))

    def test_identical_models_get_identical_metrics_and_are_promoted(self):
        df = self._frame(60)
        model = LinearRegression().fit(df[["a", "b"]], df["prix"] + df["a"] ** 2)
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "active.pkl")
            joblib.dump(model, path)
            new_metrics, active_metrics, _ = train_model.compare_on_common_test(
                model, df[["a", "b"]], df["prix"], df["url"], path, set(), min_rows=20,
            )
        self.assertEqual(new_metrics, active_metrics)
        self.assertTrue(decide_promotion(new_metrics, active_metrics)[0])

    def test_returns_none_when_too_few_unseen_rows_or_no_active_model(self):
        df = self._frame(30)
        model = LinearRegression().fit(df[["a", "b"]], df["prix"])
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "active.pkl")
            args = (model, df[["a", "b"]], df["prix"], df["url"])
            self.assertIsNone(train_model.compare_on_common_test(*args, path, set(), min_rows=20))
            joblib.dump(model, path)
            seen = set(df["url"][:15])
            self.assertIsNone(train_model.compare_on_common_test(*args, path, seen, min_rows=20))
