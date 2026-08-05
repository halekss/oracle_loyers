"""
L'Oracle des Loyers — DAG Annonces (scraping + modèle)

Fusionne les annonces immobilières scrapées (6 sites), calcule les features
de distance aux POI, ré-entraîne le modèle et régénère la carte statique.

Cadence hebdomadaire, volontairement découplée du DAG cavaliers
(oracle_cavaliers_dag.py) : les annonces ont besoin d'un rafraîchissement
plus fréquent que les POI, et ce pipeline ne doit pas rester bloqué par la
lenteur/flakiness de l'API Overpass externe. `clean_immo.py` lit simplement
le cavaliers_lyon.csv le plus récent sur disque, produit indépendamment par
oracle_cavaliers_pipeline — pas de dépendance inter-DAG nécessaire.

Architecture : data_fusion → clean_immo → train_model → generate_map
"""

from datetime import timedelta
import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

SCRIPTS = "/opt/airflow/backend/scripts"

default_args = {
    "owner": "aymeric",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="oracle_annonces_pipeline",
    default_args=default_args,
    description="Pipeline ETL : Annonces → Features → Modèle → Carte — cadence hebdomadaire",
    # 22h Europe/Paris (pas 2h du matin) : c'est le créneau où la machine qui
    # héberge Airflow a le plus de chances d'être allumée. Timezone explicite
    # (pas juste un décalage UTC figé) pour rester correct malgré les
    # changements d'heure été/hiver.
    schedule="0 22 * * 1",
    start_date=pendulum.datetime(2026, 2, 18, tz="Europe/Paris"),
    catchup=False,
    tags=["oracle", "etl", "immo", "annonces"],
) as dag:

    # Fusionne les 6 CSV d'annonces (Century21, Orpi, SeLoger, PAP, ParuVendu, Vizzit)
    # Écrit : backend/data/base_de_donnees_immo_lyon_complet.csv
    step_fusion = BashOperator(
        task_id="data_fusion",
        bash_command=f"cd {SCRIPTS} && python data_fusion.py",
    )

    # Calcule les 40 features de distance (BallTree) + géocodage + quartiers
    # Lit : base_immo_complet.csv + cavaliers_lyon.csv (le plus récent sur
    # disque, produit par oracle_cavaliers_pipeline — pas forcément du même jour)
    # Écrit : master_immo_final.csv
    step_features = BashOperator(
        task_id="clean_immo",
        bash_command=f"cd {SCRIPTS} && python clean_immo.py",
    )

    # Entraîne XGBoost sur le master
    # Écrit : backend/models/price_predictor.pkl
    step_train = BashOperator(
        task_id="train_model",
        bash_command=f"cd {SCRIPTS} && python train_model.py",
    )

    # Régénère la carte statique à partir des données/modèle à jour, pour
    # éviter toute péremption silencieuse (ORA-54).
    # Écrit : frontend/public/data/map_pings_lyon_calques.html + map_metadata.json
    step_generate_map = BashOperator(
        task_id="generate_map",
        bash_command=f"cd {SCRIPTS} && python generate_map.py",
    )

    step_fusion >> step_features >> step_train >> step_generate_map
