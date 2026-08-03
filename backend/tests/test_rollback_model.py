import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import rollback_model


class RollbackModelTest(unittest.TestCase):
    def test_rollback_restores_versioned_binary_and_updates_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            models_dir = tmp_dir
            model_path = os.path.join(models_dir, "price_predictor.pkl")
            versions_dir = os.path.join(models_dir, "versions")
            os.makedirs(versions_dir)

            old_version_path = os.path.join(versions_dir, "price_predictor_oldhash1234.pkl")
            with open(old_version_path, "wb") as f:
                f.write(b"contenu-ancienne-version")

            # Le modèle "actif" actuel est différent de la version qu'on veut restaurer.
            with open(model_path, "wb") as f:
                f.write(b"contenu-version-courante")

            meta_path = f"{model_path}.meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({"model_version": "currenthash", "metrics": {"mae": 100}}, f)

            with patch.object(rollback_model, "MODEL_PATH", model_path), \
                    patch.object(rollback_model, "VERSIONS_DIR", versions_dir):
                rollback_model.rollback_to("oldhash1234")

            with open(model_path, "rb") as f:
                self.assertEqual(f.read(), b"contenu-ancienne-version")

            with open(meta_path, encoding="utf-8") as f:
                metadata = json.load(f)
            self.assertEqual(metadata["model_version"], "oldhash1234")
            self.assertIn("rolled_back_at", metadata)
            # Les métriques précédentes ne sont pas perdues par le rollback.
            self.assertEqual(metadata["metrics"]["mae"], 100)

    def test_rollback_to_unknown_version_raises_clearly(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = os.path.join(tmp_dir, "price_predictor.pkl")
            versions_dir = os.path.join(tmp_dir, "versions")
            os.makedirs(versions_dir)

            with patch.object(rollback_model, "MODEL_PATH", model_path), \
                    patch.object(rollback_model, "VERSIONS_DIR", versions_dir):
                with self.assertRaises(SystemExit):
                    rollback_model.rollback_to("version-inexistante")


if __name__ == "__main__":
    unittest.main()
