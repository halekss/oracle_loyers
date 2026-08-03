import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from api_overpass import merge_cavaliers


def _row(lat, lon, type_osm, categorie, nom):
    return {
        'categorie_cavalier': categorie,
        'type_osm': type_osm,
        'nom_lieu': nom,
        'latitude': lat,
        'longitude': lon,
    }


class MergeCavaliersTest(unittest.TestCase):
    def test_strictly_identical_row_is_deduplicated(self):
        df_old = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Le Zinc")])
        df_new = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Le Zinc")])

        result = merge_cavaliers(df_old, df_new)

        self.assertEqual(len(result), 1)

    def test_recategorized_poi_is_not_silently_lost(self):
        df_old = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Le Zinc")])
        # Même point OSM (lat/lon), mais ré-étiqueté sous une autre catégorie/nom
        df_new = pd.DataFrame([_row(45.75, 4.85, "bar", "Gentrification - Torréfacteur", "Le Zinc Café")])

        result = merge_cavaliers(df_old, df_new)

        self.assertEqual(len(result), 2)
        self.assertIn("Vice - Bar", result['categorie_cavalier'].values)
        self.assertIn("Gentrification - Torréfacteur", result['categorie_cavalier'].values)

    def test_renamed_poi_keeps_both_versions_when_only_name_changes(self):
        df_old = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Ancien Nom")])
        df_new = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Nouveau Nom")])

        result = merge_cavaliers(df_old, df_new)

        # Nom différent => clé différente => les deux versions sont conservées,
        # conformément au comportement documenté (pas de perte silencieuse).
        self.assertEqual(len(result), 2)

    def test_unrelated_pois_are_all_kept(self):
        df_old = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Le Zinc")])
        df_new = pd.DataFrame([_row(45.76, 4.86, "kebab", "Vice - Kebab", "Chez Ali")])

        result = merge_cavaliers(df_old, df_new)

        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
