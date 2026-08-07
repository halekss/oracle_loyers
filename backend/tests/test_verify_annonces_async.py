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
