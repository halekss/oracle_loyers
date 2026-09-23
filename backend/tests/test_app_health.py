import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class HealthRouteTest(unittest.TestCase):
    def test_health_route_exposes_the_loaded_model_version_per_ville(self):
        """ORA-154 : un modèle distinct par ville — /api/health expose l'état
        de chacun plutôt qu'un unique champ `model`."""
        client = app.app.test_client()

        response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn(data["status"], ["ok", "degraded"])
        self.assertIn("model_loaded", data)
        self.assertIn("Lyon", data["models"])
        self.assertIn("Lille", data["models"])
        for ville_info in data["models"].values():
            self.assertIn("loaded", ville_info)
            self.assertIn("model_version", ville_info)
            self.assertIn("trained_at", ville_info)
            self.assertIn("metrics", ville_info)

    def test_health_route_exposes_the_training_dataset_size_per_ville(self):
        """ORA-171 : "entraîné sur N annonces" (maquette 03) doit venir du
        dernier run loggé par train_model.py (training_metrics_<ville>.jsonl),
        pas d'un chiffre codé en dur côté frontend."""
        client = app.app.test_client()

        response = client.get("/api/health")

        data = response.get_json()
        for ville_info in data["models"].values():
            if ville_info["loaded"]:
                self.assertIn("dataset_size", ville_info["metrics"])
                self.assertIsInstance(ville_info["metrics"]["dataset_size"], int)


if __name__ == "__main__":
    unittest.main()
