import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import merge_cavaliers_villes
from merge_cavaliers_villes import merge_all_villes


class MergeAllVillesTest(unittest.TestCase):
    """ORA-153 : avant ce script, rien ne produisait cavaliers_all.csv
    automatiquement (recréé à la main lors des sessions multi-ville) — c'est
    pourtant le fichier réellement consommé par clean_immo.py."""

    def _declared_villes(self):
        return {
            "lyon": {"nom": "Lyon", "slug": "lyon"},
            "lille": {"nom": "Lille", "slug": "lille"},
        }

    def test_concatenates_all_existing_ville_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pd.DataFrame([{"nom_lieu": "Le Zinc", "categorie_cavalier": "Vice - Bar"}]).to_csv(
                os.path.join(tmp_dir, "cavaliers_lyon.csv"), index=False
            )
            pd.DataFrame([{"nom_lieu": "Chez Ali", "categorie_cavalier": "Vice - Kebab"}]).to_csv(
                os.path.join(tmp_dir, "cavaliers_lille.csv"), index=False
            )
            output_file = os.path.join(tmp_dir, "cavaliers_all.csv")

            with patch.object(merge_cavaliers_villes, "load_declared_villes", return_value=self._declared_villes()):
                merge_all_villes(data_dir=tmp_dir, output_file=output_file)

            result = pd.read_csv(output_file)

        self.assertEqual(len(result), 2)
        self.assertEqual(set(result["nom_lieu"]), {"Le Zinc", "Chez Ali"})

    def test_ignores_a_ville_with_no_file_yet(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pd.DataFrame([{"nom_lieu": "Le Zinc", "categorie_cavalier": "Vice - Bar"}]).to_csv(
                os.path.join(tmp_dir, "cavaliers_lyon.csv"), index=False
            )
            output_file = os.path.join(tmp_dir, "cavaliers_all.csv")

            with patch.object(merge_cavaliers_villes, "load_declared_villes", return_value=self._declared_villes()):
                merge_all_villes(data_dir=tmp_dir, output_file=output_file)

            result = pd.read_csv(output_file)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "nom_lieu"], "Le Zinc")

    def test_does_not_write_output_file_when_no_ville_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = os.path.join(tmp_dir, "cavaliers_all.csv")

            with patch.object(merge_cavaliers_villes, "load_declared_villes", return_value=self._declared_villes()):
                merge_all_villes(data_dir=tmp_dir, output_file=output_file)

            self.assertFalse(os.path.exists(output_file))


if __name__ == "__main__":
    unittest.main()
