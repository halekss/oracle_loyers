import json
import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import scraper_utils
from scraper_utils import (
    find_first,
    get_scraper_logger,
    load_existing_rows,
    load_site_config,
    pick_proxy,
    pick_user_agent,
    retry_with_backoff,
)


class FakeElement:
    def __init__(self, text):
        self._text = text

    @property
    def text(self):
        return self._text


class FindFirstTest(unittest.TestCase):
    def test_returns_text_of_first_matching_selector(self):
        element = MagicMock()
        element.find_element.side_effect = [
            Exception("not found"),
            FakeElement("  Prix trouvé  "),
        ]

        result = find_first(element, [".missing", ".price"])

        self.assertEqual(result, "Prix trouvé")

    def test_returns_default_when_no_selector_matches(self):
        element = MagicMock()
        element.find_element.side_effect = Exception("not found")

        result = find_first(element, [".a", ".b"], default="N/A")

        self.assertEqual(result, "N/A")


class RetryWithBackoffTest(unittest.TestCase):
    def test_returns_result_on_first_success(self):
        calls = []

        @retry_with_backoff(max_retries=3, backoff_seconds=0)
        def flaky():
            calls.append(1)
            return "ok"

        self.assertEqual(flaky(), "ok")
        self.assertEqual(len(calls), 1)

    def test_retries_then_succeeds(self):
        attempts = {"count": 0}

        @retry_with_backoff(max_retries=3, backoff_seconds=0)
        def flaky():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ValueError("transient")
            return "ok"

        self.assertEqual(flaky(), "ok")
        self.assertEqual(attempts["count"], 2)

    def test_raises_last_error_after_exhausting_retries(self):
        @retry_with_backoff(max_retries=2, backoff_seconds=0)
        def always_fails():
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            always_fails()


class GetScraperLoggerTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.patcher = patch.object(scraper_utils, "LOG_DIR", self.tmp_dir.name)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp_dir.cleanup()

    def _reset_logger(self, name):
        logger = logging.getLogger(f"scraper.{name}")
        logger.handlers.clear()

    def test_configures_console_and_file_handlers(self):
        self._reset_logger("test_site")

        logger = get_scraper_logger("test_site")
        logger.info("run terminé : 10 trouvées, 3 nouvelles, 0 erreurs")

        self.assertEqual(len(logger.handlers), 2)
        log_path = os.path.join(self.tmp_dir.name, "test_site.log")
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("run terminé : 10 trouvées, 3 nouvelles, 0 erreurs", content)

    def test_is_idempotent_across_repeated_calls(self):
        self._reset_logger("test_site_2")

        logger1 = get_scraper_logger("test_site_2")
        logger2 = get_scraper_logger("test_site_2")

        self.assertIs(logger1, logger2)
        self.assertEqual(len(logger1.handlers), 2)


class LoadSiteConfigTest(unittest.TestCase):
    def _write_config(self, tmp_dir):
        path = os.path.join(tmp_dir, "config.json")
        config = {
            "ville_active": "lyon",
            "villes": {
                "lyon": {
                    "nom": "Lyon",
                    "slug": "lyon",
                    "century21": {"base_url": "https://example.test/lyon/page-{}/"},
                    "seloger": {"base_url": "https://example.test/seloger", "page_query_param": "page"},
                }
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f)
        return path

    def test_loads_base_url_and_ville_for_a_site(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_config(tmp_dir)
            config = load_site_config("century21", config_path=path)

        self.assertEqual(config["ville_nom"], "Lyon")
        self.assertEqual(config["ville_slug"], "lyon")
        self.assertEqual(config["base_url"], "https://example.test/lyon/page-{}/")
        self.assertIsNone(config["page_query_param"])

    def test_page_query_param_is_present_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_config(tmp_dir)
            config = load_site_config("seloger", config_path=path)

        self.assertEqual(config["page_query_param"], "page")

    def test_real_config_file_has_all_six_sites(self):
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(scraper_utils.__file__)), "scraping_config.json"
        )
        for site in ["century21", "orpi", "pap", "seloger", "vizzit", "paruvendu"]:
            config = load_site_config(site, config_path=config_path)
            self.assertTrue(config["base_url"].startswith("https://"))


class PickUserAgentAndProxyTest(unittest.TestCase):
    def _write_config(self, tmp_dir, user_agents=None, proxies=None):
        path = os.path.join(tmp_dir, "config.json")
        config = {
            "ville_active": "lyon",
            "user_agents": user_agents if user_agents is not None else [],
            "proxies": proxies if proxies is not None else [],
            "villes": {"lyon": {"nom": "Lyon", "slug": "lyon"}},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f)
        return path

    def test_pick_user_agent_returns_none_when_pool_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_config(tmp_dir, user_agents=[])
            self.assertIsNone(pick_user_agent(config_path=path))

    def test_pick_user_agent_returns_one_from_pool(self):
        pool = ["UA-1", "UA-2", "UA-3"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_config(tmp_dir, user_agents=pool)
            self.assertIn(pick_user_agent(config_path=path), pool)

    def test_pick_proxy_returns_none_when_pool_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_config(tmp_dir, proxies=[])
            self.assertIsNone(pick_proxy(config_path=path))

    def test_pick_proxy_returns_one_from_pool(self):
        pool = ["http://proxy1:8080", "http://proxy2:8080"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_config(tmp_dir, proxies=pool)
            self.assertIn(pick_proxy(config_path=path), pool)

    def test_real_config_has_no_proxies_configured_by_default(self):
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(scraper_utils.__file__)), "scraping_config.json"
        )
        self.assertIsNone(pick_proxy(config_path=config_path))

    def test_real_config_has_a_user_agent_pool(self):
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(scraper_utils.__file__)), "scraping_config.json"
        )
        ua = pick_user_agent(config_path=config_path)
        self.assertIsNotNone(ua)
        self.assertIn("Mozilla", ua)


class LoadExistingRowsTest(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        rows, liens_vus = load_existing_rows("/inexistant.csv")

        self.assertEqual(rows, [])
        self.assertEqual(liens_vus, set())

    def test_loads_rows_and_links_from_last_column(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "annonces.csv")
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                import csv as csv_module
                writer = csv_module.writer(f)
                writer.writerow(["Titre", "Prix", "Lien"])
                writer.writerow(["Studio Bellecour", "500€", "https://example.test/1"])
                writer.writerow(["T2 Croix-Rousse", "700€", "https://example.test/2"])

            rows, liens_vus = load_existing_rows(path)

        self.assertEqual(len(rows), 2)
        self.assertEqual(liens_vus, {"https://example.test/1", "https://example.test/2"})

    def test_empty_file_besides_header_returns_no_rows(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "annonces.csv")
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                import csv as csv_module
                csv_module.writer(f).writerow(["Titre", "Prix", "Lien"])

            rows, liens_vus = load_existing_rows(path)

        self.assertEqual(rows, [])
        self.assertEqual(liens_vus, set())


class GetChromeDriverOptionsTest(unittest.TestCase):
    """Vérifie les options passées à undetected_chromedriver sans lancer de vrai navigateur."""

    def test_user_agent_and_proxy_add_expected_arguments(self):
        captured = {}

        class FakeChromeOptions:
            def __init__(self):
                self.arguments = []

            def add_argument(self, arg):
                self.arguments.append(arg)

            def add_experimental_option(self, name, value):
                pass

        def fake_chrome(options=None):
            captured["options"] = options
            return MagicMock()

        with patch.object(scraper_utils.uc, "ChromeOptions", FakeChromeOptions), \
             patch.object(scraper_utils.uc, "Chrome", fake_chrome):
            scraper_utils.get_chrome_driver(user_agent="Mozilla/5.0 Test", proxy="http://127.0.0.1:8080")

        self.assertIn("--user-agent=Mozilla/5.0 Test", captured["options"].arguments)
        self.assertIn("--proxy-server=http://127.0.0.1:8080", captured["options"].arguments)

    def test_no_user_agent_or_proxy_by_default(self):
        captured = {}

        class FakeChromeOptions:
            def __init__(self):
                self.arguments = []

            def add_argument(self, arg):
                self.arguments.append(arg)

            def add_experimental_option(self, name, value):
                pass

        def fake_chrome(options=None):
            captured["options"] = options
            return MagicMock()

        with patch.object(scraper_utils.uc, "ChromeOptions", FakeChromeOptions), \
             patch.object(scraper_utils.uc, "Chrome", fake_chrome):
            scraper_utils.get_chrome_driver()

        self.assertFalse(any(a.startswith("--user-agent=") for a in captured["options"].arguments))
        self.assertFalse(any(a.startswith("--proxy-server=") for a in captured["options"].arguments))

    def test_applies_default_page_load_timeout(self):
        class FakeChromeOptions:
            def add_argument(self, arg):
                pass

            def add_experimental_option(self, name, value):
                pass

        fake_driver = MagicMock()

        with patch.object(scraper_utils.uc, "ChromeOptions", FakeChromeOptions), \
             patch.object(scraper_utils.uc, "Chrome", lambda options=None: fake_driver):
            driver = scraper_utils.get_chrome_driver()

        fake_driver.set_page_load_timeout.assert_called_once_with(30)
        self.assertIs(driver, fake_driver)

    def test_page_load_timeout_is_overridable(self):
        class FakeChromeOptions:
            def add_argument(self, arg):
                pass

            def add_experimental_option(self, name, value):
                pass

        fake_driver = MagicMock()

        with patch.object(scraper_utils.uc, "ChromeOptions", FakeChromeOptions), \
             patch.object(scraper_utils.uc, "Chrome", lambda options=None: fake_driver):
            scraper_utils.get_chrome_driver(page_load_timeout=60)

        fake_driver.set_page_load_timeout.assert_called_once_with(60)


if __name__ == "__main__":
    unittest.main()
