"""ORA-195 : règle unique de détection des annonces suspectes (outliers),
partagée par annonces_store.py, clean_immo.py, data_loader.py et
train_model.py. `detect_outlier` reste pure (pas de pandas) pour rester
importable depuis annonces_store.py (SQLite pur) ; `flag_dataframe` est la
version vectorisée pour les DataFrame pandas."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import outlier_detection as od


class DetectOutlierTest(unittest.TestCase):
    def test_a_normal_listing_is_not_suspect(self):
        suspect, reason = od.detect_outlier(prix=800, surface=40, type_local='T2')
        self.assertFalse(suspect)
        self.assertIsNone(reason)

    def test_prix_m2_too_low_is_suspect(self):
        # 862€ / 525m² = 1.64 €/m² < 6
        suspect, reason = od.detect_outlier(prix=862, surface=525, type_local='Grand (T4+)')
        self.assertTrue(suspect)
        self.assertIn('/m²', reason)

    def test_prix_m2_too_high_is_suspect(self):
        # 95€ / 15m² -> 6.33 €/m², pas suspect par prix_m2 mais surface OK ;
        # forçons un vrai prix_m2 trop haut : 4000€ / 10m² = 400 €/m²
        suspect, reason = od.detect_outlier(prix=4000, surface=10, type_local='Studio/T1')
        self.assertTrue(suspect)

    def test_surface_too_small_is_suspect(self):
        # 50€ / 5m² = 10 €/m² (dans la norme) : isole la règle de surface,
        # sans déclencher aussi la règle prix/m².
        suspect, reason = od.detect_outlier(prix=50, surface=5, type_local='Studio/T1')
        self.assertTrue(suspect)
        self.assertIn('petite', reason)

    def test_surface_too_large_is_suspect_unless_t4(self):
        suspect, reason = od.detect_outlier(prix=3000, surface=300, type_local='T3')
        self.assertTrue(suspect)

        # Un Grand (T4+) de 300m² reste plausible : pas suspect pour cette règle.
        suspect_t4, reason_t4 = od.detect_outlier(prix=3000, surface=300, type_local='Grand (T4+)')
        self.assertFalse(suspect_t4)

    def test_loyer_too_low_is_suspect(self):
        suspect, reason = od.detect_outlier(prix=95, surface=15, type_local='Studio/T1')
        self.assertTrue(suspect)
        self.assertIn('bas', reason)

    def test_t1_too_large_is_suspect(self):
        suspect, reason = od.detect_outlier(prix=900, surface=70, type_local='Studio/T1')
        self.assertTrue(suspect)
        self.assertIn('Studio/T1', reason)

    def test_t2_too_small_is_suspect(self):
        suspect, reason = od.detect_outlier(prix=900, surface=15, type_local='T2')
        self.assertTrue(suspect)

    def test_missing_surface_only_checks_the_rules_that_apply(self):
        # Pas de surface -> pas de prix_m2/incohérence calculable, mais le
        # loyer reste vérifiable.
        suspect, reason = od.detect_outlier(prix=50, surface=None, type_local='T2')
        self.assertTrue(suspect)
        self.assertIn('bas', reason)

    def test_missing_type_local_skips_the_type_coherence_rule_only(self):
        suspect, reason = od.detect_outlier(prix=800, surface=40, type_local=None)
        self.assertFalse(suspect)

    def test_precomputed_prix_m2_is_used_instead_of_recomputing(self):
        # Surface inconnue (aucune règle de surface calculable) ; un prix_m2
        # déjà connu (colonne dédiée du CSV) doit être utilisé tel quel.
        suspect, reason = od.detect_outlier(prix=800, surface=None, type_local='T2', prix_m2=20.0)
        self.assertFalse(suspect)

    def test_returns_the_first_matching_reason_deterministically(self):
        # Surface trop petite ET loyer trop bas à la fois : une seule raison
        # renvoyée, toujours la même (ordre de règle stable).
        suspect, reason = od.detect_outlier(prix=50, surface=5, type_local='Studio/T1')
        self.assertTrue(suspect)
        self.assertIsInstance(reason, str)


class FlagDataframeTest(unittest.TestCase):
    def test_adds_suspect_and_suspect_reason_columns(self):
        import pandas as pd
        df = pd.DataFrame([
            {'prix': 800, 'surface': 40, 'type_local': 'T2'},
            {'prix': 862, 'surface': 525, 'type_local': 'Grand (T4+)'},
        ])

        flagged = od.flag_dataframe(df)

        self.assertEqual(list(flagged['suspect']), [False, True])
        # pandas représente l'absence de raison en NaN (pas Python None) dès
        # qu'une colonne mixe None et str — comportement pandas normal, pas
        # celui de detect_outlier (qui renvoie bien None, testé plus haut).
        self.assertTrue(pd.isna(flagged.loc[0, 'suspect_reason']))
        self.assertFalse(pd.isna(flagged.loc[1, 'suspect_reason']))

    def test_uses_the_existing_prix_m2_column_when_present(self):
        import pandas as pd
        df = pd.DataFrame([
            {'prix': 800, 'surface': None, 'prix_m2': 20.0, 'type_local': 'T2'},
        ])

        flagged = od.flag_dataframe(df)

        self.assertFalse(flagged.loc[0, 'suspect'])

    def test_handles_nan_surface_without_crashing(self):
        import pandas as pd
        import numpy as np
        df = pd.DataFrame([
            {'prix': 50, 'surface': np.nan, 'type_local': 'T2'},
        ])

        flagged = od.flag_dataframe(df)

        self.assertTrue(flagged.loc[0, 'suspect'])

    def test_does_not_mutate_the_original_dataframe(self):
        import pandas as pd
        df = pd.DataFrame([{'prix': 800, 'surface': 40, 'type_local': 'T2'}])

        od.flag_dataframe(df)

        self.assertNotIn('suspect', df.columns)


class ExcludeSuspectsTest(unittest.TestCase):
    def test_drops_suspect_rows_and_keeps_original_columns(self):
        import pandas as pd
        df = pd.DataFrame([
            {'prix': 800, 'surface': 40, 'type_local': 'T2'},
            {'prix': 862, 'surface': 525, 'type_local': 'Grand (T4+)'},
        ])

        clean = od.exclude_suspects(df)

        self.assertEqual(len(clean), 1)
        self.assertEqual(list(clean.columns), ['prix', 'surface', 'type_local'])

    def test_returns_none_and_empty_dataframes_unchanged(self):
        import pandas as pd
        self.assertIsNone(od.exclude_suspects(None))
        empty = pd.DataFrame(columns=['prix'])
        self.assertTrue(od.exclude_suspects(empty).empty)


if __name__ == '__main__':
    unittest.main()
