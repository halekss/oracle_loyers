import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.view_counter import ViewCounterService


class ViewCounterServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.tmp_dir, "listing_views.json")
        self.service = ViewCounterService(self.storage_path)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_get_count_returns_zero_for_unknown_listing(self):
        self.assertEqual(self.service.get_count("42"), 0)

    def test_increment_returns_new_count(self):
        self.assertEqual(self.service.increment("42"), 1)
        self.assertEqual(self.service.increment("42"), 2)

    def test_increment_persists_across_instances(self):
        self.service.increment("42")
        self.service.increment("42")

        reloaded = ViewCounterService(self.storage_path)

        self.assertEqual(reloaded.get_count("42"), 2)

    def test_counts_are_isolated_per_listing_id(self):
        self.service.increment("1")
        self.service.increment("2")
        self.service.increment("2")

        self.assertEqual(self.service.get_count("1"), 1)
        self.assertEqual(self.service.get_count("2"), 2)

    def test_creates_storage_directory_if_missing(self):
        nested_path = os.path.join(self.tmp_dir, "nested", "listing_views.json")
        service = ViewCounterService(nested_path)

        service.increment("1")

        self.assertTrue(os.path.exists(nested_path))

    def test_does_not_leave_temp_files_behind(self):
        self.service.increment("1")

        remaining = os.listdir(self.tmp_dir)

        self.assertEqual(remaining, ["listing_views.json"])


if __name__ == "__main__":
    unittest.main()
