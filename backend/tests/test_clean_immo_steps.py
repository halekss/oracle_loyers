import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import clean_immo


class StepQuartiersTest(unittest.TestCase):
    def test_known_code_postal_and_coordinates_returns_named_quartier(self):
        df = pd.DataFrame([
            {"code_postal": "69006", "latitude": 45.77, "longitude": 4.86},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Brotteaux / Foch")

    def test_missing_code_postal_returns_inconnu(self):
        df = pd.DataFrame([
            {"code_postal": None, "latitude": 45.77, "longitude": 4.86},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Inconnu")


class StepTypesTest(unittest.TestCase):
    def test_detects_type_from_text(self):
        df = pd.DataFrame([
            {"type": "Appartement T3", "description": "beau T3 lumineux", "surface": 60},
        ])

        result = clean_immo.step_types(df)

        self.assertEqual(result.loc[0, "type_local"], "T3")

    def test_no_text_signal_and_unparseable_surface_returns_inconnu(self):
        df = pd.DataFrame([
            {"type": "", "description": "", "surface": "N/C"},
        ])

        result = clean_immo.step_types(df)

        self.assertEqual(result.loc[0, "type_local"], "Inconnu")


class StepFeaturesTest(unittest.TestCase):
    def test_computes_nearest_distance_and_count(self):
        df = pd.DataFrame([
            {"latitude": 45.75, "longitude": 4.85},
        ])
        df_cavaliers = pd.DataFrame([
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.75, "longitude": 4.85},
        ])

        result = clean_immo.step_features(df, df_cavaliers)

        self.assertIn("dist_vice_bar", result.columns)
        self.assertAlmostEqual(result.loc[0, "dist_vice_bar"], 0.0)
        self.assertEqual(result.loc[0, "nb_vice_bar_500m"], 1)

    def test_empty_cavaliers_returns_dataframe_unchanged(self):
        df = pd.DataFrame([
            {"latitude": 45.75, "longitude": 4.85},
        ])
        df_cavaliers = pd.DataFrame(columns=['categorie_cavalier', 'latitude', 'longitude'])

        result = clean_immo.step_features(df, df_cavaliers)

        self.assertListEqual(list(result.columns), ["latitude", "longitude"])


class StepIdsTest(unittest.TestCase):
    def test_reindexes_from_one(self):
        df = pd.DataFrame([{"x": 1}, {"x": 2}, {"x": 3}])

        result = clean_immo.step_ids(df)

        self.assertListEqual(list(result["id_annonce"]), [1, 2, 3])

    def test_empty_dataframe_does_not_crash(self):
        df = pd.DataFrame(columns=["x"])

        result = clean_immo.step_ids(df)

        self.assertEqual(len(result), 0)
        self.assertIn("id_annonce", result.columns)


class BuildShapesFromCavaliersTest(unittest.TestCase):
    def test_missing_file_returns_empty_dict(self):
        result = clean_immo.build_shapes_from_cavaliers("/inexistant.csv")

        self.assertEqual(result, {})

    def test_builds_polygon_for_group_with_enough_points(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "cavaliers.csv")
            df = pd.DataFrame([
                {"code_postal": "69003", "latitude": 45.755, "longitude": 4.845},
                {"code_postal": "69003", "latitude": 45.757, "longitude": 4.847},
                {"code_postal": "69003", "latitude": 45.759, "longitude": 4.849},
                {"code_postal": "69003", "latitude": 45.756, "longitude": 4.850},
            ])
            df.to_csv(path, index=False)

            result = clean_immo.build_shapes_from_cavaliers(path)

            self.assertIn("69003", result)


if __name__ == "__main__":
    unittest.main()
