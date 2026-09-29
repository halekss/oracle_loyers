import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class PredictRouteTest(unittest.TestCase):
    def test_predict_route_rejects_physically_impossible_negative_price_with_500(self):
        """ORA-152 : un modèle qui prédit un loyer négatif (ex. pickle XGBoost
        désérialisé avec une version incompatible de celle utilisée à
        l'entraînement) ne doit jamais être renvoyé tel quel au frontend."""
        client = app.app.test_client()

        broken_model = MagicMock()
        broken_model.feature_names_in_ = app.models["Lyon"].feature_names_in_
        broken_model.predict.return_value = [-168.0]

        with patch.dict(app.models, {"Lyon": broken_model}):
            response = client.post(
                "/api/predict",
                json={"surface": 45, "quartier": "Gerland", "type_local": "T2"},
            )

        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertNotIn("estimated_price", data)
        self.assertEqual(data["code"], "IMPLAUSIBLE")

    def test_predict_route_rejects_zero_price_with_500(self):
        """Un loyer exactement nul n'est pas plus plausible qu'un loyer négatif."""
        client = app.app.test_client()

        broken_model = MagicMock()
        broken_model.feature_names_in_ = app.models["Lyon"].feature_names_in_
        broken_model.predict.return_value = [0.0]

        with patch.dict(app.models, {"Lyon": broken_model}):
            response = client.post(
                "/api/predict",
                json={"surface": 45, "quartier": "Gerland", "type_local": "T2"},
            )

        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertIn("error", data)

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
        self.assertEqual(data["code"], "NO_SURFACE")
        self.assertTrue(any("surface" in detail for detail in data["details"]))

    def test_predict_route_rejects_negative_surface_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/predict",
            json={"surface": -10, "quartier": "Gerland", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "NO_SURFACE")

    def test_predict_route_rejects_unknown_quartier_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/predict",
            json={"surface": 45, "quartier": "Atlantide", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["code"], "UNKNOWN_QUARTIER")
        self.assertTrue(any("quartier" in detail for detail in data["details"]))

    def test_predict_route_rejects_malformed_field_shape_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/predict",
            json={"surface": 45, "quartier": ["Gerland"], "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["error"], "Payload invalide")

    def test_predict_route_returns_500_when_no_model_is_loaded_for_any_ville(self):
        client = app.app.test_client()

        with patch.object(app, "models", {ville: None for ville in app.models}):
            response = client.post(
                "/api/predict",
                json={"surface": 45, "quartier": "Gerland", "type_local": "T2"},
            )

        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertEqual(data["code"], "MODEL_UNAVAILABLE")

    def test_predict_route_returns_400_when_model_is_absent_for_the_requested_ville_only(self):
        """ORA-154 : la panne d'un modèle ne doit plus dégrader toutes les
        villes — seule celle sans modèle chargé échoue (400, payload
        invalide pour cette zone), les autres continuent de répondre."""
        client = app.app.test_client()

        with patch.dict(app.models, {"Lyon": None}):
            response = client.post(
                "/api/predict",
                json={"surface": 45, "quartier": "Gerland", "type_local": "T2"},
            )

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data["code"], "UNKNOWN_QUARTIER")
        self.assertTrue(any("Lyon" in detail for detail in data["details"]))

    def test_predict_route_returns_a_low_sample_code_when_fewer_than_5_comparables(self):
        """ORA-198 : l'estimation reste affichée (200), juste signalée comme
        moins fiable — pas un état bloquant comme les autres codes."""
        client = app.app.test_client()

        with patch("app.estimate_confidence", return_value=("Faible", 2)):
            response = client.post(
                "/api/predict",
                json={"surface": 45, "quartier": "Gerland", "type_local": "T2"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertGreater(data["estimated_price"], 0)
        self.assertEqual(data["code"], "LOW_SAMPLE")

    def test_predict_route_omits_the_code_field_with_enough_comparables(self):
        client = app.app.test_client()

        with patch("app.estimate_confidence", return_value=("Élevée", 25)):
            response = client.post(
                "/api/predict",
                json={"surface": 45, "quartier": "Gerland", "type_local": "T2"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("code", response.get_json())

    def test_predict_route_returns_a_model_unavailable_code_when_the_prediction_itself_crashes(self):
        client = app.app.test_client()

        broken_model = MagicMock()
        broken_model.feature_names_in_ = app.models["Lyon"].feature_names_in_
        broken_model.predict.side_effect = RuntimeError("boom")

        with patch.dict(app.models, {"Lyon": broken_model}):
            response = client.post(
                "/api/predict",
                json={"surface": 45, "quartier": "Gerland", "type_local": "T2"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["code"], "MODEL_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
