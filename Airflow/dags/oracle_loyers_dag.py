"""
L'Oracle des Loyers — DAG Airflow

Architecture :
  scrape_cavaliers → enrich_cavaliers ─┐
                                        ├──→ clean_immo → train_model
  data_fusion ──────────────────────────┘
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

SCRIPTS = "/opt/airflow/backend/scripts"
DATA = "/opt/airflow/backend/data"

default_args = {
    "owner": "aymeric",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="oracle_loyers_pipeline",
    default_args=default_args,
    description="Pipeline ETL : Cavaliers + Annonces → Features → Modèle",
    schedule="0 2 * * *",
    start_date=datetime(2026, 2, 18),
    catchup=False,
    tags=["oracle", "etl", "immo"],
) as dag:

    # BRANCHE 1A : Scrape les 21 catégories de lieux via Overpass (OSM)
    # Écrit : backend/data/cavaliers_lyon.csv (~1668 lieux)
    step_scrape = BashOperator(
        task_id="scrape_cavaliers_osm",
        bash_command=f"cd {DATA} && python {SCRIPTS}/api_overpass.py",
        execution_timeout=timedelta(minutes=15),
    )

    # BRANCHE 1B : Enrichit le CSV cavaliers avec le code postal via API Data Gouv
    # Lit/Écrit : backend/data/cavaliers_lyon.csv
    step_enrich = BashOperator(
        task_id="enrich_cavaliers_cp",
        bash_command=f"cd {SCRIPTS} && python enrich_cavaliers_cp.py",
    )

    # BRANCHE 2 : Fusionne les 6 CSV d'annonces (Century21, Orpi, SeLoger, PAP, ParuVendu, Vizzit)
    # Écrit : backend/data/base_de_donnees_immo_lyon_complet.csv
    step_fusion = BashOperator(
        task_id="data_fusion",
        bash_command=f"cd {SCRIPTS} && python data_fusion.py",
    )

    # JONCTION : Calcule les 40 features de distance (BallTree) + géocodage + quartiers
    # Lit : base_immo_complet.csv + cavaliers_lyon.csv
    # Écrit : master_immo_final.csv
    step_features = BashOperator(
        task_id="clean_immo",
        bash_command=f"cd {SCRIPTS} && python clean_immo.py",
    )

    # FINAL : Entraîne XGBoost sur le master
    # Écrit : backend/models/price_predictor.pkl
    step_train = BashOperator(
        task_id="train_model",
        bash_command=f"cd {SCRIPTS} && python train_model.py",
    )

    # ORDRE : 2 branches parallèles → jonction → modèle
    step_scrape >> step_enrich >> step_features
    step_fusion >> step_features
    step_features >> step_train
