import os
import tempfile
import unittest

import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import annonces_store


class AnnoncesStoreTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        annonces_store.init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_upsert_creates_a_new_annonce(self):
        annonce = annonces_store.upsert_annonce(
            titre="T2 Gerland",
            prix=850,
            surface=45,
            ville="Lyon",
            quartier="Gerland",
            url="https://example.com/annonce-1",
            images=["https://example.com/img1.jpg"],
            db_path=self.db_path,
        )

        self.assertIsNotNone(annonce["id"])
        self.assertEqual(annonce["titre"], "T2 Gerland")
        self.assertEqual(annonce["images"], ["https://example.com/img1.jpg"])

    def test_upsert_without_url_raises(self):
        with self.assertRaises(ValueError):
            annonces_store.upsert_annonce(titre="Sans url", db_path=self.db_path)

    def test_upsert_with_blank_url_raises(self):
        with self.assertRaises(ValueError):
            annonces_store.upsert_annonce(titre="Url vide", url="   ", db_path=self.db_path)

    def test_upsert_on_existing_url_updates_instead_of_duplicating(self):
        annonces_store.upsert_annonce(
            titre="Ancien titre", prix=800, url="https://example.com/annonce-2",
            db_path=self.db_path,
        )
        annonces_store.upsert_annonce(
            titre="Nouveau titre", prix=900, url="https://example.com/annonce-2",
            db_path=self.db_path,
        )

        result = annonces_store.list_annonces(db_path=self.db_path)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["titre"], "Nouveau titre")
        self.assertEqual(result["items"][0]["prix"], 900)

    def test_list_annonces_filters_by_ville_and_quartier(self):
        annonces_store.upsert_annonce(
            url="https://example.com/a", ville="Lyon", quartier="Gerland", db_path=self.db_path,
        )
        annonces_store.upsert_annonce(
            url="https://example.com/b", ville="Lyon", quartier="Croix-Rousse", db_path=self.db_path,
        )
        annonces_store.upsert_annonce(
            url="https://example.com/c", ville="Villeurbanne", quartier="Gratte-Ciel", db_path=self.db_path,
        )

        result = annonces_store.list_annonces(ville="Lyon", quartier="Gerland", db_path=self.db_path)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["url"], "https://example.com/a")

    def test_list_annonces_paginates(self):
        for i in range(5):
            annonces_store.upsert_annonce(url=f"https://example.com/{i}", db_path=self.db_path)

        page_1 = annonces_store.list_annonces(page=1, per_page=2, db_path=self.db_path)
        page_2 = annonces_store.list_annonces(page=2, per_page=2, db_path=self.db_path)

        self.assertEqual(page_1["total"], 5)
        self.assertEqual(page_1["total_pages"], 3)
        self.assertEqual(len(page_1["items"]), 2)
        self.assertEqual(len(page_2["items"]), 2)
        self.assertNotEqual(page_1["items"], page_2["items"])

    def test_get_annonce_by_id_returns_none_when_missing(self):
        self.assertIsNone(annonces_store.get_annonce_by_id(999, db_path=self.db_path))

    def test_get_annonce_by_id_returns_the_annonce(self):
        created = annonces_store.upsert_annonce(
            titre="T3 Confluence", url="https://example.com/annonce-3", db_path=self.db_path,
        )

        fetched = annonces_store.get_annonce_by_id(created["id"], db_path=self.db_path)

        self.assertEqual(fetched["titre"], "T3 Confluence")

    def test_count_clicks_is_zero_when_no_click_logged(self):
        created = annonces_store.upsert_annonce(url="https://example.com/d", db_path=self.db_path)

        self.assertEqual(annonces_store.count_clicks(created["id"], db_path=self.db_path), 0)

    def test_log_click_increments_the_click_count(self):
        created = annonces_store.upsert_annonce(url="https://example.com/e", db_path=self.db_path)

        annonces_store.log_click(created["id"], db_path=self.db_path)
        annonces_store.log_click(created["id"], db_path=self.db_path)

        self.assertEqual(annonces_store.count_clicks(created["id"], db_path=self.db_path), 2)

    def test_log_click_does_not_affect_other_annonces(self):
        annonce_a = annonces_store.upsert_annonce(url="https://example.com/f", db_path=self.db_path)
        annonce_b = annonces_store.upsert_annonce(url="https://example.com/g", db_path=self.db_path)

        annonces_store.log_click(annonce_a["id"], db_path=self.db_path)

        self.assertEqual(annonces_store.count_clicks(annonce_a["id"], db_path=self.db_path), 1)
        self.assertEqual(annonces_store.count_clicks(annonce_b["id"], db_path=self.db_path), 0)

    def test_delete_annonce_by_url_removes_it(self):
        annonces_store.upsert_annonce(url="https://example.com/dead", db_path=self.db_path)

        deleted = annonces_store.delete_annonce(url="https://example.com/dead", db_path=self.db_path)

        self.assertTrue(deleted)
        self.assertEqual(annonces_store.list_annonces(db_path=self.db_path)["total"], 0)

    def test_delete_annonce_by_id_removes_it(self):
        created = annonces_store.upsert_annonce(url="https://example.com/dead-2", db_path=self.db_path)

        deleted = annonces_store.delete_annonce(annonce_id=created["id"], db_path=self.db_path)

        self.assertTrue(deleted)
        self.assertIsNone(annonces_store.get_annonce_by_id(created["id"], db_path=self.db_path))

    def test_delete_annonce_unknown_url_returns_false(self):
        deleted = annonces_store.delete_annonce(url="https://example.com/never-existed", db_path=self.db_path)

        self.assertFalse(deleted)

    def test_delete_annonce_requires_exactly_one_identifier(self):
        with self.assertRaises(ValueError):
            annonces_store.delete_annonce(db_path=self.db_path)
        with self.assertRaises(ValueError):
            annonces_store.delete_annonce(url="https://example.com/x", annonce_id=1, db_path=self.db_path)

    def test_delete_annonce_also_removes_its_clicks(self):
        created = annonces_store.upsert_annonce(url="https://example.com/h", db_path=self.db_path)
        annonces_store.log_click(created["id"], db_path=self.db_path)

        annonces_store.delete_annonce(annonce_id=created["id"], db_path=self.db_path)

        conn = annonces_store.get_connection(self.db_path)
        try:
            remaining_clics = conn.execute(
                "SELECT COUNT(*) FROM clics WHERE annonce_id = ?", (created["id"],)
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(remaining_clics, 0)


if __name__ == "__main__":
    unittest.main()
