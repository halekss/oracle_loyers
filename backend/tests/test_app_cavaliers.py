import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class CavaliersRouteTest(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.original_service = app.cavaliers_radius_service
        self.mock_service = MagicMock()
        self.mock_service.compute.return_value = {
            "cavaliers_detail": [
                {"categorie": "Vice", "total": 2, "items": [], "empty_message": None},
                {"categorie": "Gentrification", "total": 0, "items": [], "empty_message": "Rien dans le rayon."},
                {"categorie": "Nuisance", "total": 0, "items": [], "empty_message": "Rien dans le rayon."},
                {"categorie": "Superstition", "total": 0, "items": [], "empty_message": "Rien dans le rayon."},
            ],
            "facteurs": [
                {"categorie": "Vice", "phrase": "2 bar(s) à moins de 300m."},
                {"categorie": "Gentrification", "phrase": "Rien à signaler."},
                {"categorie": "Nuisance", "phrase": "Rien à signaler."},
                {"categorie": "Superstition", "phrase": "Rien à signaler."},
            ],
        }
        app.cavaliers_radius_service = self.mock_service

    def tearDown(self):
        app.cavaliers_radius_service = self.original_service

    def test_returns_200_with_the_computed_detail_for_a_valid_request(self):
        response = self.client.get("/api/cavaliers?lat=45.75&lng=4.83&ville=lyon&rayon_m=300")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["ville"], "lyon")
        self.assertEqual(data["rayon_m"], 300)
        self.assertEqual(len(data["cavaliers_detail"]), 4)
        self.assertEqual(len(data["facteurs"]), 4)

    def test_calls_the_service_with_the_parsed_query_params(self):
        self.client.get("/api/cavaliers?lat=45.75&lng=4.83&ville=lyon&rayon_m=1000")

        self.mock_service.compute.assert_called_once_with(45.75, 4.83, "lyon", 1000)

    def test_defaults_rayon_m_to_500_when_absent(self):
        self.client.get("/api/cavaliers?lat=45.75&lng=4.83&ville=lyon")

        self.mock_service.compute.assert_called_once_with(45.75, 4.83, "lyon", 500)

    def test_rejects_an_invalid_rayon_m(self):
        response = self.client.get("/api/cavaliers?lat=45.75&lng=4.83&ville=lyon&rayon_m=400")

        self.assertEqual(response.status_code, 400)
        self.mock_service.compute.assert_not_called()

    def test_rejects_a_missing_lat(self):
        response = self.client.get("/api/cavaliers?lng=4.83&ville=lyon")

        self.assertEqual(response.status_code, 400)

    def test_rejects_a_missing_ville(self):
        response = self.client.get("/api/cavaliers?lat=45.75&lng=4.83")

        self.assertEqual(response.status_code, 400)

    def test_never_leaks_the_raw_exception_message_to_the_client(self):
        self.mock_service.compute.side_effect = RuntimeError("chemin secret /Users/rick/prive/cavaliers_lyon.csv")

        response = self.client.get("/api/cavaliers?lat=45.75&lng=4.83&ville=lyon")

        self.assertEqual(response.status_code, 500)
        body = response.get_data(as_text=True)
        self.assertNotIn("chemin secret", body)
        self.assertNotIn("/Users/rick", body)


if __name__ == "__main__":
    unittest.main()
