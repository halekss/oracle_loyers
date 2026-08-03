import os
import sys
import unittest

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as app_module

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "price_predictor.pkl")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "master_immo_final.csv")

# Bornes de non-régression : le modèle actuel obtient MAE≈167€ / R²≈0.75 sur ce
# jeu de données (voir backend/models/training_metrics.jsonl). On garde une
# marge confortable pour ne pas casser la CI sur un léger recalcul, tout en
# détectant une vraie dégradation du modèle.
MAX_ACCEPTABLE_MAE = 250
MIN_ACCEPTABLE_R2 = 0.6


def _prepare_features(df):
    """Reproduit exactement le prétraitement de train_model.py, pour obtenir
    le même jeu de features à partir des mêmes données brutes."""
    features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'titre', 'date']
    X = df.drop(columns=features_to_drop, errors='ignore')

    cols_nb = [c for c in X.columns if c.startswith('nb_')]
    X = X.drop(columns=cols_nb)

    cols_text = X.select_dtypes(include=['object']).columns
    if len(cols_text) > 0:
        X = pd.get_dummies(X, columns=cols_text, drop_first=True)

    return X.apply(pd.to_numeric, errors='coerce').fillna(0)


class ModelRegressionTest(unittest.TestCase):
    """Remplace backend/scripts/test_prediction.py (script manuel, échantillon
    aléatoire non reproductible) par un test de non-régression sur un jeu de
    validation fixe (ORA-35)."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(MODEL_PATH):
            raise unittest.SkipTest("Modèle price_predictor.pkl introuvable.")

        cls.model = joblib.load(MODEL_PATH)
        df = pd.read_csv(DATA_PATH)
        y = df['prix']
        X = _prepare_features(df)
        X = X.reindex(columns=cls.model.feature_names_in_, fill_value=0)

        # Même split que train_model.py (test_size=0.2, random_state=42) :
        # jeu de validation fixe et reproductible d'un run à l'autre.
        _, cls.X_test, _, cls.y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    def test_model_metrics_stay_within_acceptable_range_on_fixed_validation_set(self):
        predictions = self.model.predict(self.X_test)
        mae = mean_absolute_error(self.y_test, predictions)
        r2 = r2_score(self.y_test, predictions)

        self.assertLess(
            mae, MAX_ACCEPTABLE_MAE,
            f"MAE {mae:.2f}€ dépasse le seuil de non-régression ({MAX_ACCEPTABLE_MAE}€)",
        )
        self.assertGreater(
            r2, MIN_ACCEPTABLE_R2,
            f"R² {r2:.3f} sous le seuil de non-régression ({MIN_ACCEPTABLE_R2})",
        )


class MultiCityFeatureGenericizationTest(unittest.TestCase):
    """ORA-71 : `ville` n'est plus dans `features_to_drop` (contrairement à avant),
    donc encodée comme les autres colonnes texte (`quartier`, `type_local`). Ces
    tests vérifient que le mécanisme fonctionne avec une ville fictive de test —
    pas une vraie deuxième ville en production, qui reste un travail séparé
    (vérification live des 6 scrapers, choix de la ville)."""

    def test_ville_becomes_a_feature_once_a_second_city_exists(self):
        df = pd.DataFrame({
            'ville': ['Lyon'] * 5 + ['VilleFictiveTest'] * 5,
            'surface': [40, 45, 50, 55, 60, 65, 70, 75, 80, 85],
            'prix': [800, 850, 900, 950, 1000, 500, 550, 600, 650, 700],
        })

        X = _prepare_features(df)

        self.assertIn('ville_VilleFictiveTest', X.columns)

    def test_ville_produces_no_extra_feature_with_a_single_city(self):
        """Avec une seule ville (l'état actuel du projet), le one-hot de `ville`
        ne produit aucune colonne (drop_first supprime l'unique catégorie) :
        aucun changement de comportement du modèle actuel."""
        df = pd.DataFrame({
            'ville': ['Lyon'] * 5,
            'surface': [40, 45, 50, 55, 60],
            'prix': [800, 850, 900, 950, 1000],
        })

        X = _prepare_features(df)

        ville_columns = [c for c in X.columns if c.startswith('ville_')]
        self.assertEqual(ville_columns, [])


class PredictEndpointRegressionTest(unittest.TestCase):
    def test_predict_endpoint_does_not_regress_to_placeholder_zero(self):
        """Non-régression explicite du bug corrigé par ORA-30 : /api/predict
        renvoyait auparavant toujours {"estimated_price": 0, ...}."""
        client = app_module.app.test_client()

        response = client.post(
            "/api/predict",
            json={"surface": 50, "quartier": "Gerland", "type_local": "T2"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertNotEqual(data["estimated_price"], 0)
        self.assertGreater(data["estimated_price"], 100)
        self.assertLess(data["estimated_price"], 10000)


if __name__ == "__main__":
    unittest.main()
