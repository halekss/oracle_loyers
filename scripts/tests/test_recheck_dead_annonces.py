import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

import recheck_dead_annonces
from services import annonces_store


class LooksLikeValidListingTest(unittest.TestCase):
    def test_detects_price_pattern(self):
        self.assertTrue(recheck_dead_annonces.looks_like_valid_listing("<p>850 €</p>"))

    def test_detects_price_on_request_wording(self):
        self.assertTrue(recheck_dead_annonces.looks_like_valid_listing("<p>Loyer sur demande</p>"))

    def test_returns_false_when_no_price_signal_at_all(self):
        self.assertFalse(recheck_dead_annonces.looks_like_valid_listing("<h1>Bienvenue</h1>"))

    def test_handles_none_gracefully(self):
        self.assertFalse(recheck_dead_annonces.looks_like_valid_listing(None))


class CheckUrlStatusBrowserTest(unittest.TestCase):
    def _driver(self, current_url, page_source=""):
        driver = MagicMock()
        driver.current_url = current_url
        driver.page_source = page_source
        return driver

    def test_returns_true_when_redirected_to_homepage(self):
        driver = self._driver("https://example.com/", page_source="<html>Accueil</html>")

        result = recheck_dead_annonces.check_url_status_browser(
            "https://example.com/annonce/123", driver
        )

        self.assertTrue(result)

    def test_returns_true_on_soft_404_content(self):
        driver = self._driver(
            "https://example.com/annonce/123",
            page_source="<h1>Cette annonce n'est plus disponible</h1>",
        )

        result = recheck_dead_annonces.check_url_status_browser(
            "https://example.com/annonce/123", driver
        )

        self.assertTrue(result)

    def test_returns_false_for_normal_listing_page(self):
        driver = self._driver(
            "https://example.com/annonce/123",
            page_source="<h1>T2 Gerland</h1><p>850 € - 45 m2</p>",
        )

        result = recheck_dead_annonces.check_url_status_browser(
            "https://example.com/annonce/123", driver
        )

        self.assertFalse(result)

    def test_returns_true_when_no_price_signal_found(self):
        driver = self._driver(
            "https://example.com/annonce/123",
            page_source="<h1>Vous êtes bien sur notre site</h1><p>Découvrez nos services</p>",
        )

        result = recheck_dead_annonces.check_url_status_browser(
            "https://example.com/annonce/123", driver
        )

        self.assertTrue(result)

    def test_returns_false_for_price_on_request_listing(self):
        driver = self._driver(
            "https://example.com/annonce/123",
            page_source="<h1>Loft T3 Confluence</h1><p>Loyer sur demande</p>",
        )

        result = recheck_dead_annonces.check_url_status_browser(
            "https://example.com/annonce/123", driver
        )

        self.assertFalse(result)

    def test_returns_none_when_driver_raises(self):
        driver = MagicMock()
        driver.get.side_effect = Exception("navigation crashed")

        result = recheck_dead_annonces.check_url_status_browser(
            "https://example.com/annonce/123", driver
        )

        self.assertIsNone(result)

    def test_root_path_annonce_itself_is_not_treated_as_redirect(self):
        # Garde-fou : si l'url d'origine est déjà la racine du site, on ne doit
        # pas la traiter comme "redirigée vers l'accueil".
        driver = self._driver("https://example.com/", page_source="<p>850 €</p>")

        result = recheck_dead_annonces.check_url_status_browser("https://example.com/", driver)

        self.assertFalse(result)


class RecheckAmbiguousTest(unittest.TestCase):
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

    def test_only_escalates_http_ambiguous_urls_to_browser(self):
        self._seed(
            "https://example.com/alive",
            "https://example.com/dead-http",
            "https://example.com/ambiguous",
        )
        http_statuses = {
            "https://example.com/alive": False,
            "https://example.com/dead-http": True,
            "https://example.com/ambiguous": None,
        }
        http_checker = lambda url, session: http_statuses[url]  # noqa: E731
        browser_checker = MagicMock(return_value=True)
        fake_driver = MagicMock()

        result = recheck_dead_annonces.recheck_ambiguous(
            db_path=self.db_path,
            delay_range=(0, 0),
            browser_delay_range=(0, 0),
            checker=http_checker,
            browser_checker=browser_checker,
            driver_factory=lambda: fake_driver,
        )

        browser_checker.assert_called_once_with("https://example.com/ambiguous", fake_driver)
        self.assertEqual(result["rechecked"], 1)
        self.assertEqual(result["dead"], 1)
        self.assertEqual(result["deleted"], 1)
        fake_driver.quit.assert_called_once()

    def test_does_not_launch_browser_when_nothing_ambiguous(self):
        self._seed("https://example.com/alive")
        http_checker = lambda url, session: False  # noqa: E731
        driver_factory = MagicMock()

        result = recheck_dead_annonces.recheck_ambiguous(
            db_path=self.db_path,
            delay_range=(0, 0),
            checker=http_checker,
            driver_factory=driver_factory,
        )

        driver_factory.assert_not_called()
        self.assertEqual(result["rechecked"], 0)

    def test_dry_run_does_not_delete(self):
        self._seed("https://example.com/ambiguous")
        http_checker = lambda url, session: None  # noqa: E731
        browser_checker = lambda url, driver: True  # noqa: E731
        fake_driver = MagicMock()

        result = recheck_dead_annonces.recheck_ambiguous(
            db_path=self.db_path,
            delay_range=(0, 0),
            browser_delay_range=(0, 0),
            dry_run=True,
            checker=http_checker,
            browser_checker=browser_checker,
            driver_factory=lambda: fake_driver,
        )

        self.assertEqual(result["dead"], 1)
        self.assertEqual(result["deleted"], 0)
        self.assertEqual(annonces_store.list_annonces(db_path=self.db_path)["total"], 1)

    def test_still_ambiguous_after_browser_check_is_kept(self):
        self._seed("https://example.com/ambiguous")
        http_checker = lambda url, session: None  # noqa: E731
        browser_checker = lambda url, driver: None  # noqa: E731
        fake_driver = MagicMock()

        result = recheck_dead_annonces.recheck_ambiguous(
            db_path=self.db_path,
            delay_range=(0, 0),
            browser_delay_range=(0, 0),
            checker=http_checker,
            browser_checker=browser_checker,
            driver_factory=lambda: fake_driver,
        )

        self.assertEqual(result["still_ambiguous"], 1)
        self.assertEqual(result["deleted"], 0)

    def test_limit_caps_number_of_browser_rechecks(self):
        self._seed(*[f"https://example.com/{i}" for i in range(5)])
        http_checker = lambda url, session: None  # noqa: E731
        browser_checker = MagicMock(return_value=False)
        fake_driver = MagicMock()

        result = recheck_dead_annonces.recheck_ambiguous(
            db_path=self.db_path,
            delay_range=(0, 0),
            browser_delay_range=(0, 0),
            limit=2,
            checker=http_checker,
            browser_checker=browser_checker,
            driver_factory=lambda: fake_driver,
        )

        self.assertEqual(result["rechecked"], 2)
        self.assertEqual(browser_checker.call_count, 2)


if __name__ == "__main__":
    unittest.main()
