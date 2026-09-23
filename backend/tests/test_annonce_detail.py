import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.annonce_detail import enrich_annonce_detail


def _dataset_row(**overrides):
    row = {
        'url': 'https://example.com/annonce-1',
        'latitude': 45.75, 'longitude': 4.85,
        'type_local': 'T2', 'quartier': 'Ainay', 'prix_m2': 19.4,
        'dist_vice_bar': 46, 'nb_vice_bar_500m': 2,
    }
    row.update(overrides)
    return row


class EnrichAnnonceDetailTest(unittest.TestCase):
    def test_adds_coordinates_and_type_from_the_matching_dataset_row(self):
        annonce = {'id': 1, 'url': 'https://example.com/annonce-1', 'titre': 'T2 Ainay'}
        df = pd.DataFrame([_dataset_row()])

        result = enrich_annonce_detail(annonce, df)

        self.assertEqual(result['latitude'], 45.75)
        self.assertEqual(result['longitude'], 4.85)
        self.assertEqual(result['type_local'], 'T2')

    def test_computes_the_quartier_average_prix_m2_for_the_same_type(self):
        annonce = {'id': 1, 'url': 'https://example.com/annonce-1'}
        df = pd.DataFrame([
            _dataset_row(prix_m2=18.0),
            _dataset_row(url='https://example.com/annonce-2', prix_m2=20.0),
            # Autre type, ne doit pas peser dans la moyenne T2 :
            _dataset_row(url='https://example.com/annonce-3', type_local='T3', prix_m2=100.0),
        ])

        result = enrich_annonce_detail(annonce, df)

        self.assertEqual(result['quartier_prix_m2_moyen'], 19.0)

    def test_includes_cavaliers_detail_for_the_matched_row_only(self):
        annonce = {'id': 1, 'url': 'https://example.com/annonce-1'}
        df = pd.DataFrame([_dataset_row()])

        result = enrich_annonce_detail(annonce, df)

        self.assertIn('cavaliers_detail', result)
        vice = next(d for d in result['cavaliers_detail'] if d['categorie'] == 'Vice')
        self.assertEqual(vice['items'][0], {'poi': 'Bar', 'count': 2, 'dist_m': 46})

    def test_returns_the_annonce_unchanged_when_the_url_has_no_match(self):
        annonce = {'id': 1, 'url': 'https://example.com/unknown', 'titre': 'X'}
        df = pd.DataFrame([_dataset_row()])

        result = enrich_annonce_detail(annonce, df)

        self.assertEqual(result, annonce)

    def test_returns_the_annonce_unchanged_when_the_dataset_is_empty(self):
        annonce = {'id': 1, 'url': 'https://example.com/annonce-1'}

        result = enrich_annonce_detail(annonce, pd.DataFrame())

        self.assertEqual(result, annonce)

    def test_returns_the_annonce_unchanged_when_url_is_missing(self):
        annonce = {'id': 1, 'titre': 'Sans url'}
        df = pd.DataFrame([_dataset_row()])

        result = enrich_annonce_detail(annonce, df)

        self.assertEqual(result, annonce)


if __name__ == "__main__":
    unittest.main()
