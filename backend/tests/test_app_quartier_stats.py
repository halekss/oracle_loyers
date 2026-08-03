import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class QuartierStatsRouteTest(unittest.TestCase):
    def test_route_returns_stats_for_a_valid_payload(self):
        client = app.app.test_client()

        response = client.post(
            "/api/quartier-stats",
            json={"quartier": "Gerland", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["found"])
        self.assertEqual(data["quartier_detecte"], "Gerland")

        # ORA-73 : facteurs explicatifs ("4 Cavaliers") pour l'export PDF.
        self.assertIn("facteurs", data)
        self.assertEqual(len(data["facteurs"]), 4)
        for facteur in data["facteurs"]:
            self.assertIn("categorie", facteur)
            self.assertIn("phrase", facteur)

    def test_route_rejects_blank_quartier_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/quartier-stats",
            json={"quartier": "   "},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Le nom du quartier est vide"})

    def test_route_rejects_quartier_shaped_as_a_list_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/quartier-stats",
            json={"quartier": ["Gerland"]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Le nom du quartier est vide"})


if __name__ == "__main__":
    unittest.main()
