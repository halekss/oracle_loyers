import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import scraper_utils
from scraper_utils import find_first, get_scraper_logger, retry_with_backoff


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


if __name__ == "__main__":
    unittest.main()
