import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class ReportPdfRouteTest(unittest.TestCase):
    def test_route_returns_a_downloadable_pdf_for_a_valid_payload(self):
        client = app.app.test_client()

        response = client.post(
            "/api/report/pdf",
            json={
                "quartier": "Gerland",
                "estimated_price": 950,
                "prix_m2": 21,
                "confiance": "Élevée",
                "facteurs": [{"categorie": "Vice", "phrase": "2 bar(s) à moins de 500m."}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("attachment", response.headers.get("Content-Disposition", ""))
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_route_accepts_historique_and_comparables(self):
        """ORA-122 : enrichissement du rapport (historique de prix, biens comparables)."""
        client = app.app.test_client()

        response = client.post(
            "/api/report/pdf",
            json={
                "quartier": "Gerland",
                "estimated_price": 950,
                "historique": [
                    {"date": "2026-01-01T00:00:00+00:00", "prix_m2_moyen": 20, "count": 12},
                ],
                "comparables": [
                    {"type_local": "T2", "prix": 780, "surface": 45},
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_route_rejects_blank_quartier_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/report/pdf",
            json={"quartier": "   ", "estimated_price": 950},
        )

        self.assertEqual(response.status_code, 400)

    def test_route_rejects_missing_estimated_price_with_400(self):
        client = app.app.test_client()

        response = client.post(
            "/api/report/pdf",
            json={"quartier": "Gerland"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
