import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class QuartierHistoriqueRouteTest(unittest.TestCase):
    def test_route_returns_price_history_across_the_projects_recorded_snapshots(self):
        """État actuel réel du projet (2 snapshots enregistrés à ce jour,
        voir backend/data/snapshots/manifest.csv) : assez de recul pour une
        tendance, la route doit renvoyer un historique chronologique plutôt
        que insufficient_history."""
        client = app.app.test_client()

        response = client.post(
            "/api/quartier-historique",
            json={"quartier": "Gerland", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["found"])
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(len(data["historique"]), 1)
        for point in data["historique"]:
            self.assertIn("date", point)
            self.assertIn("prix_m2_moyen", point)
            self.assertIn("count", point)

    def test_route_rejects_blank_quartier_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/quartier-historique",
            json={"quartier": "   "},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Le nom du quartier est vide"})


if __name__ == "__main__":
    unittest.main()
