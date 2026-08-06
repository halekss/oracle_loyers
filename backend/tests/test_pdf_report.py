import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.pdf_report import build_report_html, render_estimation_pdf


class BuildReportHtmlTest(unittest.TestCase):
    """ORA-121 : mise en page HTML source du PDF (WeasyPrint), testable
    indépendamment du rendu PDF lui-même."""

    def test_includes_the_quartier_and_estimated_price(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "prix_m2": 21,
        })

        self.assertIn("Gerland", html)
        self.assertIn("950", html)
        self.assertIn("21", html)

    def test_includes_the_facteurs_when_present(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "facteurs": [
                {"categorie": "Vice", "phrase": "2 bar(s) à moins de 500m."},
                {"categorie": "Nuisance", "phrase": "Une aire de jeux à 208m."},
            ],
        })

        self.assertIn("Vice", html)
        self.assertIn("2 bar(s) à moins de 500m.", html)
        self.assertIn("Nuisance", html)
        self.assertIn("Une aire de jeux à 208m.", html)

    def test_omits_the_facteurs_section_when_absent(self):
        html = build_report_html({"quartier": "Gerland", "estimated_price": 950})

        self.assertNotIn("Les 4 Cavaliers", html)

    def test_escapes_hostile_quartier_value(self):
        html = build_report_html({
            "quartier": "<script>alert(1)</script>",
            "estimated_price": 950,
        })

        self.assertNotIn("<script>alert(1)</script>", html)

    def test_includes_a4_page_size_for_print(self):
        html = build_report_html({"quartier": "Gerland", "estimated_price": 950})

        self.assertIn("size: A4", html)

    def test_includes_the_price_history_when_present(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "historique": [
                {"date": "2026-01-01T00:00:00+00:00", "prix_m2_moyen": 20, "count": 12},
                {"date": "2026-02-01T00:00:00+00:00", "prix_m2_moyen": 21, "count": 14},
            ],
        })

        self.assertIn("Historique du prix", html)
        self.assertIn("20", html)
        self.assertIn("21", html)

    def test_omits_the_price_history_section_when_absent(self):
        html = build_report_html({"quartier": "Gerland", "estimated_price": 950})

        self.assertNotIn("Historique du prix", html)

    def test_includes_the_comparables_when_present(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "comparables": [
                {"type_local": "T2", "prix": 780, "surface": 45},
                {"type_local": "T2", "prix": 810, "surface": 48},
            ],
        })

        self.assertIn("Biens comparables", html)
        self.assertIn("780", html)
        self.assertIn("45", html)

    def test_omits_the_comparables_section_when_absent(self):
        html = build_report_html({"quartier": "Gerland", "estimated_price": 950})

        self.assertNotIn("Biens comparables", html)


class RenderEstimationPdfTest(unittest.TestCase):
    def test_returns_pdf_bytes(self):
        pdf_bytes = render_estimation_pdf({
            "quartier": "Gerland",
            "estimated_price": 950,
            "prix_m2": 21,
            "confiance": "Élevée",
            "facteurs": [{"categorie": "Vice", "phrase": "2 bar(s) à moins de 500m."}],
        })

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 500)


if __name__ == "__main__":
    unittest.main()
