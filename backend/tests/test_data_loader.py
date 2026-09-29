"""ORA-195 : `DataLoader.get_clean_data()` exclut les annonces suspectes
(outlier_detection, règle unique) des agrégats — médianes/estimations/
écarts/comparables/historique — sans jamais les retirer de `get_data()`
(source brute, encore utile ailleurs, ex. compter le total d'annonces)."""
import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.data_loader import DataLoader


class DataLoaderCleanDataTest(unittest.TestCase):
    def setUp(self):
        fd, self.csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)

    def tearDown(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def _write(self, rows):
        pd.DataFrame(rows).to_csv(self.csv_path, index=False)

    def test_get_data_still_returns_every_row_including_suspects(self):
        self._write([
            {'prix': 800, 'surface': 40, 'type_local': 'T2'},
            {'prix': 862, 'surface': 525, 'type_local': 'Grand (T4+)'},  # suspect (prix/m²)
        ])

        loader = DataLoader(self.csv_path)

        self.assertEqual(len(loader.get_data()), 2)

    def test_get_clean_data_excludes_suspects(self):
        self._write([
            {'prix': 800, 'surface': 40, 'type_local': 'T2'},
            {'prix': 862, 'surface': 525, 'type_local': 'Grand (T4+)'},  # suspect (prix/m²)
        ])

        loader = DataLoader(self.csv_path)
        clean = loader.get_clean_data()

        self.assertEqual(len(clean), 1)
        self.assertEqual(clean.iloc[0]['prix'], 800)

    def test_get_clean_data_keeps_everything_when_no_row_is_suspect(self):
        self._write([
            {'prix': 800, 'surface': 40, 'type_local': 'T2'},
            {'prix': 1200, 'surface': 60, 'type_local': 'T3'},
        ])

        loader = DataLoader(self.csv_path)

        self.assertEqual(len(loader.get_clean_data()), 2)

    def test_get_clean_data_is_safe_when_data_failed_to_load(self):
        missing_path = self.csv_path + '.does-not-exist'
        loader = DataLoader(missing_path)

        self.assertIsNone(loader.get_clean_data())


if __name__ == '__main__':
    unittest.main()
