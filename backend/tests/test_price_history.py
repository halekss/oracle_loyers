import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.price_history import compute_price_history


def _write_manifest(snapshots_dir, rows):
    manifest_path = os.path.join(snapshots_dir, "manifest.csv")
    with open(manifest_path, "w", encoding="utf-8-sig") as f:
        f.write("timestamp,sha256,snapshot_file,row_count\n")
        for row in rows:
            f.write(f"{row['timestamp']},{row['sha256']},{row['snapshot_file']},{row['row_count']}\n")
    return manifest_path


class ComputePriceHistoryTest(unittest.TestCase):
    def test_reports_insufficient_history_with_a_single_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            os.makedirs(snapshots_dir)
            pd.DataFrame({
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [800], 'surface': [40], 'prix_m2': [20], 'type_local': ['T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap1.csv"), index=False)
            manifest_path = _write_manifest(snapshots_dir, [
                {"timestamp": "2026-01-01T00:00:00+00:00", "sha256": "a", "snapshot_file": "snap1.csv", "row_count": 1},
            ])

            historique, status = compute_price_history("Gerland", "Tout", snapshots_dir, manifest_path)

            self.assertEqual(status, "insufficient_history")
            self.assertEqual(historique, [])

    def test_reports_insufficient_history_without_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            os.makedirs(snapshots_dir)

            historique, status = compute_price_history(
                "Gerland", "Tout", snapshots_dir, os.path.join(snapshots_dir, "manifest.csv")
            )

            self.assertEqual(status, "insufficient_history")
            self.assertEqual(historique, [])

    def test_returns_one_point_per_snapshot_with_the_quartier(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            os.makedirs(snapshots_dir)

            pd.DataFrame({
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Gerland', 'Gerland'], 'prix': [800, 900], 'surface': [40, 45],
                'prix_m2': [20, 20], 'type_local': ['T2', 'T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap1.csv"), index=False)
            pd.DataFrame({
                'ville': ['Lyon', 'Lyon', 'Lyon'], 'quartier': ['Gerland', 'Gerland', 'Gerland'], 'prix': [850, 950, 1000], 'surface': [40, 45, 48],
                'prix_m2': [21.25, 21.1, 20.8], 'type_local': ['T2', 'T2', 'T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap2.csv"), index=False)
            manifest_path = _write_manifest(snapshots_dir, [
                {"timestamp": "2026-01-01T00:00:00+00:00", "sha256": "a", "snapshot_file": "snap1.csv", "row_count": 2},
                {"timestamp": "2026-01-08T00:00:00+00:00", "sha256": "b", "snapshot_file": "snap2.csv", "row_count": 3},
            ])

            historique, status = compute_price_history("Gerland", "Tout", snapshots_dir, manifest_path)

            self.assertEqual(status, "ok")
            self.assertEqual(len(historique), 2)
            self.assertEqual(historique[0]["date"], "2026-01-01T00:00:00+00:00")
            self.assertEqual(historique[0]["count"], 2)
            self.assertEqual(historique[1]["date"], "2026-01-08T00:00:00+00:00")
            self.assertEqual(historique[1]["count"], 3)

    def test_skips_snapshots_without_any_matching_quartier(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            os.makedirs(snapshots_dir)

            pd.DataFrame({
                'ville': ['Lyon'], 'quartier': ['Confluence'], 'prix': [800], 'surface': [40], 'prix_m2': [20], 'type_local': ['T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap1.csv"), index=False)
            pd.DataFrame({
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [900], 'surface': [45], 'prix_m2': [20], 'type_local': ['T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap2.csv"), index=False)
            manifest_path = _write_manifest(snapshots_dir, [
                {"timestamp": "2026-01-01T00:00:00+00:00", "sha256": "a", "snapshot_file": "snap1.csv", "row_count": 1},
                {"timestamp": "2026-01-08T00:00:00+00:00", "sha256": "b", "snapshot_file": "snap2.csv", "row_count": 1},
            ])

            historique, status = compute_price_history("Gerland", "Tout", snapshots_dir, manifest_path)

            self.assertEqual(status, "ok")
            self.assertEqual(len(historique), 1)
            self.assertEqual(historique[0]["date"], "2026-01-08T00:00:00+00:00")

    def test_tolerates_a_typo_in_the_quartier_name(self):
        """ORA-110 : même matching partagé (fuzzy) que /api/quartier-stats,
        au lieu d'un str.contains naïf par snapshot."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            os.makedirs(snapshots_dir)

            pd.DataFrame({
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Gerland', 'Gerland'], 'prix': [800, 900], 'surface': [40, 45],
                'prix_m2': [20, 20], 'type_local': ['T2', 'T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap1.csv"), index=False)
            pd.DataFrame({
                'ville': ['Lyon', 'Lyon', 'Lyon'], 'quartier': ['Gerland', 'Gerland', 'Gerland'], 'prix': [850, 950, 1000], 'surface': [40, 45, 48],
                'prix_m2': [21.25, 21.1, 20.8], 'type_local': ['T2', 'T2', 'T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap2.csv"), index=False)
            manifest_path = _write_manifest(snapshots_dir, [
                {"timestamp": "2026-01-01T00:00:00+00:00", "sha256": "a", "snapshot_file": "snap1.csv", "row_count": 2},
                {"timestamp": "2026-01-08T00:00:00+00:00", "sha256": "b", "snapshot_file": "snap2.csv", "row_count": 3},
            ])

            historique, status = compute_price_history("greland", "Tout", snapshots_dir, manifest_path)

            self.assertEqual(status, "ok")
            self.assertEqual(len(historique), 2)

    def test_scopes_quartier_search_to_the_given_ville(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            os.makedirs(snapshots_dir)

            pd.DataFrame({
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Ainay', 'Ainay'], 'prix': [800, 900], 'surface': [40, 45],
                'prix_m2': [20, 20], 'type_local': ['T2', 'T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap1.csv"), index=False)
            pd.DataFrame({
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Ainay', 'Ainay'], 'prix': [850, 950], 'surface': [40, 45],
                'prix_m2': [21.25, 21.1], 'type_local': ['T2', 'T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap2.csv"), index=False)
            manifest_path = _write_manifest(snapshots_dir, [
                {"timestamp": "2026-01-01T00:00:00+00:00", "sha256": "a", "snapshot_file": "snap1.csv", "row_count": 2},
                {"timestamp": "2026-01-08T00:00:00+00:00", "sha256": "b", "snapshot_file": "snap2.csv", "row_count": 2},
            ])

            # Régression réelle : chercher "Ainay" (quartier lyonnais) tout en
            # étant sur l'onglet Lille ne doit renvoyer aucun point d'historique.
            historique, status = compute_price_history("Ainay", "Tout", snapshots_dir, manifest_path, ville="lille")

            self.assertEqual(status, "ok")
            self.assertEqual(historique, [])

    def test_filters_by_type_local(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            os.makedirs(snapshots_dir)

            pd.DataFrame({
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Gerland', 'Gerland'], 'prix': [800, 1500], 'surface': [40, 70],
                'prix_m2': [20, 21.4], 'type_local': ['T2', 'T4'],
            }).to_csv(os.path.join(snapshots_dir, "snap1.csv"), index=False)
            pd.DataFrame({
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Gerland', 'Gerland'], 'prix': [850, 1600], 'surface': [40, 70],
                'prix_m2': [21.25, 22.85], 'type_local': ['T2', 'T4'],
            }).to_csv(os.path.join(snapshots_dir, "snap2.csv"), index=False)
            manifest_path = _write_manifest(snapshots_dir, [
                {"timestamp": "2026-01-01T00:00:00+00:00", "sha256": "a", "snapshot_file": "snap1.csv", "row_count": 2},
                {"timestamp": "2026-01-08T00:00:00+00:00", "sha256": "b", "snapshot_file": "snap2.csv", "row_count": 2},
            ])

            historique, status = compute_price_history("Gerland", "T2", snapshots_dir, manifest_path)

            self.assertEqual(status, "ok")
            self.assertEqual(len(historique), 2)
            for point in historique:
                self.assertEqual(point["count"], 1)


if __name__ == "__main__":
    unittest.main()
