import json
import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from monitor_drift import build_drift_report, compute_drift, run, select_reference_snapshot


class ComputeDriftTest(unittest.TestCase):
    def test_identical_distributions_are_not_flagged_as_drifted(self):
        df = pd.DataFrame({
            'surface': [40, 45, 50, 55, 60, 65, 70],
            'prix': [800, 850, 900, 950, 1000, 1050, 1100],
            'nb_vice_bar_500m': [1, 2, 3, 4, 5, 6, 7],
            'id_annonce': range(7),
        })

        results, target_drift = compute_drift(df, df.copy())

        self.assertTrue(all(not r['drifted'] for r in results))
        self.assertIsNotNone(target_drift)
        self.assertFalse(target_drift['drifted'])
        feature_names = [r['feature'] for r in results]
        self.assertNotIn('nb_vice_bar_500m', feature_names)
        self.assertNotIn('id_annonce', feature_names)

    def test_shifted_distribution_is_flagged_as_drifted(self):
        reference = pd.DataFrame({'surface': list(range(1, 101)), 'prix': list(range(1, 101))})
        current = pd.DataFrame({'surface': list(range(1000, 1100)), 'prix': list(range(1, 101))})

        results, target_drift = compute_drift(reference, current)
        surface_result = next(r for r in results if r['feature'] == 'surface')

        self.assertTrue(surface_result['drifted'])
        self.assertGreater(surface_result['ks_statistic'], 0.5)
        self.assertFalse(target_drift['drifted'])

    def test_returns_none_target_drift_when_target_column_absent(self):
        df = pd.DataFrame({'surface': [40, 50, 60, 70]})

        results, target_drift = compute_drift(df, df.copy())

        self.assertIsNone(target_drift)

    def test_ignores_columns_with_fewer_than_two_values(self):
        reference = pd.DataFrame({'surface': [40], 'prix': [800]})
        current = pd.DataFrame({'surface': [1000], 'prix': [800]})

        results, target_drift = compute_drift(reference, current)

        self.assertEqual(results, [])


class SelectReferenceSnapshotTest(unittest.TestCase):
    def test_returns_none_with_fewer_than_two_snapshots(self):
        manifest = pd.DataFrame([
            {'timestamp': 't0', 'sha256': 'a', 'snapshot_file': 'a.csv', 'row_count': 10},
        ])

        self.assertIsNone(select_reference_snapshot(manifest))

    def test_falls_back_to_oldest_when_history_shorter_than_window(self):
        manifest = pd.DataFrame([
            {'timestamp': 't0', 'sha256': 'a', 'snapshot_file': 'a.csv', 'row_count': 10},
            {'timestamp': 't1', 'sha256': 'b', 'snapshot_file': 'b.csv', 'row_count': 11},
            {'timestamp': 't2', 'sha256': 'c', 'snapshot_file': 'c.csv', 'row_count': 12},
        ])

        reference = select_reference_snapshot(manifest, window=7)

        self.assertEqual(reference['snapshot_file'], 'a.csv')

    def test_picks_snapshot_n_runs_ago_when_enough_history(self):
        manifest = pd.DataFrame([
            {'timestamp': f't{i}', 'sha256': str(i), 'snapshot_file': f'{i}.csv', 'row_count': 10 + i}
            for i in range(10)
        ])

        reference = select_reference_snapshot(manifest, window=3)

        self.assertEqual(reference['snapshot_file'], '6.csv')


class BuildDriftReportTest(unittest.TestCase):
    def test_report_reflects_no_drift(self):
        df = pd.DataFrame({'surface': [40, 50, 60], 'prix': [800, 900, 1000]})
        reference_row = {'snapshot_file': 'ref.csv', 'timestamp': 't0', 'row_count': 3}

        report = build_drift_report(df, df.copy(), reference_row=reference_row)

        self.assertEqual(report['status'], 'ok')
        self.assertFalse(report['any_drift_detected'])
        self.assertEqual(report['reference_snapshot'], 'ref.csv')
        self.assertEqual(report['current_row_count'], 3)

    def test_report_reflects_drift(self):
        reference = pd.DataFrame({'surface': list(range(1, 51)), 'prix': list(range(1, 51))})
        current = pd.DataFrame({'surface': list(range(1000, 1050)), 'prix': list(range(1, 51))})
        reference_row = {'snapshot_file': 'ref.csv', 'timestamp': 't0', 'row_count': 50}

        report = build_drift_report(reference, current, reference_row=reference_row)

        self.assertEqual(report['status'], 'drift_detected')
        self.assertTrue(report['any_drift_detected'])


class RunTest(unittest.TestCase):
    def test_reports_insufficient_history_with_a_single_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_path = os.path.join(tmp_dir, "master_immo_final.csv")
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            reports_dir = os.path.join(tmp_dir, "drift_reports")
            os.makedirs(snapshots_dir)

            pd.DataFrame({'surface': [40, 50], 'prix': [800, 900]}).to_csv(data_path, index=False)
            snapshot_file = "master_immo_final_abc123.csv"
            pd.DataFrame({'surface': [40, 50], 'prix': [800, 900]}).to_csv(
                os.path.join(snapshots_dir, snapshot_file), index=False
            )
            with open(os.path.join(snapshots_dir, "manifest.csv"), "w", encoding="utf-8-sig") as f:
                f.write("timestamp,sha256,snapshot_file,row_count\n")
                f.write(f"2026-01-01T00:00:00+00:00,abc123,{snapshot_file},2\n")

            exit_code = run(data_path, snapshots_dir, reports_dir)

            self.assertEqual(exit_code, 0)
            with open(os.path.join(reports_dir, "drift_report_latest.json"), encoding="utf-8") as f:
                report = json.load(f)
            self.assertEqual(report['status'], 'insufficient_history')

    def test_reports_insufficient_history_without_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_path = os.path.join(tmp_dir, "master_immo_final.csv")
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            reports_dir = os.path.join(tmp_dir, "drift_reports")

            pd.DataFrame({'surface': [40, 50], 'prix': [800, 900]}).to_csv(data_path, index=False)

            exit_code = run(data_path, snapshots_dir, reports_dir)

            self.assertEqual(exit_code, 0)
            with open(os.path.join(reports_dir, "drift_report_latest.json"), encoding="utf-8") as f:
                report = json.load(f)
            self.assertEqual(report['status'], 'insufficient_history')

    def test_detects_drift_between_reference_and_current_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_path = os.path.join(tmp_dir, "master_immo_final.csv")
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            reports_dir = os.path.join(tmp_dir, "drift_reports")
            os.makedirs(snapshots_dir)

            reference_file = "master_immo_final_ref.csv"
            pd.DataFrame({'surface': list(range(1, 51)), 'prix': list(range(1, 51))}).to_csv(
                os.path.join(snapshots_dir, reference_file), index=False
            )
            pd.DataFrame({'surface': list(range(1000, 1050)), 'prix': list(range(1, 51))}).to_csv(
                data_path, index=False
            )
            with open(os.path.join(snapshots_dir, "manifest.csv"), "w", encoding="utf-8-sig") as f:
                f.write("timestamp,sha256,snapshot_file,row_count\n")
                f.write(f"2026-01-01T00:00:00+00:00,ref,{reference_file},50\n")
                f.write(f"2026-01-02T00:00:00+00:00,cur,{reference_file},50\n")

            exit_code = run(data_path, snapshots_dir, reports_dir, window=1)

            self.assertEqual(exit_code, 1)
            with open(os.path.join(reports_dir, "drift_report_latest.json"), encoding="utf-8") as f:
                report = json.load(f)
            self.assertEqual(report['status'], 'drift_detected')
            self.assertTrue(any(r['feature'] == 'surface' and r['drifted'] for r in report['features']))

            with open(os.path.join(reports_dir, "drift_history.jsonl"), encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
            self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()
