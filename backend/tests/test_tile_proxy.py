import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app
from services import tile_proxy

SECRET = "secret-carto-key-123"


class IsValidTileTest(unittest.TestCase):
    def test_accepts_tiles_inside_the_pyramid(self):
        self.assertTrue(tile_proxy.is_valid_tile(0, 0, 0))
        self.assertTrue(tile_proxy.is_valid_tile(14, 8527, 5847))
        self.assertTrue(tile_proxy.is_valid_tile(tile_proxy.MAX_ZOOM, 2 ** 19 - 1, 0))

    def test_rejects_out_of_range_tiles(self):
        self.assertFalse(tile_proxy.is_valid_tile(tile_proxy.MAX_ZOOM + 1, 0, 0))
        self.assertFalse(tile_proxy.is_valid_tile(3, 8, 0))   # x >= 2^3
        self.assertFalse(tile_proxy.is_valid_tile(3, 0, 8))   # y >= 2^3
        self.assertFalse(tile_proxy.is_valid_tile(-1, 0, 0))


class BuildUpstreamUrlTest(unittest.TestCase):
    def test_builds_a_carto_url_without_any_key(self):
        url = tile_proxy.build_upstream_url(14, 8527, 5847)

        self.assertTrue(url.startswith("https://"))
        self.assertIn(".basemaps.cartocdn.com/dark_all/14/8527/5847.png", url)
        self.assertNotIn("key", url)

    def test_retina_suffix(self):
        self.assertTrue(tile_proxy.build_upstream_url(5, 1, 2, retina=True).endswith("/5/1/2@2x.png"))


class GetTileTest(unittest.TestCase):
    def setUp(self):
        tile_proxy.get_tile.cache_clear()

    def _response(self, content=b"PNG"):
        response = MagicMock()
        response.content = content
        return response

    def test_sends_the_key_to_carto_as_a_server_side_query_param(self):
        with patch.dict(os.environ, {"CARTO_API_KEY": SECRET}), \
             patch.object(tile_proxy.requests, "get", return_value=self._response()) as get:
            tile_proxy.get_tile(5, 1, 2)

        self.assertEqual(get.call_args.kwargs["params"], {"key": SECRET})

    def test_works_without_a_key_and_sends_no_key_param(self):
        with patch.dict(os.environ, {"CARTO_API_KEY": ""}), \
             patch.object(tile_proxy.requests, "get", return_value=self._response()) as get:
            tile_proxy.get_tile(5, 1, 2)

        self.assertEqual(get.call_args.kwargs["params"], {})

    def test_caches_successful_tiles(self):
        with patch.object(tile_proxy.requests, "get", return_value=self._response()) as get:
            tile_proxy.get_tile(5, 1, 2)
            tile_proxy.get_tile(5, 1, 2)

        self.assertEqual(get.call_count, 1)

    def test_does_not_cache_failures(self):
        failing = MagicMock()
        failing.raise_for_status.side_effect = requests.HTTPError("503")
        with patch.object(tile_proxy.requests, "get", side_effect=[failing, self._response()]) as get:
            with self.assertRaises(requests.HTTPError):
                tile_proxy.get_tile(5, 1, 2)
            self.assertEqual(tile_proxy.get_tile(5, 1, 2), b"PNG")

        self.assertEqual(get.call_count, 2)


class TileRouteTest(unittest.TestCase):
    def setUp(self):
        tile_proxy.get_tile.cache_clear()
        self.client = app.app.test_client()

    def test_serves_a_png_with_cache_headers_and_never_leaks_the_key(self):
        with patch.dict(os.environ, {"CARTO_API_KEY": SECRET}), \
             patch.object(tile_proxy, "get_tile", return_value=b"\x89PNG-bytes"):
            response = self.client.get("/api/tiles/14/8527/5847.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertIn("max-age", response.headers["Cache-Control"])
        self.assertNotIn(SECRET, str(dict(response.headers)))
        self.assertNotIn(SECRET.encode(), response.data)

    def test_retina_route(self):
        with patch.object(tile_proxy, "get_tile", return_value=b"png") as get_tile:
            response = self.client.get("/api/tiles/14/8527/5847@2x.png")

        self.assertEqual(response.status_code, 200)
        get_tile.assert_called_once_with(14, 8527, 5847, True)

    def test_out_of_range_tile_is_a_404_without_calling_carto(self):
        with patch.object(tile_proxy, "get_tile") as get_tile:
            response = self.client.get("/api/tiles/3/99/0.png")

        self.assertEqual(response.status_code, 404)
        get_tile.assert_not_called()

    def test_upstream_failure_is_a_502_that_does_not_leak_details(self):
        with patch.dict(os.environ, {"CARTO_API_KEY": SECRET}), \
             patch.object(tile_proxy, "get_tile", side_effect=requests.ConnectionError(f"boom {SECRET}")):
            response = self.client.get("/api/tiles/14/8527/5847.png")

        self.assertEqual(response.status_code, 502)
        self.assertNotIn(SECRET, response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
