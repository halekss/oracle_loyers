"""Garde de version XGBoost : un modèle pickle entraîné hors de la version
épinglée (ORA-152) peut perdre son base_score au chargement en 2.1.4 — vu
avec les modèles 3.x de 739c1b2 (prédictions décalées d'environ -1000 €)."""
import os
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from scripts import train_model  # noqa: E402

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class XgboostVersionGuardTest(unittest.TestCase):
    def test_refuses_other_version(self):
        with self.assertRaises(SystemExit):
            train_model.check_xgboost_version("3.0.2")

    def test_accepts_pinned_version(self):
        train_model.check_xgboost_version(train_model.PINNED_XGBOOST_VERSION)

    def test_train_refuses_before_loading_data(self):
        with mock.patch.object(train_model, "XGBOOST_VERSION", "3.0.2"), \
                mock.patch.object(train_model, "load_source_dataframe") as load:
            with self.assertRaises(SystemExit):
                train_model.train("lyon")
        load.assert_not_called()

    def test_pin_matches_requirements_and_airflow_image(self):
        for path in ("backend/requirements.txt", "Airflow/Dockerfile"):
            with open(os.path.join(REPO_DIR, path), encoding="utf-8") as f:
                pins = re.findall(r"xgboost==([\w.]+)", f.read())
            self.assertEqual(pins, [train_model.PINNED_XGBOOST_VERSION], path)


if __name__ == "__main__":
    unittest.main()
