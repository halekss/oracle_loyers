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


class GetPointForZipcodeZonesLimitrophesTest(unittest.TestCase):
    def test_lambersart_point_stays_within_its_own_circle_not_clipped_to_lille(self):
        # Régression réelle : Lambersart borde directement Lille — un clip à
        # LILLE_COMMUNE_POLYGON (comme pour Lomme/Hellemmes, qui EN font
        # partie) placerait ses annonces du mauvais côté de la frontière.
        # Lambersart n'est jamais clippée : on vérifie ici que le point tiré
        # reste dans son propre cercle plutôt que d'être forcé vers Lille.
        z = clean_immo.ZONES_LIMITROPHES_LILLE["Lambersart"]
        for _ in range(20):
            lat, lon = clean_immo.get_point_for_zipcode("59130", {})
            dist_sq = (lat - z["lat"]) ** 2 + (lon - z["lon"]) ** 2
            self.assertLessEqual(dist_sq, z["radius"] ** 2 * 1.0001)

    def test_unknown_zone_limitrophe_cp_falls_through_to_lille_branch(self):
        # CP réel Lille (pas une commune limitrophe) : ne doit pas passer par
        # la branche ZONES_LIMITROPHES_LILLE.
        self.assertNotIn("59000", clean_immo.CP_A_ZONE_LIMITROPHE)


class MatchQuartierLilleTest(unittest.TestCase):
    def test_point_inside_wazemmes_bbox_returns_wazemmes(self):
        # Ce point est exactement le centroïde de Wazemmes, MAIS il tombe
        # aussi dans la boîte de Vauban-Esquermes (chevauchement de deux
        # quartiers limitrophes) : c'est donc un cas de chevauchement, pas
        # un simple "un seul candidat". Le départage par centroïde le plus
        # proche choisit Wazemmes (distance 0). Ce test seul ne prouve pas
        # que le filtrage par boîte est actif (voir test dédié plus bas pour
        # ça) — il documente/couvre le comportement en cas de chevauchement.
        self.assertEqual(clean_immo.match_quartier_lille(50.6243, 3.0466), "Wazemmes")

    def test_point_inside_vieux_lille_bbox_returns_vieux_lille(self):
        self.assertEqual(clean_immo.match_quartier_lille(50.6470, 3.0600), "Vieux-Lille")

    def test_point_outside_all_bboxes_returns_nearest_centroid(self):
        # Loin au sud de Lille-Sud : le centroïde le plus proche doit rester Lille-Sud.
        self.assertEqual(clean_immo.match_quartier_lille(50.590, 3.050), "Lille-Sud")

    def test_point_inside_lille_sud_bbox_but_nearer_bethune_centroid_returns_lille_sud(self):
        # Point (50.601, 3.024) : dans la boîte de Lille-Sud
        # (lat_min=50.6008, lat_max=50.6167, lon_min=3.0236, lon_max=3.0768)
        # mais PAS dans celle de Faubourg de Béthune (lat_min=50.6139).
        # Or son centroïde le plus proche par distance brute est celui de
        # Faubourg de Béthune (50.6191, 3.0355 -> d²≈0.00046) et non celui de
        # Lille-Sud (50.6097, 3.0537 -> d²≈0.00096). Un stub "centroïde le
        # plus proche uniquement" (sans filtrage par boîte) répondrait donc
        # "Faubourg de Béthune" ici, à tort : ce test échoue sous un tel
        # stub et prouve que la boîte englobante est bien consultée en
        # priorité sur la distance au centroïde.
        self.assertEqual(clean_immo.match_quartier_lille(50.601, 3.024), "Lille-Sud")


class ResolveLilleQuartierHintTest(unittest.TestCase):
    def test_known_seloger_slug_maps_to_real_quartier(self):
        url = "https://www.seloger.com/annonces/locations/maison/lille-59/moulins/265435343.htm"
        self.assertEqual(clean_immo.resolve_lille_quartier_hint(url), "Lille-Moulins")

    def test_seloger_slug_for_lomme_sub_area_maps_to_lomme(self):
        url = "https://www.seloger.com/annonces/locations/appartement/lomme-59/lomme-le-marais/123.htm"
        self.assertEqual(clean_immo.resolve_lille_quartier_hint(url), "Lomme")

    def test_seloger_url_without_quartier_segment_returns_none(self):
        url = "https://www.seloger.com/wl-cdp/26HLIM2M3DY3?serp_view=list"
        self.assertIsNone(clean_immo.resolve_lille_quartier_hint(url))

    def test_non_seloger_url_returns_none(self):
        url = "https://www.pap.fr/annonces/appartement-lille-59-r198509818"
        self.assertIsNone(clean_immo.resolve_lille_quartier_hint(url))

    def test_nan_url_returns_none(self):
        self.assertIsNone(clean_immo.resolve_lille_quartier_hint(pd.NA))


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

    def test_lomme_postal_code_returns_lomme_directly(self):
        df = pd.DataFrame([
            {"code_postal": "59160", "latitude": 50.645, "longitude": 2.987, "a_gps_reel": False},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Lomme")

    def test_lambersart_postal_code_returns_lambersart_directly(self):
        # Régression réelle (ORA-71 POC follow-up) : une recherche SeLoger
        # centrée sur Lille remonte aussi des annonces dans des communes
        # limitrophes réelles (pas des communes associées comme
        # Lomme/Hellemmes) — leur CP distinctif suffit à les identifier.
        df = pd.DataFrame([
            {"code_postal": "59130", "latitude": 50.6478, "longitude": 3.0224, "a_gps_reel": False},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Lambersart")

    def test_la_madeleine_postal_code_returns_la_madeleine_directly(self):
        df = pd.DataFrame([
            {"code_postal": "59110", "latitude": 50.6544, "longitude": 3.0733, "a_gps_reel": False},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "La Madeleine")

    def test_faches_thumesnil_postal_code_returns_faches_thumesnil_directly(self):
        df = pd.DataFrame([
            {"code_postal": "59155", "latitude": 50.6026, "longitude": 3.0698, "a_gps_reel": False},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Faches-Thumesnil")

    def test_villeneuve_d_ascq_postal_code_returns_villeneuve_d_ascq_directly(self):
        df = pd.DataFrame([
            {"code_postal": "59650", "latitude": 50.6193, "longitude": 3.1314, "a_gps_reel": False},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Villeneuve-d'Ascq")

    def test_central_cp_with_real_gps_uses_quartier_match(self):
        df = pd.DataFrame([
            {"code_postal": "59800", "latitude": 50.6243, "longitude": 3.0466, "a_gps_reel": True},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Wazemmes")

    def test_real_gps_outside_lille_boundary_does_not_get_a_lille_quartier(self):
        # Régression réelle : Vizzit étiquette parfois une annonce d'une
        # commune voisine comme "Lille" (constaté : une fiche à
        # Croisé-Laroche/Marcq-en-Barœul affichée "Location : Appartement
        # Lille (59000)"). Une vraie coordonnée hors du contour de Lille ne
        # doit jamais forcer un quartier lillois.
        df = pd.DataFrame([
            {"code_postal": "59000", "latitude": 50.68, "longitude": 3.10, "a_gps_reel": True},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Lille / Non localisé")

    def test_central_cp_without_gps_but_seloger_url_hint_uses_real_quartier(self):
        df = pd.DataFrame([
            {
                "code_postal": "59000",
                "latitude": 50.63,
                "longitude": 3.05,
                "a_gps_reel": False,
                "url": "https://www.seloger.com/annonces/locations/appartement/lille-59/wazemmes/999.htm",
            },
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Wazemmes")

    def test_central_cp_without_gps_or_url_hint_returns_generic_fallback(self):
        df = pd.DataFrame([
            {
                "code_postal": "59000",
                "latitude": 50.63,
                "longitude": 3.05,
                "a_gps_reel": False,
                "url": "https://www.pap.fr/annonces/appartement-lille-59-r1",
            },
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Lille / Non localisé")

    def test_central_cp_without_real_gps_returns_generic_fallback(self):
        df = pd.DataFrame([
            {"code_postal": "59000", "latitude": 50.63, "longitude": 3.05, "a_gps_reel": False},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertEqual(result.loc[0, "quartier"], "Lille / Non localisé")

    def test_a_gps_reel_working_column_is_dropped_after_quartiers(self):
        df = pd.DataFrame([
            {"code_postal": "69006", "latitude": 45.77, "longitude": 4.86, "a_gps_reel": True},
        ])

        result = clean_immo.step_quartiers(df)

        self.assertNotIn("a_gps_reel", result.columns)


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

    def test_lyon_listing_never_matched_against_a_lille_only_poi(self):
        # Régression réelle : sans bornage par ville, une annonce Lyon pouvait
        # en théorie chercher son POI le plus proche parmi les cavaliers
        # Lille (et inversement) — sans effet numérique aujourd'hui vu la
        # distance entre les deux villes, mais faux par construction plutôt
        # que juste par coïncidence géographique. On force le cas limite ici
        # en plaçant le cavalier Lille exactement sur les coordonnées de
        # l'annonce Lyon (distance 0 si le bornage ne fonctionne pas).
        df = pd.DataFrame([
            {"latitude": 45.75, "longitude": 4.85, "ville": "Lyon"},
        ])
        df_cavaliers = pd.DataFrame([
            # Cavalier "Lille" (pas de code_postal, convention existante cf.
            # build_shapes_from_cavaliers) collé sur l'annonce Lyon.
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.75, "longitude": 4.85, "code_postal": None},
            # Vrai cavalier Lyon (code_postal renseigné), ~111m plus loin.
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.751, "longitude": 4.85, "code_postal": "69001"},
        ])

        result = clean_immo.step_features(df, df_cavaliers)

        self.assertGreater(result.loc[0, "dist_vice_bar"], 50)

    def test_lille_listing_never_matched_against_a_lyon_only_poi(self):
        df = pd.DataFrame([
            {"latitude": 50.63, "longitude": 3.06, "ville": "Lille"},
        ])
        df_cavaliers = pd.DataFrame([
            # Vrai cavalier Lyon (code_postal renseigné) collé sur l'annonce Lille.
            {"categorie_cavalier": "Vice - Bar", "latitude": 50.63, "longitude": 3.06, "code_postal": "69001"},
            # Cavalier Lille (pas de code_postal), ~111m plus loin.
            {"categorie_cavalier": "Vice - Bar", "latitude": 50.631, "longitude": 3.06, "code_postal": None},
        ])

        result = clean_immo.step_features(df, df_cavaliers)

        self.assertGreater(result.loc[0, "dist_vice_bar"], 50)

    def test_without_ville_column_falls_back_to_the_unscoped_legacy_behaviour(self):
        # Compatibilité : anciens appelants/tests sans colonne `ville` (un
        # seul jeu de données, pas de multi-ville) gardent le comportement
        # d'origine plutôt que de casser.
        df = pd.DataFrame([
            {"latitude": 45.75, "longitude": 4.85},
        ])
        df_cavaliers = pd.DataFrame([
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.75, "longitude": 4.85},
        ])

        result = clean_immo.step_features(df, df_cavaliers)

        self.assertAlmostEqual(result.loc[0, "dist_vice_bar"], 0.0)


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

    def test_lille_cavaliers_without_code_postal_are_grouped_by_quartier(self):
        # Cavaliers Lille (ORA-71 POC) : pas de colonne code_postal (produite
        # uniquement pour Lyon par enrich_cavaliers_cp.py) — regroupement par
        # quartier réel résolu depuis les vraies coordonnées, même principe
        # que Lyon (quadriller la ville à partir des cavaliers) appliqué au
        # bon axe pour cette ville. 4 points dans la boîte de Wazemmes.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "cavaliers_lille.csv")
            df = pd.DataFrame([
                {"latitude": 50.6230, "longitude": 3.0450, "categorie_cavalier": "Vice - Bar"},
                {"latitude": 50.6240, "longitude": 3.0460, "categorie_cavalier": "Vice - Bar"},
                {"latitude": 50.6250, "longitude": 3.0470, "categorie_cavalier": "Vice - Bar"},
                {"latitude": 50.6260, "longitude": 3.0480, "categorie_cavalier": "Vice - Bar"},
            ])
            df.to_csv(path, index=False)

            result = clean_immo.build_shapes_from_cavaliers(path)

            self.assertIn("Wazemmes", result)

    def test_mixed_lyon_and_lille_cavaliers_produce_both_kinds_of_keys(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "cavaliers_all.csv")
            df = pd.DataFrame([
                {"code_postal": "69003", "latitude": 45.755, "longitude": 4.845},
                {"code_postal": "69003", "latitude": 45.757, "longitude": 4.847},
                {"code_postal": "69003", "latitude": 45.759, "longitude": 4.849},
                {"code_postal": "69003", "latitude": 45.756, "longitude": 4.850},
                {"code_postal": None, "latitude": 50.6230, "longitude": 3.0450},
                {"code_postal": None, "latitude": 50.6240, "longitude": 3.0460},
                {"code_postal": None, "latitude": 50.6250, "longitude": 3.0470},
                {"code_postal": None, "latitude": 50.6260, "longitude": 3.0480},
            ])
            df.to_csv(path, index=False)

            result = clean_immo.build_shapes_from_cavaliers(path)

            self.assertIn("69003", result)
            self.assertIn("Wazemmes", result)


if __name__ == "__main__":
    unittest.main()
