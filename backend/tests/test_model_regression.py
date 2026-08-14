import os
import sys
import unittest

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as app_module

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "master_immo_final.csv")

# Bornes de non-régression PAR VILLE (ORA-154 : un modèle XGBoost distinct
# par ville, chacun avec sa propre histoire de métriques — comparer un seuil
# unique aux deux reviendrait au problème que ce ticket corrige : mélanger
# des gammes de prix différentes gonfle mécaniquement la variance testée).
# Lille est un jeu de données plus jeune (moins d'annonces, quartiers
# limitrophes à faible échantillon) : un plancher R² plus bas est un choix
# assumé (voir ORA-154 "coût accepté"), pas un oubli. On garde une marge
# confortable au-dessus/en-dessous des métriques observées (voir
# backend/models/training_metrics_<ville>.jsonl) pour ne pas casser la CI
# sur un léger recalcul, tout en détectant une vraie dégradation.
REGRESSION_THRESHOLDS = {
    "Lyon": {"max_mae": 280, "min_r2": 0.45},
    "Lille": {"max_mae": 230, "min_r2": 0.40},
}


def _prepare_features(df):
    """Reproduit exactement le prétraitement de train_model.py (ORA-154,
    ORA-155), pour obtenir le même jeu de features à partir des mêmes
    données brutes. `ville` est toujours exclue : constante au sein d'un
    modèle par ville, elle n'apporterait aucune information."""
    features_to_drop = [
        'id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'titre',
        'date', 'image', 'ville',
    ]
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
    validation fixe (ORA-35) — un par ville (ORA-154), chacun évalué sur SA
    propre tranche du dataset combiné, avec le même split que
    train_model.py (test_size=0.2, random_state=42)."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(DATA_PATH):
            raise unittest.SkipTest("master_immo_final.csv introuvable.")
        cls.df_all = pd.read_csv(DATA_PATH)

    def _evaluate_ville(self, ville_nom, ville_slug):
        model_path = os.path.join(MODELS_DIR, f"price_predictor_{ville_slug}.pkl")
        if not os.path.exists(model_path):
            self.skipTest(f"{model_path} introuvable.")

        model = joblib.load(model_path)
        df = self.df_all[self.df_all['ville'] == ville_nom]
        y = df['prix']
        X = _prepare_features(df)
        X = X.reindex(columns=model.feature_names_in_, fill_value=0)

        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        predictions = model.predict(X_test)
        return mean_absolute_error(y_test, predictions), r2_score(y_test, predictions)

    def test_lyon_model_metrics_stay_within_acceptable_range(self):
        mae, r2 = self._evaluate_ville("Lyon", "lyon")
        thresholds = REGRESSION_THRESHOLDS["Lyon"]

        self.assertLess(
            mae, thresholds["max_mae"],
            f"MAE {mae:.2f}€ dépasse le seuil de non-régression Lyon ({thresholds['max_mae']}€)",
        )
        self.assertGreater(
            r2, thresholds["min_r2"],
            f"R² {r2:.3f} sous le seuil de non-régression Lyon ({thresholds['min_r2']})",
        )

    def test_lille_model_metrics_stay_within_acceptable_range(self):
        mae, r2 = self._evaluate_ville("Lille", "lille")
        thresholds = REGRESSION_THRESHOLDS["Lille"]

        self.assertLess(
            mae, thresholds["max_mae"],
            f"MAE {mae:.2f}€ dépasse le seuil de non-régression Lille ({thresholds['max_mae']}€)",
        )
        self.assertGreater(
            r2, thresholds["min_r2"],
            f"R² {r2:.3f} sous le seuil de non-régression Lille ({thresholds['min_r2']})",
        )


class VilleExcludedFromFeaturesTest(unittest.TestCase):
    """ORA-154 : un modèle XGBoost distinct par ville plutôt que `ville` en
    feature d'un modèle combiné (approche initiale d'ORA-71, abandonnée —
    voir la justification dans train_model.py). `ville` est désormais
    toujours exclue de l'encodage, quel que soit le nombre de villes
    présentes dans les données brutes passées à _prepare_features."""

    def test_ville_is_never_encoded_as_a_feature(self):
        df = pd.DataFrame({
            'ville': ['Lyon'] * 5 + ['Lille'] * 5,
            'surface': [40, 45, 50, 55, 60, 65, 70, 75, 80, 85],
            'prix': [800, 850, 900, 950, 1000, 500, 550, 600, 650, 700],
        })

        X = _prepare_features(df)

        ville_columns = [c for c in X.columns if c == 'ville' or c.startswith('ville_')]
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
