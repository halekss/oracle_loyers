import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.pdf_report import build_report_html, render_estimation_pdf


class BuildReportHtmlTest(unittest.TestCase):
    """ORA-121/ORA-177 : mise en page HTML source du PDF (WeasyPrint),
    alignée sur la maquette Claude Design 09 (`project/09-pdf.dc.html`),
    testable indépendamment du rendu PDF lui-même."""

    def test_includes_the_quartier_and_estimated_price(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
        })

        self.assertIn("Gerland", html)
        self.assertIn("950", html)

    def test_escapes_hostile_quartier_value(self):
        html = build_report_html({
            "quartier": "<script>alert(1)</script>",
            "estimated_price": 950,
        })

        self.assertNotIn("<script>alert(1)</script>", html)

    def test_includes_a4_page_size_for_print(self):
        html = build_report_html({"quartier": "Gerland", "estimated_price": 950})

        self.assertIn("size: A4", html)

    def test_includes_the_facteurs_when_present(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "facteurs": [
                {"categorie": "Vice", "phrase": "2 bar(s) à moins de 500m."},
                {"categorie": "Nuisance", "phrase": "Une aire de jeux à 208m."},
            ],
        })

        self.assertIn("Les 4 cavaliers", html)
        self.assertIn("Vice", html)
        self.assertIn("2 bar(s) à moins de 500m.", html)
        self.assertIn("Nuisance", html)
        self.assertIn("Une aire de jeux à 208m.", html)

    def test_omits_the_facteurs_section_when_absent(self):
        html = build_report_html({"quartier": "Gerland", "estimated_price": 950})

        self.assertNotIn("Les 4 cavaliers", html)

    def test_includes_the_comparables_table_with_source_and_ecart(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "comparables": [
                {"type_local": "T2", "prix": 780, "surface": 40, "site": "Vizzit"},
                {"type_local": "T2", "prix": 900, "surface": 40, "site": "PAP"},
            ],
        })

        self.assertIn("Les 2 annonces comparables", html)
        self.assertIn("780", html)
        self.assertIn("Vizzit", html)
        self.assertIn("PAP", html)
        # écart €/m² : 780/40=19,5 et 900/40=22,5, médiane=21 -> -7% / +7%
        self.assertIn("-7 %", html)
        self.assertIn("+7 %", html)

    def test_comparable_without_site_shows_a_placeholder(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "comparables": [{"type_local": "T2", "prix": 780, "surface": 40}],
        })

        self.assertIn(">—<", html)

    def test_omits_the_comparables_section_when_absent(self):
        html = build_report_html({"quartier": "Gerland", "estimated_price": 950})

        self.assertNotIn("annonces comparables", html)

    def test_loyer_median_box_uses_estimated_price_without_comparables(self):
        html = build_report_html({"quartier": "Gerland", "estimated_price": 950})

        self.assertIn("Loyer médian", html)
        self.assertIn("950", html)

    def test_loyer_median_box_derives_median_and_quartiles_from_comparables(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "comparables": [
                {"prix": 700, "surface": 40}, {"prix": 750, "surface": 40},
                {"prix": 800, "surface": 40}, {"prix": 850, "surface": 40},
            ],
            "count": 4,
        })

        self.assertIn("P25", html)
        self.assertIn("4 annonces", html)

    def test_omits_quartile_range_with_fewer_than_4_comparables(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "comparables": [{"prix": 700, "surface": 40}, {"prix": 800, "surface": 40}],
        })

        self.assertNotIn("P25", html)

    def test_estimation_box_only_shown_with_a_surface(self):
        with_surface = build_report_html({
            "quartier": "Gerland", "estimated_price": 950, "surface": 45,
        })
        without_surface = build_report_html({
            "quartier": "Gerland", "estimated_price": 950,
        })

        self.assertIn("Estimation 45 m²", with_surface)
        self.assertNotIn("metric-label\">Estimation", without_surface)

    def test_includes_the_data_as_of_date_when_present(self):
        html = build_report_html({
            "quartier": "Gerland",
            "estimated_price": 950,
            "data_as_of": "12/08/2026",
        })

        self.assertIn("Données au 12/08/2026", html)

    def test_omits_the_data_as_of_line_when_absent(self):
        html = build_report_html({"quartier": "Gerland", "estimated_price": 950})

        self.assertNotIn("Données au", html)


class RenderEstimationPdfTest(unittest.TestCase):
    def test_returns_pdf_bytes(self):
        pdf_bytes = render_estimation_pdf({
            "quartier": "Gerland",
            "estimated_price": 950,
            "prix_m2": 21,
            "confiance": "Élevée",
            "surface": 45,
            "facteurs": [{"categorie": "Vice", "phrase": "2 bar(s) à moins de 500m."}],
            "comparables": [{"type_local": "T2", "prix": 950, "surface": 45, "site": "Vizzit"}],
        })

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 500)


if __name__ == "__main__":
    unittest.main()
