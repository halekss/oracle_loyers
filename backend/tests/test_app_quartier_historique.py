import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class QuartierHistoriqueRouteTest(unittest.TestCase):
    def test_route_returns_insufficient_history_with_the_projects_current_single_snapshot(self):
        """État actuel réel du projet (un seul snapshot enregistré à ce jour,
        voir backend/data/snapshots/manifest.csv) : la route doit le signaler
        honnêtement plutôt que de prétendre à une tendance sur un point."""
        client = app.app.test_client()

        response = client.post(
            "/api/quartier-historique",
            json={"quartier": "Gerland", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["found"])
        self.assertEqual(data["status"], "insufficient_history")
        self.assertEqual(data["historique"], [])

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
