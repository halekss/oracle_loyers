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
    """ORA-154 : un modèle XGBoost distinct par ville plutôt qu'un modèle
    combiné — build_feature_row reçoit désormais un jeu de features PAR
    ville (`feature_names_by_ville`) et route vers le bon jeu une fois la
    ville déduite du quartier résolu."""

    def setUp(self):
        self.df = pd.DataFrame([
            {"quartier": "Gerland", "ville": "Lyon", "type_local": "T2", "latitude": 45.75, "longitude": 4.85, "code_postal": 69007},
            {"quartier": "Wazemmes", "ville": "Lille", "type_local": "T2", "latitude": 50.63, "longitude": 3.05, "code_postal": 59000},
        ])
        self.lyon_feature_names = [
            "surface", "code_postal", "latitude", "longitude",
            "type_Appartement", "type_local_T2", "quartier_Gerland",
        ]
        self.lille_feature_names = [
            "surface", "code_postal", "latitude", "longitude",
            "type_Appartement", "type_local_T2", "quartier_Wazemmes",
        ]
        self.feature_names_by_ville = {
            "Lyon": self.lyon_feature_names,
            "Lille": self.lille_feature_names,
        }

    def test_accepts_a_quartier_present_in_its_ville_model_features(self):
        features_df, result = build_feature_row(
            {"surface": 40, "quartier": "Gerland", "type_local": "T2"},
            self.df, None, self.feature_names_by_ville,
        )

        self.assertIsNotNone(features_df)
        self.assertEqual(result["quartier"], "Gerland")
        self.assertEqual(result["ville"], "Lyon")

    def test_routes_a_ville_with_its_own_registered_model(self):
        """Le point même d'ORA-154 : avant, un quartier Lille échouait car le
        modèle combiné n'avait jamais vu Lille. Avec un modèle Lille dédié
        (quartier_Wazemmes dans SES features), la requête aboutit."""
        features_df, result = build_feature_row(
            {"surface": 40, "quartier": "Wazemmes", "type_local": "T2"},
            self.df, None, self.feature_names_by_ville,
        )

        self.assertIsNotNone(features_df)
        self.assertEqual(result["ville"], "Lille")

    def test_rejects_a_quartier_absent_from_its_ville_model_features(self):
        # Régression réelle (ORA-99 follow-up) : un quartier peut exister dans
        # les données réelles (df) sans jamais avoir été vu par le modèle
        # promu de sa ville. Sans ce garde-fou, la colonne one-hot est
        # silencieusement ignorée et le modèle prédit à l'aveugle tout en
        # affichant un niveau de confiance basé sur les vraies annonces
        # comparables — trompeur. Le frontend a déjà un repli silencieux sur
        # la moyenne réelle du secteur quand /api/predict échoue.
        feature_names_by_ville = dict(self.feature_names_by_ville)
        feature_names_by_ville["Lyon"] = [c for c in self.lyon_feature_names if c != "quartier_Gerland"]

        features_df, errors = build_feature_row(
            {"surface": 40, "quartier": "Gerland", "type_local": "T2"},
            self.df, None, feature_names_by_ville,
        )

        self.assertIsNone(features_df)
        self.assertTrue(any("Gerland" in e for e in errors))

    def test_rejects_when_no_model_is_registered_for_the_resolved_ville(self):
        features_df, errors = build_feature_row(
            {"surface": 40, "quartier": "Wazemmes", "type_local": "T2"},
            self.df, None, {"Lyon": self.lyon_feature_names},
        )

        self.assertIsNone(features_df)
        self.assertTrue(any("Lille" in e for e in errors))

    def test_scopes_distance_features_to_the_listings_ville(self):
        cavaliers = pd.DataFrame([
            # Cavalier "Lille" collé sur les coordonnées de Gerland (Lyon).
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.75, "longitude": 4.85, "code_postal": None},
            # Vrai cavalier Lyon, ~111m plus loin.
            {"categorie_cavalier": "Vice - Bar", "latitude": 45.751, "longitude": 4.85, "code_postal": "69007"},
        ])
        feature_names_by_ville = dict(self.feature_names_by_ville)
        feature_names_by_ville["Lyon"] = self.lyon_feature_names + ["dist_vice_bar"]

        features_df, _ = build_feature_row(
            {"surface": 40, "quartier": "Gerland", "type_local": "T2", "latitude": 45.75, "longitude": 4.85},
            self.df, cavaliers, feature_names_by_ville,
        )

        self.assertGreater(features_df.loc[0, "dist_vice_bar"], 50)


if __name__ == "__main__":
    unittest.main()
