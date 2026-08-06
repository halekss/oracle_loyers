import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

import prune_dead_map_listings


class PruneDeadMapListingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.csv_path = os.path.join(self.tmp_dir.name, "master_immo_final.csv")
        self.fake_map_script = os.path.join(self.tmp_dir.name, "fake_generate_map.py")
        with open(self.fake_map_script, "w") as f:
            f.write("print('map regenerated')\n")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_csv(self, rows):
        pd.DataFrame(rows).to_csv(self.csv_path, index=False)

    def test_removes_only_confirmed_dead_rows(self):
        self._write_csv([
            {"id_annonce": 1, "url": "https://example.com/alive", "prix": 800},
            {"id_annonce": 2, "url": "https://example.com/dead-http", "prix": 700},
            {"id_annonce": 3, "url": "https://example.com/ambiguous", "prix": 900},
        ])
        http_statuses = {
            "https://example.com/alive": False,
            "https://example.com/dead-http": True,
            "https://example.com/ambiguous": None,
        }
        checker = lambda url, session: http_statuses[url]  # noqa: E731
        browser_checker = MagicMock(return_value=True)
        fake_driver = MagicMock()

        result = prune_dead_map_listings.prune_dead_map_listings(
            csv_path=self.csv_path,
            delay_range=(0, 0),
            browser_delay_range=(0, 0),
            checker=checker,
            browser_checker=browser_checker,
            driver_factory=lambda: fake_driver,
            generate_map_script=self.fake_map_script,
        )

        self.assertEqual(result["total"], 3)
        self.assertEqual(result["dead"], 2)
        self.assertEqual(result["deleted"], 2)
        remaining = pd.read_csv(self.csv_path)
        self.assertEqual(list(remaining["url"]), ["https://example.com/alive"])

    def test_dry_run_does_not_modify_csv_or_regenerate_map(self):
        self._write_csv([{"id_annonce": 1, "url": "https://example.com/dead", "prix": 700}])
        checker = lambda url, session: True  # noqa: E731

        with patch("prune_dead_map_listings.subprocess.run") as mock_run:
            result = prune_dead_map_listings.prune_dead_map_listings(
                csv_path=self.csv_path,
                delay_range=(0, 0),
                dry_run=True,
                checker=checker,
                generate_map_script=self.fake_map_script,
            )
            mock_run.assert_not_called()

        self.assertEqual(result["deleted"], 0)
        remaining = pd.read_csv(self.csv_path)
        self.assertEqual(len(remaining), 1)

    def test_regenerates_map_after_real_deletion(self):
        self._write_csv([{"id_annonce": 1, "url": "https://example.com/dead", "prix": 700}])
        checker = lambda url, session: True  # noqa: E731

        with patch("prune_dead_map_listings.subprocess.run") as mock_run:
            prune_dead_map_listings.prune_dead_map_listings(
                csv_path=self.csv_path,
                delay_range=(0, 0),
                checker=checker,
                generate_map_script=self.fake_map_script,
            )
            mock_run.assert_called_once()
            self.assertIn(self.fake_map_script, mock_run.call_args[0][0])

    def test_skip_map_regen_does_not_call_subprocess(self):
        self._write_csv([{"id_annonce": 1, "url": "https://example.com/dead", "prix": 700}])
        checker = lambda url, session: True  # noqa: E731

        with patch("prune_dead_map_listings.subprocess.run") as mock_run:
            prune_dead_map_listings.prune_dead_map_listings(
                csv_path=self.csv_path,
                delay_range=(0, 0),
                checker=checker,
                regenerate_map=False,
                generate_map_script=self.fake_map_script,
            )
            mock_run.assert_not_called()

    def test_no_deletion_does_not_touch_csv_or_regenerate_map(self):
        self._write_csv([{"id_annonce": 1, "url": "https://example.com/alive", "prix": 700}])
        checker = lambda url, session: False  # noqa: E731
        original_mtime = os.path.getmtime(self.csv_path)

        with patch("prune_dead_map_listings.subprocess.run") as mock_run:
            result = prune_dead_map_listings.prune_dead_map_listings(
                csv_path=self.csv_path,
                delay_range=(0, 0),
                checker=checker,
                generate_map_script=self.fake_map_script,
            )
            mock_run.assert_not_called()

        self.assertEqual(result["deleted"], 0)
        self.assertEqual(os.path.getmtime(self.csv_path), original_mtime)

    def test_rows_with_missing_url_are_skipped_not_deleted(self):
        self._write_csv([
            {"id_annonce": 1, "url": None, "prix": 700},
            {"id_annonce": 2, "url": "https://example.com/alive", "prix": 800},
        ])
        checker = MagicMock(return_value=False)

        result = prune_dead_map_listings.prune_dead_map_listings(
            csv_path=self.csv_path,
            delay_range=(0, 0),
            checker=checker,
            generate_map_script=self.fake_map_script,
        )

        self.assertEqual(checker.call_count, 1)
        self.assertEqual(checker.call_args[0][0], "https://example.com/alive")
        self.assertEqual(result["dead"], 0)


if __name__ == "__main__":
    unittest.main()
