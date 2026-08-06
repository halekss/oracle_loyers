import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import clean_immo


class StepPruneExpiredTest(unittest.TestCase):
    def test_keeps_recently_seen_annonces(self):
        reference = pd.Timestamp("2026-08-06", tz="UTC")
        df = pd.DataFrame([{"url": "https://example.com/1", "date_dernier_scan": "2026-08-01"}])

        result = clean_immo.step_prune_expired(df, ttl_days=14, reference_date=reference)

        self.assertEqual(len(result), 1)

    def test_drops_annonces_not_seen_within_ttl(self):
        reference = pd.Timestamp("2026-08-06", tz="UTC")
        df = pd.DataFrame([{"url": "https://example.com/1", "date_dernier_scan": "2026-07-01"}])

        result = clean_immo.step_prune_expired(df, ttl_days=14, reference_date=reference)

        self.assertEqual(len(result), 0)

    def test_keeps_rows_with_missing_date_conservatively(self):
        reference = pd.Timestamp("2026-08-06", tz="UTC")
        df = pd.DataFrame([
            {"url": "https://example.com/1", "date_dernier_scan": None},
            {"url": "https://example.com/2", "date_dernier_scan": ""},
        ])

        result = clean_immo.step_prune_expired(df, ttl_days=14, reference_date=reference)

        self.assertEqual(len(result), 2)

    def test_missing_column_returns_dataframe_unchanged(self):
        df = pd.DataFrame([{"url": "https://example.com/1"}])

        result = clean_immo.step_prune_expired(df)

        self.assertEqual(len(result), 1)
        self.assertNotIn("date_dernier_scan", result.columns)

    def test_mixed_batch_keeps_only_fresh_and_unknown(self):
        reference = pd.Timestamp("2026-08-06", tz="UTC")
        df = pd.DataFrame([
            {"url": "https://example.com/fresh", "date_dernier_scan": "2026-08-05"},
            {"url": "https://example.com/expired", "date_dernier_scan": "2026-07-01"},
            {"url": "https://example.com/unknown", "date_dernier_scan": None},
        ])

        result = clean_immo.step_prune_expired(df, ttl_days=14, reference_date=reference)

        self.assertEqual(
            set(result["url"]),
            {"https://example.com/fresh", "https://example.com/unknown"},
        )


class StepQuartiersTest(unittest.TestCase):
    def test_known_code_postal_and_coordinates_returns_named_quartier(self):
        df = pd.DataFrame([
            {"code_postal": "69006", "latitude": 45.77, "longitude": 4.86},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Brotteaux / Foch")

    def test_missing_code_postal_returns_inconnu(self):
        df = pd.DataFrame([
            {"code_postal": None, "latitude": 45.77, "longitude": 4.86},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Inconnu")


class StepTypesTest(unittest.TestCase):
    def test_detects_type_from_text(self):
        df = pd.DataFrame([
            {"type": "Appartement T3", "description": "beau T3 lumineux", "surface": 60},
        ])

        result = clean_immo.step_types(df)

        self.assertEqual(result.loc[0, "type_local"], "T3")

    def test_no_text_signal_and_unparseable_surface_returns_inconnu(self):
        df = pd.DataFrame([
            {"type": "", "description": "", "surface": "N/C"},
        ])

        result = clean_immo.step_types(df)

        self.assertEqual(result.loc[0, "type_local"], "Inconnu")


class StepFeaturesTest(unittest.TestCase):
    def test_computes_nearest_distance_and_count(self):
        df = pd.DataFrame([
            {"latitude": 45.75, "longitude": 4.85},
        ])
        df_cavaliers = pd.DataFrame([
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.75, "longitude": 4.85},
        ])

        result = clean_immo.step_features(df, df_cavaliers)

        self.assertIn("dist_vice_bar", result.columns)
        self.assertAlmostEqual(result.loc[0, "dist_vice_bar"], 0.0)
        self.assertEqual(result.loc[0, "nb_vice_bar_500m"], 1)

    def test_empty_cavaliers_returns_dataframe_unchanged(self):
        df = pd.DataFrame([
            {"latitude": 45.75, "longitude": 4.85},
        ])
        df_cavaliers = pd.DataFrame(columns=['categorie_cavalier', 'latitude', 'longitude'])

        result = clean_immo.step_features(df, df_cavaliers)

        self.assertListEqual(list(result.columns), ["latitude", "longitude"])


class StepIdsTest(unittest.TestCase):
    def test_reindexes_from_one(self):
        df = pd.DataFrame([{"x": 1}, {"x": 2}, {"x": 3}])

        result = clean_immo.step_ids(df)

        self.assertListEqual(list(result["id_annonce"]), [1, 2, 3])

    def test_empty_dataframe_does_not_crash(self):
        df = pd.DataFrame(columns=["x"])

        result = clean_immo.step_ids(df)

        self.assertEqual(len(result), 0)
        self.assertIn("id_annonce", result.columns)


class StepSyncAnnoncesStoreTest(unittest.TestCase):
    def test_syncs_rows_with_url_into_store(self):
        import tempfile

        from services import annonces_store

        df = pd.DataFrame([
            {
                "type_local": "T2",
                "quartier": "Part-Dieu",
                "description": "beau T2 lumineux",
                "prix": 750,
                "surface": 45,
                "ville": "Lyon",
                "url": "https://example.com/annonce-1",
                "image": "https://example.com/photo-1.jpg",
            },
        ])

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "annonces.db")

            result = clean_immo.step_sync_annonces_store(df, db_path=db_path)

            annonces = annonces_store.list_annonces(db_path=db_path)
            self.assertEqual(annonces["total"], 1)
            annonce = annonces["items"][0]
            self.assertEqual(annonce["titre"], "T2 — Part-Dieu")
            self.assertEqual(annonce["prix"], 750)
            self.assertEqual(annonce["url"], "https://example.com/annonce-1")
            self.assertEqual(annonce["images"], ["https://example.com/photo-1.jpg"])
            # step_sync_annonces_store renvoie le dataframe inchangé (étape terminale du pipeline)
            self.assertIs(result, df)

    def test_skips_rows_without_url(self):
        import tempfile

        from services import annonces_store

        df = pd.DataFrame([
            {"type_local": "T3", "quartier": "Croix-Rousse", "prix": 900, "surface": 60,
             "ville": "Lyon", "url": None, "image": None},
        ])

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "annonces.db")

            clean_immo.step_sync_annonces_store(df, db_path=db_path)

            annonces = annonces_store.list_annonces(db_path=db_path)
            self.assertEqual(annonces["total"], 0)

    def test_rerun_upserts_instead_of_duplicating(self):
        import tempfile

        from services import annonces_store

        df = pd.DataFrame([
            {"type_local": "Studio/T1", "quartier": "Guillotière", "prix": 500, "surface": 22,
             "ville": "Lyon", "url": "https://example.com/annonce-2", "image": None},
        ])

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "annonces.db")

            clean_immo.step_sync_annonces_store(df, db_path=db_path)
            clean_immo.step_sync_annonces_store(df, db_path=db_path)

            annonces = annonces_store.list_annonces(db_path=db_path)
            self.assertEqual(annonces["total"], 1)


class BuildTitreTest(unittest.TestCase):
    def test_combines_type_local_and_quartier(self):
        row = pd.Series({"type_local": "T3", "quartier": "Croix-Rousse", "description": ""})

        self.assertEqual(clean_immo.build_titre(row), "T3 — Croix-Rousse")

    def test_falls_back_to_description_when_type_and_quartier_missing(self):
        row = pd.Series({"type_local": "", "quartier": "", "description": "Superbe maison avec jardin"})

        self.assertEqual(clean_immo.build_titre(row), "Superbe maison avec jardin")

    def test_returns_none_when_nothing_available(self):
        row = pd.Series({"type_local": "", "quartier": "", "description": ""})

        self.assertIsNone(clean_immo.build_titre(row))


class BuildShapesFromCavaliersTest(unittest.TestCase):
    def test_missing_file_returns_empty_dict(self):
        result = clean_immo.build_shapes_from_cavaliers("/inexistant.csv")

        self.assertEqual(result, {})

    def test_builds_polygon_for_group_with_enough_points(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "cavaliers.csv")
            df = pd.DataFrame([
                {"code_postal": "69003", "latitude": 45.755, "longitude": 4.845},
                {"code_postal": "69003", "latitude": 45.757, "longitude": 4.847},
                {"code_postal": "69003", "latitude": 45.759, "longitude": 4.849},
                {"code_postal": "69003", "latitude": 45.756, "longitude": 4.850},
            ])
            df.to_csv(path, index=False)

            result = clean_immo.build_shapes_from_cavaliers(path)

            self.assertIn("69003", result)


if __name__ == "__main__":
    unittest.main()
