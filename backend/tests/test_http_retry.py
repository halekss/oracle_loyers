import os
import sys
import unittest
from unittest.mock import patch

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from http_retry import request_with_retry


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class RequestWithRetryTest(unittest.TestCase):
    def test_returns_response_immediately_on_success(self):
        with patch("http_retry.requests.request", return_value=FakeResponse(200)) as mock_request:
            response = request_with_retry("GET", "https://example.com", max_retries=3, backoff_seconds=0)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 1)

    def test_retries_on_transient_status_then_succeeds(self):
        responses = [FakeResponse(503), FakeResponse(200)]
        with patch("http_retry.requests.request", side_effect=responses) as mock_request:
            response = request_with_retry("GET", "https://example.com", max_retries=3, backoff_seconds=0)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)

    def test_retries_on_network_exception_then_succeeds(self):
        with patch(
            "http_retry.requests.request",
            side_effect=[requests.exceptions.ConnectionError("boom"), FakeResponse(200)],
        ) as mock_request:
            response = request_with_retry("GET", "https://example.com", max_retries=3, backoff_seconds=0)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)

    def test_returns_none_and_logs_error_after_exhausting_retries(self):
        with patch("http_retry.requests.request", return_value=FakeResponse(500)) as mock_request:
            with self.assertLogs("http_retry", level="ERROR") as logs:
                response = request_with_retry("GET", "https://example.com", max_retries=3, backoff_seconds=0)

        self.assertIsNone(response)
        self.assertEqual(mock_request.call_count, 3)
        self.assertTrue(any("Échec définitif" in message for message in logs.output))

    def test_non_transient_error_status_is_returned_without_retry(self):
        with patch("http_retry.requests.request", return_value=FakeResponse(404)) as mock_request:
            response = request_with_retry("GET", "https://example.com", max_retries=3, backoff_seconds=0)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(mock_request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
