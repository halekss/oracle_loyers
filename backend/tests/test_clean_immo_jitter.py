import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random

import pandas as pd
from shapely.geometry import Point

from scripts import clean_immo


class GeocodingJitterTest(unittest.TestCase):
    def _sample_df(self):
        return pd.DataFrame({
            "code_postal": ["69007", "69007", "69003", "75000", "69001"],
        })

    def test_step_geocoding_is_deterministic_across_runs(self):
        df1 = clean_immo.step_geocoding(self._sample_df())
        df2 = clean_immo.step_geocoding(self._sample_df())

        pd.testing.assert_series_equal(df1["latitude"], df2["latitude"])
        pd.testing.assert_series_equal(df1["longitude"], df2["longitude"])

    def test_step_geocoding_keeps_existing_real_coordinates_unjittered(self):
        df_input = self._sample_df()
        df_input["latitude"] = [45.75, None, None, None, None]
        df_input["longitude"] = [4.85, None, None, None, None]

        result = clean_immo.step_geocoding(df_input)

        self.assertAlmostEqual(result["latitude"].iloc[0], 45.75)
        self.assertAlmostEqual(result["longitude"].iloc[0], 4.85)


class LilleRealPolygonsTest(unittest.TestCase):
    """ORA-158 : le point tiré tombe dans le vrai polygone du quartier."""

    SLUG_URL = "https://www.seloger.com/annonces/locations/appartement/lille-59/{slug}/1234.htm"

    def test_jittered_point_falls_inside_the_real_quartier_polygon(self):
        self.assertTrue(clean_immo.QUARTIERS_LILLE_POLYGONS, "lille_quartiers.geojson absent")
        cases = {
            "moulins": "Lille-Moulins", "wazemmes": "Wazemmes", "vieux-lille": "Vieux-Lille",
            "fives": "Fives", "lille-sud": "Lille-Sud", "bois-blanc": "Bois Blancs",
        }
        random.seed(clean_immo.GEOCODING_JITTER_SEED)
        for slug, quartier in cases.items():
            polygon = clean_immo.QUARTIERS_LILLE_POLYGONS[quartier]
            for _ in range(20):
                lat, lon = clean_immo.get_point_for_zipcode("59000", {}, url=self.SLUG_URL.format(slug=slug))
                self.assertTrue(polygon.contains(Point(lon, lat)), f"{quartier}: ({lat}, {lon})")

    def test_match_quartier_lille_uses_the_real_polygon(self):
        for quartier in clean_immo.QUARTIERS_LILLE:
            centre = clean_immo.QUARTIERS_LILLE_POLYGONS[quartier].representative_point()
            found = clean_immo.match_quartier_lille(centre.y, centre.x)
            # Les tracés OSM peuvent se chevaucher légèrement : le point
            # doit au moins être contenu dans le quartier renvoyé.
            self.assertTrue(clean_immo.QUARTIERS_LILLE_POLYGONS[found].contains(centre), quartier)

    def test_geocoding_stays_deterministic_with_real_polygons(self):
        df = pd.DataFrame({
            "code_postal": ["59000"] * 3,
            "url": [self.SLUG_URL.format(slug=s) for s in ("moulins", "fives", "wazemmes")],
        })
        r1 = clean_immo.step_geocoding(df.copy())
        r2 = clean_immo.step_geocoding(df.copy())
        pd.testing.assert_series_equal(r1["latitude"], r2["latitude"])


if __name__ == "__main__":
    unittest.main()
