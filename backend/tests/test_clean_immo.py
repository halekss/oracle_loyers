import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from scripts.clean_immo import step_flag_expired


class StepFlagExpiredTest(unittest.TestCase):
    def setUp(self):
        fd, self.csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        os.remove(self.csv_path)  # le fichier n'existe pas encore = premier run

    def tearDown(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def test_first_run_all_rows_default_active(self):
        df = pd.DataFrame({
            "url": ["https://example.com/1", "https://example.com/2"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()] * 2,
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        self.assertListEqual(list(result["statut"]), ["active", "active"])

    def test_previously_inactive_row_is_preserved_across_runs(self):
        # Simule un CSV précédent où l'url 'dead' a déjà été marquée inactive
        # par verify_annonces_async.py (Task 3).
        previous = pd.DataFrame({
            "url": ["https://example.com/dead"],
            "statut": ["inactive"],
            "derniere_verification_http": ["2026-08-01T00:00:00+00:00"],
        })
        previous.to_csv(self.csv_path, index=False)

        # Le run courant re-fusionne des données brutes fraîches ne contenant
        # PAS cette colonne statut (comme le fait réellement data_fusion.py).
        df = pd.DataFrame({
            "url": ["https://example.com/dead"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        self.assertEqual(result.iloc[0]["statut"], "inactive",
                          "le statut inactive confirmé ne doit pas être écrasé par une re-fusion")

    def test_reappearing_row_resets_to_active(self):
        # Une url 'a_verifier' (TTL dépassé sans confirmation morte) qui
        # réapparaît dans un scrape frais (date_dernier_scan récente) est
        # une preuve forte qu'elle est de nouveau active.
        previous = pd.DataFrame({
            "url": ["https://example.com/revenue"],
            "statut": ["a_verifier"],
            "derniere_verification_http": [""],
        })
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({
            "url": ["https://example.com/revenue"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        self.assertEqual(result.iloc[0]["statut"], "active")

    def test_stale_active_row_flagged_a_verifier_not_dropped(self):
        previous = pd.DataFrame({"url": ["https://example.com/stale"], "statut": ["active"]})
        previous.to_csv(self.csv_path, index=False)

        old_date = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=20)).isoformat()
        df = pd.DataFrame({"url": ["https://example.com/stale"], "date_dernier_scan": [old_date]})

        result = step_flag_expired(df, previous_csv_path=self.csv_path, ttl_days=14)

        self.assertEqual(len(result), 1, "la ligne ne doit plus être supprimée du dataframe")
        self.assertEqual(result.iloc[0]["statut"], "a_verifier")

    def test_row_missing_from_new_scrape_is_kept_and_flagged(self):
        # ORA-134 bis, étape 3.1 du spec utilisateur : une url absente du
        # scrape courant (introuvable dans `df`) mais présente dans le run
        # précédent doit être conservée avec statut a_verifier, pas perdue.
        previous = pd.DataFrame({"url": ["https://example.com/disparue"], "statut": ["active"]})
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({"url": ["https://example.com/autre"], "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()]})

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        urls = list(result["url"])
        self.assertIn("https://example.com/disparue", urls)
        disparue = result[result["url"] == "https://example.com/disparue"].iloc[0]
        self.assertEqual(disparue["statut"], "a_verifier")
