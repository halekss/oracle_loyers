import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.text_matching import compact_text, match_quartier, normalize_text, resolve_quartier, searchable_text


class NormalizeTextTest(unittest.TestCase):
    def test_strips_accents_and_lowercases(self):
        self.assertEqual(normalize_text("Gerland Été"), "gerland ete")

    def test_none_returns_empty_string(self):
        self.assertEqual(normalize_text(None), "")


class CompactTextTest(unittest.TestCase):
    def test_removes_hyphens_and_spaces(self):
        self.assertEqual(compact_text("Part-Dieu"), "partdieu")

    def test_collapses_multiple_spaces(self):
        self.assertEqual(compact_text("Vieux   Lyon"), "vieuxlyon")


class SearchableTextTest(unittest.TestCase):
    def test_replaces_punctuation_with_single_space(self):
        self.assertEqual(searchable_text("Part-Dieu"), "part dieu")

    def test_collapses_multiple_spaces_and_trims(self):
        self.assertEqual(searchable_text("  Vieux   Lyon  "), "vieux lyon")


class MatchQuartierTest(unittest.TestCase):
    """ORA-109 : tolérance aux fautes de frappe sur les quartiers connus."""

    KNOWN_QUARTIERS = ["Gerland", "Part-Dieu", "Vieux Lyon", "Croix-Rousse", "Confluence"]

    def test_finds_an_exact_match(self):
        result = match_quartier("Gerland", self.KNOWN_QUARTIERS)

        self.assertTrue(result["found"])
        self.assertEqual(result["match"], "Gerland")

    def test_tolerates_a_typo(self):
        result = match_quartier("greland", self.KNOWN_QUARTIERS)

        self.assertTrue(result["found"])
        self.assertEqual(result["match"], "Gerland")

    def test_tolerates_missing_hyphen(self):
        result = match_quartier("part dieu", self.KNOWN_QUARTIERS)

        self.assertTrue(result["found"])
        self.assertEqual(result["match"], "Part-Dieu")

    def test_tolerates_a_typo_within_a_full_sentence(self):
        result = match_quartier("je cherche un t2 a greland stp", self.KNOWN_QUARTIERS)

        self.assertTrue(result["found"])
        self.assertEqual(result["match"], "Gerland")

    def test_returns_not_found_with_no_match_for_a_distant_query(self):
        result = match_quartier("xyzabc123", self.KNOWN_QUARTIERS)

        self.assertFalse(result["found"])
        self.assertIsNone(result["match"])

    def test_returns_not_found_for_an_empty_query(self):
        result = match_quartier("", self.KNOWN_QUARTIERS)

        self.assertFalse(result["found"])
        self.assertEqual(result["suggestions"], [])

    def test_returns_not_found_when_no_known_quartiers_are_provided(self):
        result = match_quartier("gerland", [])

        self.assertFalse(result["found"])
        self.assertEqual(result["suggestions"], [])


class ResolveQuartierTest(unittest.TestCase):
    """ORA-110 : point d'entrée unique utilisé par /api/quartier-stats,
    /api/quartier-historique et /api/predict pour résoudre un quartier saisi
    vers son libellé canonique."""

    KNOWN_QUARTIERS = ["Gerland", "Part-Dieu", "Vieux Lyon", "Croix-Rousse", "Confluence"]

    def test_resolves_a_substring_query_case_insensitively(self):
        self.assertEqual(resolve_quartier("gerland", self.KNOWN_QUARTIERS), "Gerland")

    def test_resolves_a_typo(self):
        self.assertEqual(resolve_quartier("greland", self.KNOWN_QUARTIERS), "Gerland")

    def test_returns_none_for_an_unrelated_query(self):
        self.assertIsNone(resolve_quartier("xyzabc123", self.KNOWN_QUARTIERS))

    def test_returns_none_for_an_empty_query(self):
        self.assertIsNone(resolve_quartier("", self.KNOWN_QUARTIERS))
