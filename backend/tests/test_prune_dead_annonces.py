import os
import sys
import tempfile
import unittest
from unittest.mock import Mock

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import prune_dead_annonces
from services import annonces_store


class CheckUrlStatusTest(unittest.TestCase):
    def test_returns_true_on_404(self):
        session = Mock()
        session.get.return_value = Mock(status_code=404)

        self.assertTrue(prune_dead_annonces.check_url_status("https://example.com/x", session))

    def test_returns_true_on_410(self):
        session = Mock()
        session.get.return_value = Mock(status_code=410)

        self.assertTrue(prune_dead_annonces.check_url_status("https://example.com/x", session))

    def test_returns_false_on_200(self):
        session = Mock()
        session.get.return_value = Mock(status_code=200)

        self.assertFalse(prune_dead_annonces.check_url_status("https://example.com/x", session))

    def test_returns_none_on_ambiguous_status(self):
        session = Mock()
        session.get.return_value = Mock(status_code=403)

        self.assertIsNone(prune_dead_annonces.check_url_status("https://example.com/x", session))

    def test_returns_none_on_request_exception(self):
        session = Mock()
        session.get.side_effect = requests.ConnectionError("boom")

        self.assertIsNone(prune_dead_annonces.check_url_status("https://example.com/x", session))


class PruneDeadAnnoncesTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        annonces_store.init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _seed(self, *urls):
        for url in urls:
            annonces_store.upsert_annonce(url=url, db_path=self.db_path)

    def test_deletes_only_confirmed_dead_urls(self):
        self._seed(
            "https://example.com/dead",
            "https://example.com/alive",
            "https://example.com/ambiguous",
        )
        statuses = {
            "https://example.com/dead": True,
            "https://example.com/alive": False,
            "https://example.com/ambiguous": None,
        }
        checker = lambda url, session: statuses[url]  # noqa: E731

        result = prune_dead_annonces.prune_dead_annonces(
            db_path=self.db_path, delay_range=(0, 0), checker=checker
        )

        self.assertEqual(result, {"checked": 3, "dead": 1, "deleted": 1, "ambiguous": 1})
        remaining_urls = {a["url"] for a in annonces_store.list_annonces(db_path=self.db_path, per_page=50)["items"]}
        self.assertEqual(remaining_urls, {"https://example.com/alive", "https://example.com/ambiguous"})

    def test_dry_run_does_not_delete_anything(self):
        self._seed("https://example.com/dead")
        checker = lambda url, session: True  # noqa: E731

        result = prune_dead_annonces.prune_dead_annonces(
            db_path=self.db_path, delay_range=(0, 0), checker=checker, dry_run=True
        )

        self.assertEqual(result, {"checked": 1, "dead": 1, "deleted": 0, "ambiguous": 0})
        self.assertEqual(annonces_store.list_annonces(db_path=self.db_path)["total"], 1)

    def test_deleting_earlier_rows_does_not_skip_later_ones(self):
        # Garde-fou contre le bug classique de pagination OFFSET/LIMIT quand on
        # supprime des lignes en cours de parcours.
        urls = [f"https://example.com/{i}" for i in range(120)]
        self._seed(*urls)
        checker = lambda url, session: True  # noqa: E731

        result = prune_dead_annonces.prune_dead_annonces(
            db_path=self.db_path, delay_range=(0, 0), checker=checker
        )

        self.assertEqual(result["checked"], 120)
        self.assertEqual(result["deleted"], 120)
        self.assertEqual(annonces_store.list_annonces(db_path=self.db_path)["total"], 0)


if __name__ == "__main__":
    unittest.main()
