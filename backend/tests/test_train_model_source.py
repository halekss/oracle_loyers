"""ORA-181 : option d'entraînement sur master + archive (en plus du master
seul, comportement historique inchangé par défaut).

Ne teste QUE la préparation des données (`load_source_dataframe`) et la
comparaison de sources (`compare_sources`), en pointant vers un dossier
`data/` temporaire — jamais les vrais fichiers versionnés ni un entraînement
XGBoost complet (trop lourd/lent pour un test unitaire), sauf pour
`compare_sources` où un XGBoost minimal sur quelques lignes reste rapide."""
import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from scripts import train_model  # noqa: E402


MASTER_COLUMNS = ['id_annonce', 'site', 'prix', 'surface', 'url', 'ville', 'quartier', 'type_local']
ARCHIVE_COLUMNS = MASTER_COLUMNS + ['statut', 'archive_le']


def _write_csv(path, columns, rows):
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


class LoadSourceDataframeTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.data_dir = os.path.join(self.tmp_dir.name, 'data')
        os.makedirs(self.data_dir)
        self.master_path = os.path.join(self.data_dir, 'master_immo_final.csv')
        self.archive_path = os.path.join(self.data_dir, 'master_archive.csv')

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_master_source_returns_only_master_rows_for_the_ville_unchanged(self):
        _write_csv(self.master_path, MASTER_COLUMNS, [
            [1, 'Vizzit', 800, 40, 'https://x/1', 'Lyon', 'Gerland', 'T2'],
            [2, 'Vizzit', 900, 45, 'https://x/2', 'Lille', 'Wazemmes', 'T2'],
        ])

        df = train_model.load_source_dataframe('lyon', source='master', data_dir=self.data_dir)

        self.assertEqual(list(df['url']), ['https://x/1'])

    def test_master_archive_source_adds_archive_rows_for_the_same_ville(self):
        _write_csv(self.master_path, MASTER_COLUMNS, [
            [1, 'Vizzit', 800, 40, 'https://x/1', 'Lyon', 'Gerland', 'T2'],
        ])
        _write_csv(self.archive_path, ARCHIVE_COLUMNS, [
            [2, 'Vizzit', 700, 35, 'https://x/2', 'Lyon', 'Croix-Rousse', 'T1', 'a_verifier', '2026-01-01'],
            [3, 'Vizzit', 950, 50, 'https://x/3', 'Lille', 'Wazemmes', 'T3', 'active', '2026-01-01'],
        ])

        df = train_model.load_source_dataframe('lyon', source='master_archive', data_dir=self.data_dir)

        self.assertEqual(sorted(df['url']), ['https://x/1', 'https://x/2'])

    def test_excludes_archive_rows_with_statut_inactive(self):
        _write_csv(self.master_path, MASTER_COLUMNS, [
            [1, 'Vizzit', 800, 40, 'https://x/1', 'Lyon', 'Gerland', 'T2'],
        ])
        _write_csv(self.archive_path, ARCHIVE_COLUMNS, [
            [2, 'Vizzit', 700, 35, 'https://x/2', 'Lyon', 'Croix-Rousse', 'T1', 'inactive', '2026-01-01'],
            [3, 'Vizzit', 650, 30, 'https://x/3', 'Lyon', 'Perrache', 'T1', 'a_verifier', '2026-01-01'],
        ])

        df = train_model.load_source_dataframe('lyon', source='master_archive', data_dir=self.data_dir)

        self.assertEqual(sorted(df['url']), ['https://x/1', 'https://x/3'])

    def test_master_wins_when_a_url_exists_in_both(self):
        _write_csv(self.master_path, MASTER_COLUMNS, [
            [1, 'Vizzit', 800, 40, 'https://x/1', 'Lyon', 'Gerland', 'T2'],
        ])
        _write_csv(self.archive_path, ARCHIVE_COLUMNS, [
            [1, 'Vizzit', 650, 40, 'https://x/1', 'Lyon', 'Gerland', 'T2', 'a_verifier', '2026-01-01'],
        ])

        df = train_model.load_source_dataframe('lyon', source='master_archive', data_dir=self.data_dir)

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['prix'], 800)

    def test_keeps_only_the_most_recent_archive_row_per_url(self):
        _write_csv(self.master_path, MASTER_COLUMNS, [])
        _write_csv(self.archive_path, ARCHIVE_COLUMNS, [
            [1, 'Vizzit', 700, 40, 'https://x/1', 'Lyon', 'Gerland', 'T2', 'a_verifier', '2026-01-01'],
            [2, 'Vizzit', 750, 40, 'https://x/1', 'Lyon', 'Gerland', 'T2', 'a_verifier', '2026-02-01'],
        ])

        df = train_model.load_source_dataframe('lyon', source='master_archive', data_dir=self.data_dir)

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['prix'], 750)

    def test_falls_back_to_master_only_when_archive_file_is_absent(self):
        _write_csv(self.master_path, MASTER_COLUMNS, [
            [1, 'Vizzit', 800, 40, 'https://x/1', 'Lyon', 'Gerland', 'T2'],
        ])

        df = train_model.load_source_dataframe('lyon', source='master_archive', data_dir=self.data_dir)

        self.assertEqual(list(df['url']), ['https://x/1'])

    def test_rejects_an_unknown_source(self):
        _write_csv(self.master_path, MASTER_COLUMNS, [])

        with self.assertRaises(ValueError):
            train_model.load_source_dataframe('lyon', source='bogus', data_dir=self.data_dir)


class CompareSourcesTest(unittest.TestCase):
    """`compare_sources` ne doit rien sauvegarder/promouvoir (ORA-181 :
    comparer AVANT de changer le défaut) — juste renvoyer les métriques des
    deux sources pour un affichage/decision humaine."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.data_dir = os.path.join(self.tmp_dir.name, 'data')
        os.makedirs(self.data_dir)
        self.master_path = os.path.join(self.data_dir, 'master_immo_final.csv')
        self.archive_path = os.path.join(self.data_dir, 'master_archive.csv')

        # Assez de lignes pour que train_test_split (test_size=0.2) ait au
        # moins une ligne de chaque côté.
        rows = [
            [i, 'Vizzit', 500 + i * 10, 30 + i, f'https://x/{i}', 'Lyon', 'Gerland', 'T2']
            for i in range(10)
        ]
        _write_csv(self.master_path, MASTER_COLUMNS, rows)
        archive_rows = [
            [100 + i, 'Vizzit', 500 + i * 10, 30 + i, f'https://y/{i}', 'Lyon', 'Gerland', 'T2', 'a_verifier', '2026-01-01']
            for i in range(10)
        ]
        _write_csv(self.archive_path, ARCHIVE_COLUMNS, archive_rows)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_returns_mae_r2_and_dataset_size_for_both_sources(self):
        results = train_model.compare_sources('lyon', data_dir=self.data_dir)

        self.assertEqual(set(results.keys()), {'master', 'master_archive'})
        for source, metrics in results.items():
            self.assertIn('mae', metrics)
            self.assertIn('r2', metrics)
            self.assertIn('dataset_size', metrics)

    def test_master_archive_dataset_is_larger_than_master_alone(self):
        results = train_model.compare_sources('lyon', data_dir=self.data_dir)

        self.assertGreater(results['master_archive']['dataset_size'], results['master']['dataset_size'])


if __name__ == '__main__':
    unittest.main()
