import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

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


if __name__ == "__main__":
    unittest.main()
