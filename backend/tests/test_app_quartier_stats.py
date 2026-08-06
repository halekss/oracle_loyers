import os
import sys
import unittest
from unittest.mock import patch

import pandas as pd

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

    def test_route_returns_up_to_3_comparables(self):
        """ORA-122/ORA-128 : quelques biens comparables réels (échantillon),
        pour le rapport PDF et l'explication de la confiance côté frontend."""
        client = app.app.test_client()
        controlled_df = pd.DataFrame({
            'quartier': ['Gerland'] * 5,
            'prix': [700, 750, 800, 850, 1200],
            'surface': [30, 32, 35, 38, 50],
            'type_local': ['T2'] * 5,
        })

        with patch.object(app.data_loader, "get_data", return_value=controlled_df):
            response = client.post(
                "/api/quartier-stats",
                json={"quartier": "Gerland", "type_local": "T2"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("comparables", data)
        self.assertLessEqual(len(data["comparables"]), 3)
        self.assertGreater(len(data["comparables"]), 0)
        for comparable in data["comparables"]:
            self.assertIn("type_local", comparable)
            self.assertIn("prix", comparable)
            self.assertIn("surface", comparable)

    def test_route_returns_empty_comparables_list_when_type_filtered_result_is_empty(self):
        client = app.app.test_client()
        controlled_df = pd.DataFrame({
            'quartier': ['Gerland'],
            'prix': [700],
            'surface': [30],
            'type_local': ['T2'],
        })

        with patch.object(app.data_loader, "get_data", return_value=controlled_df):
            response = client.post(
                "/api/quartier-stats",
                json={"quartier": "Gerland", "type_local": "T4+"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["comparables"], [])

    def test_route_tolerates_a_typo_in_the_quartier_name(self):
        """ORA-110 : le endpoint utilise désormais le matching partagé
        (fuzzy) au lieu d'un str.contains naïf."""
        client = app.app.test_client()

        response = client.post(
            "/api/quartier-stats",
            json={"quartier": "greland", "type_local": "Tout"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["found"])
        self.assertEqual(data["quartier_detecte"], "Gerland")

    def test_route_reports_no_result_when_nothing_is_close(self):
        """ORA-111 : message différencié aucun résultat vs quartier ambigu."""
        client = app.app.test_client()
        controlled_df = pd.DataFrame({
            'quartier': ['Croix-Rousse Plateau', 'Pentes Croix-Rousse', 'Vieux Lyon'],
            'prix': [800, 850, 900],
            'surface': [40, 42, 45],
            'type_local': ['T2', 'T2', 'T2'],
        })

        with patch.object(app.data_loader, "get_data", return_value=controlled_df):
            response = client.post("/api/quartier-stats", json={"quartier": "gzzzzz", "type_local": "Tout"})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["found"])
        self.assertFalse(data["ambiguous"])
        self.assertEqual(data["suggestions"], [])

    def test_route_reports_ambiguous_when_several_quartiers_are_close(self):
        """ORA-111 : suggestions renvoyées quand plusieurs quartiers sont proches."""
        client = app.app.test_client()
        controlled_df = pd.DataFrame({
            'quartier': ['Croix-Rousse Plateau', 'Pentes Croix-Rousse', 'Vieux Lyon'],
            'prix': [800, 850, 900],
            'surface': [40, 42, 45],
            'type_local': ['T2', 'T2', 'T2'],
        })

        with patch.object(app.data_loader, "get_data", return_value=controlled_df):
            response = client.post("/api/quartier-stats", json={"quartier": "croiss", "type_local": "Tout"})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["found"])
        self.assertTrue(data["ambiguous"])
        self.assertEqual(
            set(data["suggestions"]), {"Croix-Rousse Plateau", "Pentes Croix-Rousse"}
        )
        self.assertIn("Croix-Rousse Plateau", data["message"])

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
