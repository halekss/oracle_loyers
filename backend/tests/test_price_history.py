import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.price_history import compute_price_history, compute_price_history_from_listings


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
            self.assertEqual(historique[0]["date"], "2026-01-01")
            self.assertEqual(historique[0]["count"], 2)
            self.assertEqual(historique[1]["date"], "2026-01-08")
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
            self.assertEqual(historique[0]["date"], "2026-01-08")

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

    def test_aggregates_multiple_snapshots_on_the_same_calendar_day_into_one_point(self):
        """ORA-199 : un run rejoué le même jour (manifest.csv, ex. reprise
        après échec) ne doit pas produire deux points pour la même date —
        agrégation par jour, pas par ligne de manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            os.makedirs(snapshots_dir)

            pd.DataFrame({
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [800], 'surface': [40],
                'prix_m2': [20], 'type_local': ['T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap1.csv"), index=False)
            pd.DataFrame({
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [900], 'surface': [45],
                'prix_m2': [20], 'type_local': ['T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap1bis.csv"), index=False)
            pd.DataFrame({
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [1000], 'surface': [40],
                'prix_m2': [25], 'type_local': ['T2'],
            }).to_csv(os.path.join(snapshots_dir, "snap2.csv"), index=False)
            manifest_path = _write_manifest(snapshots_dir, [
                {"timestamp": "2026-01-01T08:00:00+00:00", "sha256": "a", "snapshot_file": "snap1.csv", "row_count": 1},
                {"timestamp": "2026-01-01T20:00:00+00:00", "sha256": "a2", "snapshot_file": "snap1bis.csv", "row_count": 1},
                {"timestamp": "2026-01-08T08:00:00+00:00", "sha256": "b", "snapshot_file": "snap2.csv", "row_count": 1},
            ])

            historique, status = compute_price_history("Gerland", "Tout", snapshots_dir, manifest_path)

            self.assertEqual(status, "ok")
            self.assertEqual(len(historique), 2, "un seul point pour le 2026-01-01, malgré 2 snapshots ce jour-là")
            self.assertEqual(historique[0]["date"], "2026-01-01")
            self.assertEqual(historique[0]["count"], 2)
            self.assertEqual(historique[0]["prix_m2_moyen"], 20)

    def test_excludes_suspect_rows_from_the_average(self):
        """ORA-195/ORA-199 : une annonce suspecte (prix/m² aberrant) ne doit
        pas fausser la moyenne de l'historique."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshots_dir = os.path.join(tmp_dir, "snapshots")
            os.makedirs(snapshots_dir)

            pd.DataFrame({
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Gerland', 'Gerland'],
                'prix': [800, 862], 'surface': [40, 525],
                'prix_m2': [20, 1.6], 'type_local': ['T2', 'Grand (T4+)'],
            }).to_csv(os.path.join(snapshots_dir, "snap1.csv"), index=False)
            manifest_path = _write_manifest(snapshots_dir, [
                {"timestamp": "2026-01-01T00:00:00+00:00", "sha256": "a", "snapshot_file": "snap1.csv", "row_count": 2},
                {"timestamp": "2026-01-08T00:00:00+00:00", "sha256": "b", "snapshot_file": "snap1.csv", "row_count": 2},
            ])

            historique, status = compute_price_history("Gerland", "Tout", snapshots_dir, manifest_path)

            self.assertEqual(status, "ok")
            self.assertEqual(historique[0]["count"], 1, "l'annonce suspecte (1.6€/m²) est exclue")
            self.assertEqual(historique[0]["prix_m2_moyen"], 20)


class ComputePriceHistoryFromListingsTest(unittest.TestCase):
    """ORA-182 : historique depuis master + archive plutôt que les snapshots
    périodiques — un point par date `date_dernier_scan` distincte."""

    def _write(self, path, rows):
        pd.DataFrame(rows).to_csv(path, index=False)

    def test_reports_insufficient_history_when_only_one_date_matches(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            master_path = os.path.join(tmp_dir, "master.csv")
            archive_path = os.path.join(tmp_dir, "archive.csv")
            self._write(master_path, {
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [900], 'surface': [45],
                'prix_m2': [20], 'type_local': ['T2'], 'date_dernier_scan': ['2026-09-26'],
            })
            self._write(archive_path, {
                'ville': [], 'quartier': [], 'prix': [], 'surface': [],
                'prix_m2': [], 'type_local': [], 'date_dernier_scan': [],
            })

            historique, status = compute_price_history_from_listings("Gerland", "Tout", master_path, archive_path)

            self.assertEqual(status, "insufficient_history")
            self.assertEqual(historique, [])

    def test_reports_insufficient_history_when_files_are_missing(self):
        historique, status = compute_price_history_from_listings(
            "Gerland", "Tout", "/no/such/master.csv", "/no/such/archive.csv",
        )

        self.assertEqual(status, "insufficient_history")
        self.assertEqual(historique, [])

    def test_combines_master_and_archive_into_one_chronological_history(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            master_path = os.path.join(tmp_dir, "master.csv")
            archive_path = os.path.join(tmp_dir, "archive.csv")
            # Archive : deux dates plus anciennes (annonces sorties du master).
            self._write(archive_path, {
                'ville': ['Lyon', 'Lyon', 'Lyon'],
                'quartier': ['Gerland', 'Gerland', 'Gerland'],
                'prix': [800, 850, 900],
                'surface': [40, 40, 45],
                'prix_m2': [20, 21.25, 20],
                'type_local': ['T2', 'T2', 'T2'],
                'date_dernier_scan': ['2026-08-12', '2026-08-12', '2026-09-24'],
            })
            # Master : dernier run seulement, une seule date (toujours la plus récente).
            self._write(master_path, {
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [1000], 'surface': [45],
                'prix_m2': [22.2], 'type_local': ['T2'], 'date_dernier_scan': ['2026-09-26'],
            })

            historique, status = compute_price_history_from_listings("Gerland", "Tout", master_path, archive_path)

            self.assertEqual(status, "ok")
            self.assertEqual([p["date"] for p in historique], ["2026-08-12", "2026-09-24", "2026-09-26"])
            self.assertEqual(historique[0]["count"], 2)
            self.assertEqual(historique[0]["prix_m2_moyen"], round((20 + 21.25) / 2, 0))
            self.assertEqual(historique[2]["count"], 1)
            self.assertEqual(historique[2]["prix_m2_moyen"], 22)

    def test_skips_dates_without_any_matching_quartier(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            master_path = os.path.join(tmp_dir, "master.csv")
            archive_path = os.path.join(tmp_dir, "archive.csv")
            self._write(archive_path, {
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Confluence', 'Gerland'],
                'prix': [800, 900], 'surface': [40, 45], 'prix_m2': [20, 20],
                'type_local': ['T2', 'T2'], 'date_dernier_scan': ['2026-08-12', '2026-09-24'],
            })
            self._write(master_path, {
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [1000], 'surface': [45],
                'prix_m2': [22.2], 'type_local': ['T2'], 'date_dernier_scan': ['2026-09-26'],
            })

            historique, status = compute_price_history_from_listings("Gerland", "Tout", master_path, archive_path)

            self.assertEqual(status, "ok")
            self.assertEqual([p["date"] for p in historique], ["2026-09-24", "2026-09-26"])

    def test_filters_by_type_local(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            master_path = os.path.join(tmp_dir, "master.csv")
            archive_path = os.path.join(tmp_dir, "archive.csv")
            self._write(archive_path, {
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Gerland', 'Gerland'],
                'prix': [800, 1500], 'surface': [40, 70], 'prix_m2': [20, 21.4],
                'type_local': ['T2', 'T4'], 'date_dernier_scan': ['2026-08-12', '2026-08-12'],
            })
            self._write(master_path, {
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [900], 'surface': [45],
                'prix_m2': [20], 'type_local': ['T2'], 'date_dernier_scan': ['2026-09-26'],
            })

            historique, status = compute_price_history_from_listings("Gerland", "T2", master_path, archive_path)

            self.assertEqual(status, "ok")
            self.assertEqual(len(historique), 2)
            for point in historique:
                self.assertEqual(point["count"], 1)

    def test_scopes_quartier_search_to_the_given_ville(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            master_path = os.path.join(tmp_dir, "master.csv")
            archive_path = os.path.join(tmp_dir, "archive.csv")
            self._write(archive_path, {
                'ville': ['Lyon'], 'quartier': ['Ainay'], 'prix': [800], 'surface': [40],
                'prix_m2': [20], 'type_local': ['T2'], 'date_dernier_scan': ['2026-08-12'],
            })
            self._write(master_path, {
                'ville': ['Lyon'], 'quartier': ['Ainay'], 'prix': [900], 'surface': [45],
                'prix_m2': [20], 'type_local': ['T2'], 'date_dernier_scan': ['2026-09-26'],
            })

            historique, status = compute_price_history_from_listings(
                "Ainay", "Tout", master_path, archive_path, ville="lille",
            )

            self.assertEqual(status, "ok")
            self.assertEqual(historique, [])

    def test_uses_prix_over_surface_when_prix_m2_column_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            master_path = os.path.join(tmp_dir, "master.csv")
            archive_path = os.path.join(tmp_dir, "archive.csv")
            self._write(archive_path, {
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [800], 'surface': [40],
                'type_local': ['T2'], 'date_dernier_scan': ['2026-08-12'],
            })
            self._write(master_path, {
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [900], 'surface': [45],
                'type_local': ['T2'], 'date_dernier_scan': ['2026-09-26'],
            })

            historique, status = compute_price_history_from_listings("Gerland", "Tout", master_path, archive_path)

            self.assertEqual(status, "ok")
            self.assertEqual(historique[0]["prix_m2_moyen"], 20)
            self.assertEqual(historique[1]["prix_m2_moyen"], 20)

    def test_excludes_suspect_rows_from_the_average(self):
        """ORA-195/ORA-199 : une annonce suspecte ne doit pas fausser la
        moyenne de l'historique master+archive non plus."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            master_path = os.path.join(tmp_dir, "master.csv")
            archive_path = os.path.join(tmp_dir, "archive.csv")
            self._write(archive_path, {
                'ville': [], 'quartier': [], 'prix': [], 'surface': [],
                'type_local': [], 'date_dernier_scan': [],
            })
            self._write(master_path, {
                'ville': ['Lyon', 'Lyon'], 'quartier': ['Gerland', 'Gerland'],
                'prix': [800, 862], 'surface': [40, 525],
                'type_local': ['T2', 'Grand (T4+)'],
                'date_dernier_scan': ['2026-09-26', '2026-09-26'],
            })
            # Deuxième date pour dépasser le seuil "insufficient_history" (< 2 dates).
            self._write(archive_path, {
                'ville': ['Lyon'], 'quartier': ['Gerland'], 'prix': [900], 'surface': [45],
                'type_local': ['T2'], 'date_dernier_scan': ['2026-08-12'],
            })

            historique, status = compute_price_history_from_listings("Gerland", "Tout", master_path, archive_path)

            self.assertEqual(status, "ok")
            recent = next(p for p in historique if p["date"] == "2026-09-26")
            self.assertEqual(recent["count"], 1, "l'annonce suspecte (1.6€/m²) est exclue")
            self.assertEqual(recent["prix_m2_moyen"], 20)


if __name__ == "__main__":
    unittest.main()
