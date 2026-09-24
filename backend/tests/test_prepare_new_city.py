import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.prepare_new_city import build_config_skeleton, classify, slugify

# Réponses de geo.api.gouv.fr figées (ORA-160) : pas d'appel réseau en test.
LYON_CPS = [f"6900{i}" for i in range(1, 10)]
LYON_ARR = [{"nom": f"Lyon {i}", "codesPostaux": [cp]} for i, cp in enumerate(LYON_CPS, 1)]
LILLE_CPS = ["59000", "59160", "59260", "59777", "59800"]
BORDEAUX_CPS = ["33000", "33100", "33200", "33300", "33800"]


class ClassifyTest(unittest.TestCase):
    def test_lyon_is_lyon_like(self):
        self.assertEqual(classify(LYON_CPS, LYON_ARR, [])[0], "lyon_like")

    def test_lille_is_lille_like(self):
        self.assertEqual(classify(LILLE_CPS, [], ["59160", "59260"])[0], "lille_like")

    def test_bordeaux_is_hybride(self):
        self.assertEqual(classify(BORDEAUX_CPS, [], [])[0], "hybride_a_verifier")

    def test_single_postal_code_is_lille_like(self):
        self.assertEqual(classify(["12345"], [], [])[0], "lille_like")

    def test_arrondissements_not_covering_all_cps_are_not_lyon_like(self):
        self.assertEqual(classify(LYON_CPS + ["69999"], LYON_ARR, [])[0], "hybride_a_verifier")


class SkeletonTest(unittest.TestCase):
    def test_skeleton_is_a_todo_template_with_slug(self):
        skeleton = build_config_skeleton({"nom": "Saint-Étienne", "codesPostaux": ["42100", "42000"]})
        self.assertEqual(skeleton["slug"], "saint-etienne")
        self.assertEqual(skeleton["code_postal_defaut"], "42000")
        self.assertEqual(skeleton["seloger"]["base_url"], "A_COMPLETER")

    def test_slugify(self):
        self.assertEqual(slugify("Lille"), "lille")


if __name__ == "__main__":
    unittest.main()
