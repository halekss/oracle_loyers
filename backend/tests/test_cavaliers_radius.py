import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.cavaliers_radius import CavaliersRadiusService, ALLOWED_RADII_M

CENTER_LAT, CENTER_LNG = 45.0, 4.0
# ~111 320 m par degré de latitude à cette latitude — largement assez de
# marge par rapport aux rayons testés (300/500/1000m) pour que l'imprécision
# entre ce facteur approximatif et le rayon terrestre moyen utilisé par
# haversine_distance_m (6 371 000 m) ne fasse jamais basculer un point d'un
# côté ou de l'autre d'un seuil.
DEG_PER_METER_LAT = 1 / 111320.0


def _offset(dist_m):
    """(lat, lng) à ~`dist_m` mètres au nord de CENTER_LAT/CENTER_LNG."""
    return CENTER_LAT + dist_m * DEG_PER_METER_LAT, CENTER_LNG


LYON_ROWS = [
    # categorie_cavalier, type_osm, nom_lieu, distance (m), code_postal
    ("Vice - Bar", "bar", "Le Bar Proche", 100, "69002"),
    ("Vice - Bar", "bar", "Le Bar Loin", 800, "69002"),
    ("Vice - Kebab", "kebab", "Kebab King", 400, "69002"),
    ("Gentrification - Yoga", "yoga", "Studio Yoga", 1500, "69002"),
    ("Nuisance - École", "school", "École du Coin", 800, "69002"),
    ("Superstition - Cimetière", "cemetery", "Cimetière du Nord", 1500, "69004"),
]

LILLE_ROWS = [
    ("Vice - Bar", "bar", "Bar Lillois", 100, None),
]


def _write_csv(path, rows, with_code_postal, bom=False):
    header = "categorie_cavalier,type_osm,nom_lieu,latitude,longitude"
    if with_code_postal:
        header += ",code_postal"
    lines = [header]
    for categorie, type_osm, nom, dist_m, code_postal in rows:
        lat, lng = _offset(dist_m)
        line = f"{categorie},{type_osm},{nom},{lat},{lng}"
        if with_code_postal:
            line += f",{code_postal or ''}"
        lines.append(line)
    encoding = "utf-8-sig" if bom else "utf-8"
    with open(path, "w", encoding=encoding) as f:
        f.write("\n".join(lines) + "\n")


class CavaliersRadiusServiceTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        self.lyon_csv = os.path.join(self.tmp_dir, "cavaliers_lyon.csv")
        self.lille_csv = os.path.join(self.tmp_dir, "cavaliers_lille.csv")
        _write_csv(self.lyon_csv, LYON_ROWS, with_code_postal=True)
        # Le vrai fichier Lille a un BOM UTF-8 (déjà rencontré en prod) : le
        # service doit le lire correctement (utf-8-sig), pas seulement le
        # fichier Lyon (sans BOM ici).
        _write_csv(self.lille_csv, LILLE_ROWS, with_code_postal=False, bom=True)
        self.service = CavaliersRadiusService(self.lyon_csv, self.lille_csv)

    def test_allowed_radii_are_exactly_300_500_1000(self):
        self.assertEqual(ALLOWED_RADII_M, (300, 500, 1000))

    def test_counts_change_with_the_radius(self):
        """Le Bar Loin (800m) et l'École du Coin (800m) n'entrent que dans le
        rayon 1000m ; Kebab King (400m) seulement à partir de 500m."""
        detail_300 = CavaliersRadiusService.category(self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 300), "Vice")
        detail_500 = CavaliersRadiusService.category(self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 500), "Vice")
        detail_1000 = CavaliersRadiusService.category(self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 1000), "Vice")

        self.assertEqual(detail_300["total"], 1)  # seulement Le Bar Proche
        self.assertEqual(detail_500["total"], 2)  # + Kebab King
        self.assertEqual(detail_1000["total"], 3)  # + Le Bar Loin

    def test_subcategory_count_and_minimum_distance(self):
        result = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 1000)
        vice = CavaliersRadiusService.category(result, "Vice")
        items_by_poi = {i["poi"]: i for i in vice["items"]}

        self.assertEqual(items_by_poi["Bar"]["count"], 2)
        self.assertEqual(items_by_poi["Bar"]["dist_m"], 100)
        self.assertEqual(items_by_poi["Kebab"]["count"], 1)
        self.assertEqual(items_by_poi["Kebab"]["dist_m"], 400)

    def test_empty_category_names_the_nearest_place_regardless_of_radius(self):
        """Cimetière du Nord (1500m) reste le plus proche même si hors de
        tous les rayons proposés — même sémantique que detail_cavaliers."""
        result = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 300)
        superstition = CavaliersRadiusService.category(result, "Superstition")

        self.assertEqual(superstition["items"], [])
        self.assertEqual(superstition["total"], 0)
        self.assertIn("Cimetière", superstition["empty_message"])
        # ~1500m attendus (léger écart possible, DEG_PER_METER_LAT est une
        # approximation ; on vérifie une plage plutôt que la valeur exacte).
        self.assertAlmostEqual(superstition["nearest"]["dist_m"], 1500, delta=10)

    def test_lyon_and_lille_are_kept_separate(self):
        lyon_result = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 1000)
        lille_result = self.service.compute(CENTER_LAT, CENTER_LNG, "lille", 1000)

        lyon_vice = CavaliersRadiusService.category(lyon_result, "Vice")
        lille_vice = CavaliersRadiusService.category(lille_result, "Vice")

        # 3 lieux Vice à Lyon (fixture LYON_ROWS) contre 1 seul à Lille
        # (fixture LILLE_ROWS) : la ville change bien le fichier consulté.
        self.assertEqual(lyon_vice["total"], 3)
        self.assertEqual(lille_vice["total"], 1)

    def test_reads_a_bom_prefixed_csv_without_losing_the_first_column(self):
        """Le fichier Lille fixture a un BOM (utf-8-sig) : si le service le
        lisait en utf-8 simple, 'categorie_cavalier' deviendrait
        '﻿categorie_cavalier' et plus aucune ligne ne matcherait."""
        result = self.service.compute(CENTER_LAT, CENTER_LNG, "lille", 1000)
        vice = CavaliersRadiusService.category(result, "Vice")

        self.assertEqual(vice["total"], 1)

    def test_phrases_use_the_given_rayon(self):
        result_300 = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 300)
        result_1000 = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 1000)

        phrase_300 = next(f["phrase"] for f in result_300["facteurs"] if f["categorie"] == "Vice")
        phrase_1000 = next(f["phrase"] for f in result_1000["facteurs"] if f["categorie"] == "Vice")

        self.assertIn("300m", phrase_300)
        self.assertIn("1000m", phrase_1000)

    def test_absence_phrase_for_a_category_empty_at_this_radius(self):
        result = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 300)
        phrase = next(f["phrase"] for f in result["facteurs"] if f["categorie"] == "Superstition")

        self.assertIn("300m", phrase)

    def test_returns_the_rounded_ville_prefixed_categories_in_order(self):
        result = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", 1000)
        categories = [d["categorie"] for d in result["cavaliers_detail"]]

        self.assertEqual(categories, ["Vice", "Gentrification", "Nuisance", "Superstition"])


class CavaliersRadiusServiceNoRadiusTest(unittest.TestCase):
    """Rayon « Aucun » (ORA-183, v3) : totaux à l'échelle de la ville, sans
    filtre de distance ni notion de "plus proche" — l'utilisateur a
    explicitement retiré le rayon, tous les lieux de la ville comptent."""

    def setUp(self):
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        self.lyon_csv = os.path.join(self.tmp_dir, "cavaliers_lyon.csv")
        self.lille_csv = os.path.join(self.tmp_dir, "cavaliers_lille.csv")
        _write_csv(self.lyon_csv, LYON_ROWS, with_code_postal=True)
        _write_csv(self.lille_csv, LILLE_ROWS, with_code_postal=False)
        self.service = CavaliersRadiusService(self.lyon_csv, self.lille_csv)

    def test_counts_every_place_in_the_city_regardless_of_distance(self):
        """3 lieux Vice à Lyon (Le Bar Proche 100m, Le Bar Loin 800m, Kebab
        King 400m) : tous comptent, y compris le plus lointain (800m, hors
        de tous les rayons 300/500/1000 proposés)."""
        result = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", None)
        vice = CavaliersRadiusService.category(result, "Vice")

        self.assertEqual(vice["total"], 3)

    def test_items_have_no_distance_field(self):
        result = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", None)
        vice = CavaliersRadiusService.category(result, "Vice")

        for item in vice["items"]:
            self.assertNotIn("dist_m", item)

    def test_a_category_absent_from_the_city_data_is_simply_skipped(self):
        """Lille (fixture LILLE_ROWS) n'a que du Vice : à l'échelle d'une
        ville, une catégorie présente dans les données a forcément un total
        > 0 (le "vide" n'a de sens que filtré par rayon) — une catégorie
        totalement absente du CSV reste omise, comme pour un rayon donné."""
        result = self.service.compute(CENTER_LAT, CENTER_LNG, "lille", None)
        categories = [d["categorie"] for d in result["cavaliers_detail"]]

        self.assertEqual(categories, ["Vice"])

    def test_facteurs_are_empty_because_the_joke_phrase_talks_about_a_radius(self):
        result = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", None)

        self.assertEqual(result["facteurs"], [])

    def test_lyon_and_lille_still_kept_separate(self):
        lyon_result = self.service.compute(CENTER_LAT, CENTER_LNG, "lyon", None)
        lille_result = self.service.compute(CENTER_LAT, CENTER_LNG, "lille", None)

        self.assertEqual(CavaliersRadiusService.category(lyon_result, "Vice")["total"], 3)
        self.assertEqual(CavaliersRadiusService.category(lille_result, "Vice")["total"], 1)


if __name__ == "__main__":
    unittest.main()
