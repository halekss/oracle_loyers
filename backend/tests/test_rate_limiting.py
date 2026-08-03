import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as app_module


class RateLimitConfigTest(unittest.TestCase):
    def test_get_default_rate_limits_parses_comma_separated_env_var(self):
        os.environ["RATE_LIMIT_DEFAULT"] = "10 per minute, 100 per hour"
        try:
            self.assertEqual(
                app_module.get_default_rate_limits(),
                ["10 per minute", "100 per hour"],
            )
        finally:
            del os.environ["RATE_LIMIT_DEFAULT"]

    def test_get_default_rate_limits_has_a_sensible_default(self):
        os.environ.pop("RATE_LIMIT_DEFAULT", None)
        limits = app_module.get_default_rate_limits()
        self.assertGreaterEqual(len(limits), 1)

    def test_get_chat_rate_limit_reads_env_var(self):
        os.environ["RATE_LIMIT_CHAT"] = "5 per hour"
        try:
            self.assertEqual(app_module.get_chat_rate_limit(), "5 per hour")
        finally:
            del os.environ["RATE_LIMIT_CHAT"]

    def test_get_chat_rate_limit_has_a_sensible_default(self):
        os.environ.pop("RATE_LIMIT_CHAT", None)
        self.assertTrue(app_module.get_chat_rate_limit())


class RateLimitBehaviorTest(unittest.TestCase):
    def test_chat_route_enforces_its_own_stricter_limit(self):
        # Utilise la vraie route /api/chat de l'app avec une limite très
        # basse (surchargée le temps du test) pour vérifier que le
        # décorateur @limiter.limit(get_chat_rate_limit) est bien appliqué,
        # indépendamment de la limite globale par défaut.
        os.environ["RATE_LIMIT_CHAT"] = "2 per hour"
        try:
            client = app_module.app.test_client()
            payload = {"message": "Quel prix à Gerland ?"}

            statuses = [client.post("/api/chat", json=payload).status_code for _ in range(3)]

            self.assertIn(429, statuses)
        finally:
            del os.environ["RATE_LIMIT_CHAT"]

    def test_exceeding_the_configured_limit_returns_429_with_json_error(self):
        # Reproduit le même montage (Limiter + errorhandler 429) que app.py,
        # sur une mini-app isolée avec une limite volontairement basse, pour
        # vérifier le comportement sans dépendre de l'état partagé de l'app
        # de production ni attendre une heure pour épuiser le vrai quota.
        from flask import Flask, jsonify
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        test_app = Flask(__name__)
        Limiter(
            key_func=get_remote_address,
            app=test_app,
            default_limits=["2 per minute"],
            storage_uri="memory://",
        )

        @test_app.errorhandler(429)
        def handle_429(_error):
            return jsonify({"error": "Trop de requêtes. Réessayez dans quelques instants."}), 429

        @test_app.route("/ping")
        def ping():
            return jsonify({"ok": True})

        client = test_app.test_client()

        self.assertEqual(client.get("/ping").status_code, 200)
        self.assertEqual(client.get("/ping").status_code, 200)

        response = client.get("/ping")

        self.assertEqual(response.status_code, 429)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
