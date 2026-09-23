import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app
from services import annonces_store


class AnnoncesRoutesTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        annonces_store.init_db(self.db_path)

        self.original_db_path = app.ANNONCES_DB_PATH
        app.ANNONCES_DB_PATH = self.db_path
        self.client = app.app.test_client()

    def tearDown(self):
        app.ANNONCES_DB_PATH = self.original_db_path
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_list_annonces_returns_paginated_envelope(self):
        annonces_store.upsert_annonce(
            titre="T2 Gerland", ville="Lyon", quartier="Gerland",
            url="https://example.com/a", db_path=self.db_path,
        )

        response = self.client.get("/api/annonces")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["items"][0]["titre"], "T2 Gerland")

    def test_list_annonces_filters_by_ville_and_quartier(self):
        annonces_store.upsert_annonce(url="https://example.com/a", ville="Lyon", quartier="Gerland", db_path=self.db_path)
        annonces_store.upsert_annonce(url="https://example.com/b", ville="Lyon", quartier="Vaise", db_path=self.db_path)

        response = self.client.get("/api/annonces?ville=Lyon&quartier=Gerland")

        data = response.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["url"], "https://example.com/a")

    def test_list_annonces_rejects_invalid_pagination(self):
        response = self.client.get("/api/annonces?page=abc")
        self.assertEqual(response.status_code, 400)

        response = self.client.get("/api/annonces?page=0")
        self.assertEqual(response.status_code, 400)

    def test_list_annonces_sorts_by_prix(self):
        annonces_store.upsert_annonce(url="https://example.com/a", prix=1200, db_path=self.db_path)
        annonces_store.upsert_annonce(url="https://example.com/b", prix=800, db_path=self.db_path)

        response = self.client.get("/api/annonces?sort=prix&order=asc")

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["prix"] for item in data["items"]], [800, 1200])

    def test_list_annonces_rejects_invalid_sort(self):
        response = self.client.get("/api/annonces?sort=bogus")
        self.assertEqual(response.status_code, 400)

    def test_list_annonces_rejects_invalid_order(self):
        response = self.client.get("/api/annonces?sort=prix&order=bogus")
        self.assertEqual(response.status_code, 400)

    def test_get_annonce_detail_returns_the_annonce(self):
        created = annonces_store.upsert_annonce(
            titre="T3 Confluence", url="https://example.com/c", db_path=self.db_path,
        )

        response = self.client.get(f"/api/annonces/{created['id']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["titre"], "T3 Confluence")

    def test_get_annonce_detail_returns_404_when_missing(self):
        response = self.client.get("/api/annonces/999999")

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.get_json())

    def test_log_click_returns_the_updated_view_count(self):
        created = annonces_store.upsert_annonce(url="https://example.com/click", db_path=self.db_path)

        first = self.client.post(f"/api/annonces/{created['id']}/click")
        second = self.client.post(f"/api/annonces/{created['id']}/click")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json(), {"logged": True, "views": 1})
        self.assertEqual(second.get_json(), {"logged": True, "views": 2})

    def test_log_click_returns_404_when_annonce_missing(self):
        response = self.client.post("/api/annonces/999999/click")

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
