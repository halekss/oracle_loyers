import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as app_module
from services.view_counter import ViewCounterService


class ListingViewsRouteTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.original_view_counter = app_module.view_counter
        app_module.view_counter = ViewCounterService(os.path.join(self.tmp_dir, "listing_views.json"))
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.view_counter = self.original_view_counter
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_get_returns_zero_views_for_unknown_listing(self):
        response = self.client.get("/api/listings/999/views")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"id": "999", "views": 0})

    def test_post_increments_and_returns_new_count(self):
        response = self.client.post("/api/listings/42/views")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {"id": "42", "views": 1})

    def test_multiple_posts_accumulate_and_get_reflects_it(self):
        self.client.post("/api/listings/42/views")
        self.client.post("/api/listings/42/views")

        response = self.client.get("/api/listings/42/views")

        self.assertEqual(response.get_json(), {"id": "42", "views": 2})

    def test_counts_are_isolated_per_listing(self):
        self.client.post("/api/listings/1/views")
        self.client.post("/api/listings/2/views")
        self.client.post("/api/listings/2/views")

        self.assertEqual(self.client.get("/api/listings/1/views").get_json()["views"], 1)
        self.assertEqual(self.client.get("/api/listings/2/views").get_json()["views"], 2)

    def test_post_enforces_its_own_rate_limit(self):
        os.environ["RATE_LIMIT_LISTING_VIEW"] = "2 per hour"
        try:
            statuses = [self.client.post("/api/listings/7/views").status_code for _ in range(3)]
            self.assertIn(429, statuses)
        finally:
            del os.environ["RATE_LIMIT_LISTING_VIEW"]


if __name__ == "__main__":
    unittest.main()
