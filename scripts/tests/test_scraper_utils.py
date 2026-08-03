import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper_utils import find_first, retry_with_backoff


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


if __name__ == "__main__":
    unittest.main()
