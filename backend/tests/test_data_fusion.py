import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from data_fusion import (
    clean_price_integer,
    clean_surface,
    extract_postal_code,
    extract_type,
    format_description,
)


class CleanPriceIntegerTest(unittest.TestCase):
    def test_strips_currency_symbol_and_spaces(self):
        self.assertEqual(clean_price_integer("850 €"), 850)

    def test_strips_eur_and_cc_suffixes(self):
        self.assertEqual(clean_price_integer("650€ cc"), 650)
        self.assertEqual(clean_price_integer("700 eur"), 700)

    def test_handles_thousands_separator_space(self):
        self.assertEqual(clean_price_integer("1 200 €"), 1200)

    def test_returns_none_for_nan(self):
        self.assertIsNone(clean_price_integer(pd.NA))
        self.assertIsNone(clean_price_integer(float("nan")))

    def test_returns_none_when_no_digits_present(self):
        self.assertIsNone(clean_price_integer("Prix sur demande"))


class CleanSurfaceTest(unittest.TestCase):
    def test_extracts_integer_surface_before_m2_marker(self):
        self.assertEqual(clean_surface("Appartement 45 m2 lumineux"), 45.0)

    def test_extracts_decimal_surface_with_comma(self):
        self.assertEqual(clean_surface("62,5 m²"), 62.5)

    def test_extracts_decimal_surface_with_dot(self):
        self.assertEqual(clean_surface("62.5 m2"), 62.5)

    def test_returns_none_when_no_surface_marker_found(self):
        self.assertIsNone(clean_surface("Bel appartement lumineux"))

    def test_returns_none_for_nan(self):
        self.assertIsNone(clean_surface(pd.NA))


class ExtractPostalCodeTest(unittest.TestCase):
    def test_extracts_explicit_lyon_postal_code(self):
        self.assertEqual(extract_postal_code("Appartement Lyon 69007"), "69007")

    def test_derives_postal_code_from_arrondissement_mention(self):
        self.assertEqual(extract_postal_code("Lyon 3eme, quartier Part-Dieu"), "69003")

    def test_defaults_to_69000_when_nothing_found(self):
        self.assertEqual(extract_postal_code("Bel appartement"), "69000")

    def test_defaults_to_69000_for_nan(self):
        self.assertEqual(extract_postal_code(pd.NA), "69000")


class ExtractTypeTest(unittest.TestCase):
    def test_detects_colocation(self):
        self.assertEqual(extract_type("Chambre en Colocation"), "Colocation")

    def test_detects_maison(self):
        self.assertEqual(extract_type("Belle Maison avec jardin"), "Maison")

    def test_detects_studio(self):
        self.assertEqual(extract_type("Studio meublé centre-ville"), "Studio")

    def test_detects_parking(self):
        self.assertEqual(extract_type("Location Garage sécurisé"), "Parking")

    def test_defaults_to_appartement(self):
        self.assertEqual(extract_type("T3 lumineux avec balcon"), "Appartement")

    def test_defaults_to_appartement_for_nan(self):
        self.assertEqual(extract_type(pd.NA), "Appartement")


class FormatDescriptionTest(unittest.TestCase):
    def test_extracts_room_count_prefix(self):
        result = format_description("T3 Lyon 69003 Appartement lumineux avec balcon")
        self.assertTrue(result.startswith("T3"))
        self.assertNotIn("69003", result)
        self.assertNotIn("Lyon", result)

    def test_returns_empty_string_for_nan(self):
        self.assertEqual(format_description(pd.NA), "")


if __name__ == "__main__":
    unittest.main()
