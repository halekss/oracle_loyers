import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.cavaliers_factors import detail_cavaliers, list_poi_types, summarize_cavaliers


def _row(**overrides):
    row = {
        'dist_vice_bar': 800, 'nb_vice_bar_500m': 0,
        'dist_vice_kebab': 800, 'nb_vice_kebab_500m': 0,
        'dist_gentrification_yoga': 800, 'nb_gentrification_yoga_500m': 0,
        'dist_nuisance_école': 800, 'nb_nuisance_école_500m': 0,
        'dist_superstition_cimetière': 800, 'nb_superstition_cimetière_500m': 0,
    }
    row.update(overrides)
    return row


class ListPoiTypesTest(unittest.TestCase):
    def test_groups_poi_types_by_category_from_columns(self):
        df = pd.DataFrame([_row()])

        result = list_poi_types(df)

        self.assertIn('bar', result['vice'])
        self.assertIn('kebab', result['vice'])
        self.assertIn('yoga', result['gentrification'])
        self.assertIn('école', result['nuisance'])
        self.assertIn('cimetière', result['superstition'])

    def test_ignores_unrelated_columns(self):
        df = pd.DataFrame([{**_row(), 'prix': 900, 'surface': 45}])

        result = list_poi_types(df)

        all_pois = [poi for pois in result.values() for poi in pois]
        self.assertNotIn('prix', all_pois)
        self.assertNotIn('surface', all_pois)


class SummarizeCavaliersTest(unittest.TestCase):
    def test_returns_one_factor_per_category_present_in_columns(self):
        df = pd.DataFrame([_row()])

        factors = summarize_cavaliers(df)

        categories = [f['categorie'] for f in factors]
        self.assertEqual(categories, ['Vice', 'Gentrification', 'Nuisance', 'Superstition'])

    def test_uses_absence_phrase_when_no_poi_present_within_500m(self):
        df = pd.DataFrame([_row(nb_vice_bar_500m=0, nb_vice_kebab_500m=0)])

        factors = summarize_cavaliers(df)

        vice_factor = next(f for f in factors if f['categorie'] == 'Vice')
        self.assertIn("Aucune tentation", vice_factor['phrase'])

    def test_picks_the_most_present_poi_type_in_a_category(self):
        df = pd.DataFrame([
            _row(nb_vice_bar_500m=4, dist_vice_bar=120, nb_vice_kebab_500m=1, dist_vice_kebab=400),
            _row(nb_vice_bar_500m=6, dist_vice_bar=100, nb_vice_kebab_500m=0, dist_vice_kebab=500),
        ])

        factors = summarize_cavaliers(df)

        vice_factor = next(f for f in factors if f['categorie'] == 'Vice')
        self.assertIn("bar", vice_factor['phrase'])
        self.assertIn("5", vice_factor['phrase'])  # nb moyen (4+6)/2, le template "bar" cite le compte, pas la distance

    def test_uses_generic_phrase_for_an_unrecognized_poi_type(self):
        df = pd.DataFrame([{
            'dist_vice_nouveau_poi_inconnu': 250,
            'nb_vice_nouveau_poi_inconnu_500m': 3,
        }])

        factors = summarize_cavaliers(df)

        vice_factor = next(f for f in factors if f['categorie'] == 'Vice')
        self.assertIn("nouveau poi inconnu", vice_factor['phrase'])

    def test_skips_a_category_entirely_absent_from_the_dataframe(self):
        df = pd.DataFrame([{
            'dist_vice_bar': 300, 'nb_vice_bar_500m': 2,
        }])

        factors = summarize_cavaliers(df)

        self.assertEqual(len(factors), 1)
        self.assertEqual(factors[0]['categorie'], 'Vice')

    def test_defaults_to_a_500m_radius_when_unspecified(self):
        """Non-régression : /api/quartier-stats et le PDF n'appellent
        summarize_cavaliers sans argument rayon — le comportement (et le
        texte "500m") doit rester identique à avant la paramétrisation."""
        df = pd.DataFrame([_row(nb_vice_bar_500m=4, dist_vice_bar=120)])

        factors = summarize_cavaliers(df)

        vice_factor = next(f for f in factors if f['categorie'] == 'Vice')
        self.assertIn("500m", vice_factor['phrase'])

    def test_uses_the_given_rayon_in_the_phrase_instead_of_500m(self):
        df = pd.DataFrame([_row(nb_vice_bar_500m=4, dist_vice_bar=120)])

        factors = summarize_cavaliers(df, rayon=300)

        vice_factor = next(f for f in factors if f['categorie'] == 'Vice')
        self.assertIn("300m", vice_factor['phrase'])
        self.assertNotIn("500m", vice_factor['phrase'])

    def test_absence_phrase_also_uses_the_given_rayon(self):
        df = pd.DataFrame([_row(nb_vice_bar_500m=0, nb_vice_kebab_500m=0)])

        factors = summarize_cavaliers(df, rayon=1000)

        vice_factor = next(f for f in factors if f['categorie'] == 'Vice')
        self.assertIn("1000m", vice_factor['phrase'])


class DetailCavaliersTest(unittest.TestCase):
    def test_lists_every_poi_subtype_with_rounded_count_and_min_distance(self):
        """ORA-172 : contrairement à summarize_cavaliers (1 phrase, le POI
        dominant), le panneau "Les 4 Cavaliers" liste TOUS les sous-types."""
        df = pd.DataFrame([
            _row(nb_vice_bar_500m=12, dist_vice_bar=46, nb_vice_kebab_500m=2, dist_vice_kebab=54),
            _row(nb_vice_bar_500m=12, dist_vice_bar=200, nb_vice_kebab_500m=2, dist_vice_kebab=300),
        ])

        detail = detail_cavaliers(df)

        vice = next(d for d in detail if d['categorie'] == 'Vice')
        items_by_poi = {i['poi']: i for i in vice['items']}
        self.assertEqual(items_by_poi['Bar'], {'poi': 'Bar', 'count': 12, 'dist_m': 46})
        self.assertEqual(items_by_poi['Kebab'], {'poi': 'Kebab', 'count': 2, 'dist_m': 54})

    def test_sorts_items_by_descending_count(self):
        df = pd.DataFrame([_row(nb_vice_bar_500m=2, nb_vice_kebab_500m=8)])

        detail = detail_cavaliers(df)

        vice = next(d for d in detail if d['categorie'] == 'Vice')
        self.assertEqual([i['poi'] for i in vice['items']], ['Kebab', 'Bar'])

    def test_total_is_the_sum_of_listed_items_counts(self):
        df = pd.DataFrame([_row(nb_vice_bar_500m=12, nb_vice_kebab_500m=2)])

        detail = detail_cavaliers(df)

        vice = next(d for d in detail if d['categorie'] == 'Vice')
        self.assertEqual(vice['total'], 14)

    def test_empty_category_names_the_closest_poi_across_all_subtypes(self):
        """Reproduit "Rien dans le rayon. Pompes funèbres les plus proches à
        573 m." (maquette 04) : aucun sous-type superstition dense, mais on
        nomme quand même le plus proche tous types confondus."""
        df = pd.DataFrame([_row(
            nb_superstition_cimetière_500m=0, dist_superstition_cimetière=573,
        )])

        detail = detail_cavaliers(df)

        superstition = next(d for d in detail if d['categorie'] == 'Superstition')
        self.assertEqual(superstition['items'], [])
        self.assertEqual(superstition['total'], 0)
        self.assertEqual(superstition['empty_message'], "Rien dans le rayon. Cimetière les plus proches à 573 m.")

    def test_no_empty_message_when_the_category_has_items(self):
        df = pd.DataFrame([_row(nb_vice_bar_500m=12, dist_vice_bar=46)])

        detail = detail_cavaliers(df)

        vice = next(d for d in detail if d['categorie'] == 'Vice')
        self.assertIsNone(vice['empty_message'])

    def test_skips_a_category_entirely_absent_from_the_dataframe(self):
        df = pd.DataFrame([{'dist_vice_bar': 300, 'nb_vice_bar_500m': 2}])

        detail = detail_cavaliers(df)

        self.assertEqual(len(detail), 1)
        self.assertEqual(detail[0]['categorie'], 'Vice')


if __name__ == "__main__":
    unittest.main()
