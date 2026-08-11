import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.predictor import build_feature_row, scope_cavaliers_to_ville


class ScopeCavaliersToVilleTest(unittest.TestCase):
    def setUp(self):
        self.cavaliers = pd.DataFrame([
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.75, "longitude": 4.85, "code_postal": "69001"},
            {"categorie_cavalier": "Vice - Bar", "latitude": 50.63, "longitude": 3.06, "code_postal": None},
        ])

    def test_lyon_keeps_only_rows_with_code_postal(self):
        result = scope_cavaliers_to_ville(self.cavaliers, "Lyon")

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["code_postal"], "69001")

    def test_lille_keeps_only_rows_without_code_postal(self):
        result = scope_cavaliers_to_ville(self.cavaliers, "Lille")

        self.assertEqual(len(result), 1)
        self.assertTrue(pd.isna(result.iloc[0]["code_postal"]))

    def test_unknown_ville_returns_unchanged(self):
        result = scope_cavaliers_to_ville(self.cavaliers, None)

        self.assertEqual(len(result), 2)

    def test_missing_code_postal_column_returns_unchanged(self):
        cavaliers_sans_cp = self.cavaliers.drop(columns=["code_postal"])

        result = scope_cavaliers_to_ville(cavaliers_sans_cp, "Lyon")

        self.assertEqual(len(result), 2)


class BuildFeatureRowTest(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
            {"quartier": "Gerland", "ville": "Lyon", "type_local": "T2", "latitude": 45.75, "longitude": 4.85, "code_postal": 69007},
            {"quartier": "Wazemmes", "ville": "Lille", "type_local": "T2", "latitude": 50.63, "longitude": 3.05, "code_postal": 59000},
        ])
        self.feature_names = [
            "surface", "code_postal", "latitude", "longitude",
            "type_Appartement", "type_local_T2", "quartier_Gerland",
        ]

    def test_accepts_a_quartier_present_in_the_model_features(self):
        features_df, result = build_feature_row(
            {"surface": 40, "quartier": "Gerland", "type_local": "T2"},
            self.df, None, self.feature_names,
        )

        self.assertIsNotNone(features_df)
        self.assertEqual(result["quartier"], "Gerland")

    def test_rejects_a_quartier_absent_from_the_model_features(self):
        # Régression réelle (ORA-99 follow-up) : le modèle actif n'a jamais
        # été entraîné avec des données Lille (quartier_Wazemmes absent de
        # feature_names). Sans ce garde-fou, la colonne one-hot est
        # silencieusement ignorée et le modèle prédit à l'aveugle tout en
        # affichant un niveau de confiance basé sur les vraies annonces
        # comparables — trompeur. Le frontend a déjà un repli silencieux sur
        # la moyenne réelle du secteur quand /api/predict échoue.
        features_df, errors = build_feature_row(
            {"surface": 40, "quartier": "Wazemmes", "type_local": "T2"},
            self.df, None, self.feature_names,
        )

        self.assertIsNone(features_df)
        self.assertTrue(any("Wazemmes" in e for e in errors))

    def test_scopes_distance_features_to_the_listings_ville(self):
        cavaliers = pd.DataFrame([
            # Cavalier "Lille" collé sur les coordonnées de Gerland (Lyon).
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.75, "longitude": 4.85, "code_postal": None},
            # Vrai cavalier Lyon, ~111m plus loin.
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.751, "longitude": 4.85, "code_postal": "69007"},
        ])
        feature_names = self.feature_names + ["dist_vice_bar"]

        features_df, _ = build_feature_row(
            {"surface": 40, "quartier": "Gerland", "type_local": "T2", "latitude": 45.75, "longitude": 4.85},
            self.df, cavaliers, feature_names,
        )

        self.assertGreater(features_df.loc[0, "dist_vice_bar"], 50)


if __name__ == "__main__":
    unittest.main()
