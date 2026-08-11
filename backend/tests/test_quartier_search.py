import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.quartier_search import resolve_quartier_filter


def _df():
    return pd.DataFrame([
        {"ville": "Lyon", "quartier": "Ainay", "prix": 900},
        {"ville": "Lyon", "quartier": "Vieux Lyon", "prix": 1000},
        {"ville": "Lyon", "quartier": "Lyon / Non localisé", "prix": 800},
        {"ville": "Lille", "quartier": "Wazemmes", "prix": 700},
        {"ville": "Lille", "quartier": "Lille-Centre", "prix": 1200},
        {"ville": "Lille", "quartier": "Lille / Non localisé", "prix": 650},
    ])


class ResolveQuartierFilterTest(unittest.TestCase):
    def test_quartier_name_search_is_scoped_to_the_active_ville(self):
        # Régression réelle : chercher "Ainay" en étant sur l'onglet Lille
        # ne devait renvoyer aucun résultat, pas les stats du Ainay lyonnais
        # (et surtout pas un match flou vers un quartier lillois).
        result, match = resolve_quartier_filter(_df(), "Ainay", ville="lille")

        self.assertFalse(match["is_city_search"])
        self.assertFalse(match["found"])
        self.assertTrue(result.empty)

    def test_quartier_name_search_matches_within_the_active_ville(self):
        result, match = resolve_quartier_filter(_df(), "Ainay", ville="lyon")

        self.assertFalse(match["is_city_search"])
        self.assertTrue(match["found"])
        self.assertEqual(match["match"], "Ainay")
        self.assertEqual(list(result["quartier"]), ["Ainay"])

    def test_city_name_search_returns_all_matching_ville_rows_including_fallback(self):
        # Régression réelle : chercher "Lille" ne doit renvoyer QUE les
        # annonces de la ville de Lille (repli générique inclus, puisqu'il
        # en fait partie), pas un simple match flou sur un nom de quartier
        # contenant "Lille" (Lille-Centre...).
        result, match = resolve_quartier_filter(_df(), "Lille")

        self.assertTrue(match["is_city_search"])
        self.assertEqual(set(result["ville"]), {"Lille"})
        self.assertEqual(len(result), 3)

    def test_city_name_search_is_case_insensitive(self):
        result, match = resolve_quartier_filter(_df(), "lYoN")

        self.assertTrue(match["is_city_search"])
        self.assertEqual(len(result), 3)

    def test_partial_city_name_falls_back_to_fuzzy_quartier_match(self):
        # "Lill" ne matche pas exactement une ville connue : reste une
        # recherche de quartier, résolue par matching flou (ORA-110) au sein
        # de la ville active — ici sur tout le dataset faute de ville fournie.
        result, match = resolve_quartier_filter(_df(), "Lill")

        self.assertFalse(match["is_city_search"])
        self.assertTrue(match["found"])
        self.assertEqual(match["match"], "Lille-Centre")
        self.assertEqual(list(result["quartier"]), ["Lille-Centre"])

    def test_no_ville_param_searches_across_all_cities(self):
        # Compatibilité : sans `ville` (client existant qui ne l'envoie pas
        # encore), la recherche reste non bornée comme avant.
        result, match = resolve_quartier_filter(_df(), "Ainay")

        self.assertFalse(match["is_city_search"])
        self.assertEqual(list(result["quartier"]), ["Ainay"])

    def test_unresolved_quartier_returns_not_found(self):
        # Un texte qui ne matche raisonnablement aucun quartier de la ville
        # active renvoie found=False (le détail suggestions/score est déjà
        # couvert par les tests de services.text_matching.match_quartier).
        result, match = resolve_quartier_filter(_df(), "Bellecour", ville="lille")

        self.assertFalse(match["found"])
        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
