import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class ListingsRouteTest(unittest.TestCase):
    def test_listings_route_exposes_ville_code_postal_and_prix_m2(self):
        """ORA-170 : le tableau de bord "Le marché en un coup d'œil" agrège
        côté frontend par arrondissement (code_postal) et par quartier
        (prix_m2 médian) — ces colonnes doivent être présentes en plus du
        strict nécessaire pour la carte."""
        client = app.app.test_client()

        response = client.get("/api/listings")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        for field in ("latitude", "longitude", "prix", "type_local", "quartier", "ville", "code_postal", "prix_m2"):
            self.assertIn(field, data[0])


if __name__ == "__main__":
    unittest.main()
