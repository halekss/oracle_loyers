import asyncio
import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import verify_annonces_async
from services import annonces_store


class RowsToVerifyTest(unittest.TestCase):
    """Test the date-arithmetic logic of _rows_to_verify (TTL/staleness detection)."""

    def test_active_row_stale_included(self):
        """Row with statut='active' and derniere_verification_http older than ttl_days → included."""
        df = pd.DataFrame({
            "url": ["https://example.com/old"],
            "statut": ["active"],
            "derniere_verification_http": ["2026-07-20T00:00:00+00:00"],  # 18 days old from 2026-08-07
        })
        reference_date = pd.Timestamp("2026-08-07T12:00:00+00:00")
        ttl_days = 15

        result = verify_annonces_async._rows_to_verify(df, ttl_days, reference_date)

        self.assertIn(0, result, "Stale active row should be included for re-verification")

    def test_active_row_fresh_excluded(self):
        """Row with statut='active' and derniere_verification_http within ttl_days → NOT included."""
        df = pd.DataFrame({
            "url": ["https://example.com/fresh"],
            "statut": ["active"],
            "derniere_verification_http": ["2026-08-05T00:00:00+00:00"],  # 2 days old
        })
        reference_date = pd.Timestamp("2026-08-07T12:00:00+00:00")
        ttl_days = 15

        result = verify_annonces_async._rows_to_verify(df, ttl_days, reference_date)

        self.assertNotIn(0, result, "Fresh active row should be excluded from verification")

    def test_active_row_missing_verification_timestamp_included(self):
        """Row with statut='active' and missing/empty derniere_verification_http → included."""
        df = pd.DataFrame({
            "url": ["https://example.com/no-history"],
            "statut": ["active"],
            "derniere_verification_http": [""],  # No verification history
        })
        reference_date = pd.Timestamp("2026-08-07T12:00:00+00:00")
        ttl_days = 15

        result = verify_annonces_async._rows_to_verify(df, ttl_days, reference_date)

        self.assertIn(0, result, "Active row with no verification history should be included")

    def test_active_row_nan_verification_timestamp_included(self):
        """Row with statut='active' and NaT derniere_verification_http → included."""
        df = pd.DataFrame({
            "url": ["https://example.com/nan-history"],
            "statut": ["active"],
            "derniere_verification_http": [pd.NaT],  # NaT from to_datetime
        })
        reference_date = pd.Timestamp("2026-08-07T12:00:00+00:00")
        ttl_days = 15

        result = verify_annonces_async._rows_to_verify(df, ttl_days, reference_date)

        self.assertIn(0, result, "Active row with NaT verification timestamp should be included")

    def test_a_verifier_row_always_included(self):
        """Row with statut='a_verifier' regardless of derniere_verification_http → always included."""
        df = pd.DataFrame({
            "url": [
                "https://example.com/verify-no-history",
                "https://example.com/verify-old",
                "https://example.com/verify-fresh",
            ],
            "statut": ["a_verifier", "a_verifier", "a_verifier"],
            "derniere_verification_http": ["", "2026-08-01T00:00:00+00:00", "2026-08-06T00:00:00+00:00"],
        })
        reference_date = pd.Timestamp("2026-08-07T12:00:00+00:00")
        ttl_days = 15

        result = verify_annonces_async._rows_to_verify(df, ttl_days, reference_date)

        self.assertEqual(len(result), 3, "All a_verifier rows should be included regardless of timestamp")
        self.assertIn(0, result)
        self.assertIn(1, result)
        self.assertIn(2, result)

    def test_inactive_row_always_excluded(self):
        """Row with statut='inactive' → never included (even with stale/missing timestamp)."""
        df = pd.DataFrame({
            "url": ["https://example.com/inactive"],
            "statut": ["inactive"],
            "derniere_verification_http": [""],  # No history would normally trigger inclusion
        })
        reference_date = pd.Timestamp("2026-08-07T12:00:00+00:00")
        ttl_days = 15

        result = verify_annonces_async._rows_to_verify(df, ttl_days, reference_date)

        self.assertNotIn(0, result, "Inactive row should never be included, even if stale/missing")

    def test_mixed_statuses_correct_filtering(self):
        """Integration test: mix of all statuses with various verification timestamps."""
        df = pd.DataFrame({
            "url": [
                "https://example.com/a_verifier-old",
                "https://example.com/a_verifier-fresh",
                "https://example.com/active-stale",
                "https://example.com/active-fresh",
                "https://example.com/active-no-history",
                "https://example.com/inactive-stale",
                "https://example.com/inactive-no-history",
            ],
            "statut": [
                "a_verifier",
                "a_verifier",
                "active",
                "active",
                "active",
                "inactive",
                "inactive",
            ],
            "derniere_verification_http": [
                "2026-08-01T00:00:00+00:00",  # Old, but a_verifier → included
                "2026-08-06T00:00:00+00:00",  # Fresh, but a_verifier → included
                "2026-07-20T00:00:00+00:00",  # Stale active → included
                "2026-08-05T00:00:00+00:00",  # Fresh active → excluded
                "",  # No history, active → included
                "2026-07-20T00:00:00+00:00",  # Stale, but inactive → excluded
                "",  # No history, but inactive → excluded
            ],
        })
        reference_date = pd.Timestamp("2026-08-07T12:00:00+00:00")
        ttl_days = 15

        result = verify_annonces_async._rows_to_verify(df, ttl_days, reference_date)

        expected = {0, 1, 2, 4}  # Indices 0, 1 (a_verifier), 2, 4 (active stale or no history)
        self.assertEqual(set(result), expected, "Mixed statuses should be filtered correctly")


class CheckUrlStatusAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_true_on_404(self):
        session = MagicMock()
        response = AsyncMock()
        response.status = 404
        response.__aenter__.return_value = response
        response.__aexit__.return_value = False
        session.get.return_value = response

        result = await verify_annonces_async.check_url_status_async("https://example.com/x", session)

        self.assertTrue(result)

    async def test_returns_true_on_soft_404_text(self):
        session = MagicMock()
        response = AsyncMock()
        response.status = 200
        response.text = AsyncMock(return_value="<div>Cette annonce a été supprimée</div>")
        response.__aenter__.return_value = response
        response.__aexit__.return_value = False
        session.get.return_value = response

        result = await verify_annonces_async.check_url_status_async("https://example.com/x", session)

        self.assertTrue(result)

    async def test_returns_false_on_live_page(self):
        session = MagicMock()
        response = AsyncMock()
        response.status = 200
        response.text = AsyncMock(return_value="<div>T2 - 850€/mois</div>")
        response.__aenter__.return_value = response
        response.__aexit__.return_value = False
        session.get.return_value = response

        result = await verify_annonces_async.check_url_status_async("https://example.com/x", session)

        self.assertFalse(result)

    async def test_returns_none_on_network_error(self):
        import aiohttp
        session = MagicMock()
        session.get.side_effect = aiohttp.ClientError("boom")

        result = await verify_annonces_async.check_url_status_async("https://example.com/x", session)

        self.assertIsNone(result)


class VerifyAnnoncesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fd, self.csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        annonces_store.init_db(self.db_path)

        pd.DataFrame({
            "url": ["https://example.com/dead", "https://example.com/alive", "https://example.com/ambiguous"],
            "statut": ["a_verifier", "a_verifier", "a_verifier"],
        }).to_csv(self.csv_path, index=False)

    def tearDown(self):
        for path in (self.csv_path, self.db_path):
            if os.path.exists(path):
                os.remove(path)

    async def test_confirmed_dead_updates_csv_and_db_without_deleting_rows(self):
        async def fake_checker(url, session, timeout=10):
            return {"https://example.com/dead": True, "https://example.com/alive": False,
                    "https://example.com/ambiguous": None}[url]

        annonces_store.upsert_annonce(url="https://example.com/dead", statut="a_verifier", db_path=self.db_path)

        stats = await verify_annonces_async.verify_annonces(
            csv_path=self.csv_path, db_path=self.db_path, checker=fake_checker,
        )

        result_df = pd.read_csv(self.csv_path)
        self.assertEqual(len(result_df), 3, "aucune ligne ne doit être supprimée")
        statuts = dict(zip(result_df["url"], result_df["statut"]))
        self.assertEqual(statuts["https://example.com/dead"], "inactive")
        self.assertEqual(statuts["https://example.com/alive"], "active")
        self.assertEqual(statuts["https://example.com/ambiguous"], "a_verifier")

        self.assertEqual(stats["confirmed_dead"], 1)
        self.assertEqual(stats["reconfirmed_alive"], 1)
        self.assertEqual(stats["still_ambiguous"], 1)

        annonce = annonces_store.get_annonce_by_url("https://example.com/dead", db_path=self.db_path)
        self.assertEqual(annonce["statut"], "inactive")

    async def test_dry_run_does_not_write(self):
        async def fake_checker(url, session, timeout=10):
            return True

        original_mtime = os.path.getmtime(self.csv_path)
        await verify_annonces_async.verify_annonces(
            csv_path=self.csv_path, db_path=self.db_path, checker=fake_checker, dry_run=True,
        )

        self.assertEqual(os.path.getmtime(self.csv_path), original_mtime)

    async def test_ambiguous_result_does_not_stamp_verification_timestamp(self):
        # Finding 3 (final review, important): an ambiguous (None) result must
        # NOT be recorded as a successful verification. Stamping
        # derniere_verification_http on an inconclusive result suppresses
        # re-verification for the full ttl_days window based on a single
        # failed attempt -- and given SeLoger's near-100% CAPTCHA/403 rate,
        # ambiguous is the dominant case, not an edge case.
        pd.DataFrame({
            "url": ["https://example.com/ambiguous-only"],
            "statut": ["a_verifier"],
            "derniere_verification_http": [""],
        }).to_csv(self.csv_path, index=False)

        async def fake_checker(url, session, timeout=10):
            return None

        await verify_annonces_async.verify_annonces(
            csv_path=self.csv_path, db_path=self.db_path, checker=fake_checker,
        )

        result_df = pd.read_csv(self.csv_path)
        row = result_df[result_df["url"] == "https://example.com/ambiguous-only"].iloc[0]
        self.assertTrue(
            pd.isna(row["derniere_verification_http"]) or row["derniere_verification_http"] == "",
            "ambiguous result must leave derniere_verification_http unchanged (still empty), not stamp a fresh timestamp",
        )

    async def test_stats_have_no_misleading_network_errors_key(self):
        # Finding 6 (final review, important): network_errors always equalled
        # still_ambiguous in lockstep (it never distinguished a genuine
        # network failure from an ambiguous HTTP status), so the stat -- and
        # the "(dont N erreurs réseau)" log clause -- actively misled
        # operators. The fix removes it entirely rather than leave a fake
        # distinction in place.
        async def fake_checker(url, session, timeout=10):
            return None

        stats = await verify_annonces_async.verify_annonces(
            csv_path=self.csv_path, db_path=self.db_path, checker=fake_checker,
        )

        self.assertNotIn("network_errors", stats)
        self.assertEqual(stats["still_ambiguous"], 3)

    async def test_malformed_url_does_not_crash_the_whole_batch(self):
        # Finding 4 (final review, important): a NaN/non-string url mixed in
        # among otherwise-valid eligible rows must not crash verify_annonces
        # via an uncaught TypeError propagating out of asyncio.gather --
        # which would discard results for every other successfully-checked
        # row in the batch before any CSV write or DB sync happens.
        pd.DataFrame({
            "url": ["https://example.com/valid-dead", float("nan"), "https://example.com/valid-alive"],
            "statut": ["a_verifier", "a_verifier", "a_verifier"],
        }).to_csv(self.csv_path, index=False)

        async def fake_checker(url, session, timeout=10):
            return {"https://example.com/valid-dead": True,
                    "https://example.com/valid-alive": False}[url]

        stats = await verify_annonces_async.verify_annonces(
            csv_path=self.csv_path, db_path=self.db_path, checker=fake_checker,
        )

        result_df = pd.read_csv(self.csv_path)
        self.assertEqual(len(result_df), 3, "no row should be dropped, including the malformed-url one")
        statuts = dict(zip(result_df["url"], result_df["statut"]))
        self.assertEqual(statuts["https://example.com/valid-dead"], "inactive")
        self.assertEqual(statuts["https://example.com/valid-alive"], "active")
        self.assertEqual(stats["confirmed_dead"], 1)
        self.assertEqual(stats["reconfirmed_alive"], 1)

    async def test_checker_exception_treated_as_ambiguous_not_crash(self):
        # Finding 4 defense-in-depth: even if a bad row slips past
        # _rows_to_verify's url filter, an unexpected exception from the
        # checker itself (e.g. TypeError from a malformed input) must not
        # propagate out of asyncio.gather and abort the whole batch.
        pd.DataFrame({
            "url": ["https://example.com/boom", "https://example.com/valid-alive"],
            "statut": ["a_verifier", "a_verifier"],
        }).to_csv(self.csv_path, index=False)

        async def flaky_checker(url, session, timeout=10):
            if url == "https://example.com/boom":
                raise TypeError("simulated malformed-url crash")
            return False

        stats = await verify_annonces_async.verify_annonces(
            csv_path=self.csv_path, db_path=self.db_path, checker=flaky_checker,
        )

        result_df = pd.read_csv(self.csv_path)
        self.assertEqual(len(result_df), 2)
        statuts = dict(zip(result_df["url"], result_df["statut"]))
        self.assertEqual(statuts["https://example.com/valid-alive"], "active")
        self.assertEqual(statuts["https://example.com/boom"], "a_verifier",
                          "row whose checker raised must be treated as ambiguous, staying a_verifier")
        self.assertEqual(stats["reconfirmed_alive"], 1)
        self.assertEqual(stats["still_ambiguous"], 1)
