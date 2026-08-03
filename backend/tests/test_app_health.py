import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app


class HealthRouteTest(unittest.TestCase):
    def test_health_route_exposes_the_loaded_model_version(self):
        client = app.app.test_client()

        response = client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn(data["status"], ["ok", "degraded"])
        self.assertIn("model_loaded", data)
        self.assertIn("model_version", data["model"])
        self.assertIn("trained_at", data["model"])
        self.assertIn("metrics", data["model"])


if __name__ == "__main__":
    unittest.main()
