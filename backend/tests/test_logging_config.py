import importlib
import logging
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging_config


class LoggingConfigTest(unittest.TestCase):
    """
    Vérifie le logger structuré centralisé (ORA-63) : niveau par défaut,
    prise en compte de LOG_LEVEL, format structuré, idempotence, et le
    comportement no-op de init_sentry() sans SENTRY_DSN (aucune dépendance
    à un vrai compte/DSN Sentry pour ces tests).
    """

    def setUp(self):
        # Isole chaque test du reste de la suite : d'autres fichiers de test
        # importent `app`, qui appelle déjà configure_logging() à l'import.
        # On repart d'un logger racine et d'un module logging_config vierges
        # quel que soit l'ordre d'exécution des tests.
        self._root_logger = logging.getLogger()
        self._original_handlers = list(self._root_logger.handlers)
        self._original_level = self._root_logger.level
        self._root_logger.handlers = []
        importlib.reload(logging_config)

    def tearDown(self):
        self._root_logger.handlers = self._original_handlers
        self._root_logger.setLevel(self._original_level)
        importlib.reload(logging_config)

    def test_configure_logging_default_level_is_info(self):
        env = dict(os.environ)
        env.pop("LOG_LEVEL", None)
        with patch.dict(os.environ, env, clear=True):
            root = logging_config.configure_logging()
        self.assertEqual(root.level, logging.INFO)

    def test_configure_logging_respects_log_level_env(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}, clear=False):
            root = logging_config.configure_logging()
        self.assertEqual(root.level, logging.DEBUG)

    def test_configure_logging_is_case_insensitive(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "warning"}, clear=False):
            root = logging_config.configure_logging()
        self.assertEqual(root.level, logging.WARNING)

    def test_configure_logging_invalid_level_falls_back_to_info(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "NOT_A_REAL_LEVEL"}, clear=False):
            root = logging_config.configure_logging()
        self.assertEqual(root.level, logging.INFO)

    def test_configure_logging_format_includes_timestamp_level_module_and_message(self):
        root = logging_config.configure_logging()

        self.assertTrue(root.handlers, "configure_logging() doit ajouter au moins un handler")
        formatter = root.handlers[0].formatter
        self.assertIn("%(asctime)s", formatter._fmt)
        self.assertIn("%(levelname)s", formatter._fmt)
        self.assertIn("%(name)s", formatter._fmt)
        self.assertIn("%(message)s", formatter._fmt)

    def test_configure_logging_is_idempotent_no_duplicate_handlers(self):
        logging_config.configure_logging()
        handlers_after_first_call = len(logging.getLogger().handlers)

        logging_config.configure_logging()
        handlers_after_second_call = len(logging.getLogger().handlers)

        self.assertEqual(handlers_after_first_call, handlers_after_second_call)

    def test_init_sentry_is_a_silent_noop_without_sentry_dsn(self):
        env = dict(os.environ)
        env.pop("SENTRY_DSN", None)
        with patch.dict(os.environ, env, clear=True):
            result = logging_config.init_sentry()

        self.assertIsNone(result)

    def test_init_sentry_is_a_silent_noop_with_blank_sentry_dsn(self):
        with patch.dict(os.environ, {"SENTRY_DSN": "   "}, clear=False):
            result = logging_config.init_sentry()

        self.assertIsNone(result)

    def test_init_sentry_initializes_sdk_when_dsn_is_set(self):
        # DSN syntaxiquement valide mais fictif : aucun compte Sentry réel
        # requis, sentry_sdk.init() ne fait aucun appel réseau synchrone.
        fake_dsn = "https://fake_public_key@o0.ingest.sentry.io/123456"
        try:
            with patch.dict(os.environ, {"SENTRY_DSN": fake_dsn}, clear=False):
                result = logging_config.init_sentry()

            self.assertIsNotNone(result)
        finally:
            # Désactive le client Sentry configuré par ce test pour ne pas
            # affecter le reste de la suite.
            import sentry_sdk
            sentry_sdk.init(dsn=None)


if __name__ == "__main__":
    unittest.main()
