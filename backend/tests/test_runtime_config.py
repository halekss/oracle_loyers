import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class RuntimeConfigTest(unittest.TestCase):
    def test_get_server_port_uses_render_port_env(self):
        with patch.dict(os.environ, {"PORT": "10000"}, clear=False):
            self.assertEqual(app.get_server_port(), 10000)

    def test_get_server_port_falls_back_to_5000(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(app.get_server_port(), 5000)

    def test_get_cors_origins_parses_comma_separated_env(self):
        with patch.dict(
            os.environ,
            {"CORS_ORIGINS": "https://oracle-loyers.onrender.com/, https://admin.example.com "},
            clear=False,
        ):
            origins = app.get_cors_origins()
            self.assertEqual(origins[:2], ["https://oracle-loyers.onrender.com", "https://admin.example.com"])
            self.assertIn("http://localhost:5173", origins)

    def test_get_cors_origins_keeps_frontend_origin_allowed_when_env_is_set(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": "https://admin.example.com"}, clear=False):
            origins = app.get_cors_origins()
            self.assertEqual(origins[0], "https://admin.example.com")
            self.assertIn("https://oracle-loyers.onrender.com", origins)
            self.assertIn("http://localhost:5173", origins)

    def test_get_cors_origins_defaults_to_restrictive_list_without_wildcard(self):
        with patch.dict(os.environ, {}, clear=True):
            origins = app.get_cors_origins()
            self.assertNotEqual(origins, "*")
            self.assertEqual(origins, app.DEFAULT_CORS_ORIGINS)
            self.assertIn("https://oracle-loyers.onrender.com", origins)


if __name__ == "__main__":
    unittest.main()
