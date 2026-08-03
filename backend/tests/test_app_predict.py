import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class PredictRouteTest(unittest.TestCase):
    def test_predict_route_returns_coherent_price_for_nominal_payload(self):
        client = app.app.test_client()

        response = client.post(
            "/api/predict",
            json={"surface": 45, "quartier": "Gerland", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreater(data["estimated_price"], 0)
        self.assertGreater(data["price_m2"], 0)
        self.assertIn(data["confiance"], ["Faible", "Moyenne", "Élevée"])
        self.assertEqual(data["quartier_detecte"], "Gerland")
        self.assertEqual(data["type_local_detecte"], "T2")

    def test_predict_route_rejects_missing_surface_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/predict",
            json={"quartier": "Gerland", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Payload invalide")
        self.assertTrue(any("surface" in detail for detail in data["details"]))

    def test_predict_route_rejects_negative_surface_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/predict",
            json={"surface": -10, "quartier": "Gerland", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 400)

    def test_predict_route_rejects_unknown_quartier_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/predict",
            json={"surface": 45, "quartier": "Atlantide", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertTrue(any("quartier" in detail for detail in data["details"]))

    def test_predict_route_returns_500_when_model_is_absent(self):
        client = app.app.test_client()

        with patch.object(app, "model", None):
            response = client.post(
                "/api/predict",
                json={"surface": 45, "quartier": "Gerland", "type_local": "T2"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
