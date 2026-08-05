"""
L'Oracle des Loyers — DAG Cavaliers (POI)

Scrape les points d'intérêt ("cavaliers" : Vice/Gentrification/Nuisance/
Superstition) via Overpass (OSM) et les enrichit avec leur code postal.

Cadence mensuelle, volontairement découplée du DAG annonces
(oracle_annonces_dag.py) : ces lieux ne bougent pas d'un jour à l'autre,
contrairement aux annonces, et l'API Overpass publique est rate-limitée
(21 catégories × jusqu'à 3 miroirs, retries sur 429/504 — un run complet
mesuré en conditions réelles dépasse déjà 15 min, cf. execution_timeout
ci-dessous). Un `clean_immo.py` lancé côté annonces lit simplement le
cavaliers_lyon.csv le plus récent sur disque, sans dépendance inter-DAG.

Architecture : scrape_cavaliers_osm → enrich_cavaliers_cp
"""

from datetime import timedelta
import pendulum
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
    dag_id="oracle_cavaliers_pipeline",
    default_args=default_args,
    description="Pipeline ETL : POI (cavaliers) via Overpass — cadence mensuelle",
    # 22h Europe/Paris (pas 2h du matin) : c'est le créneau où la machine qui
    # héberge Airflow a le plus de chances d'être allumée. Timezone explicite
    # (pas juste un décalage UTC figé) pour rester correct malgré les
    # changements d'heure été/hiver.
    schedule="0 22 1 * *",
    start_date=pendulum.datetime(2026, 2, 18, tz="Europe/Paris"),
    catchup=False,
    tags=["oracle", "etl", "immo", "cavaliers"],
) as dag:

    # Scrape les 21 catégories de lieux via Overpass (OSM)
    # Écrit : backend/data/cavaliers_lyon.csv (~1700 lieux)
    step_scrape = BashOperator(
        task_id="scrape_cavaliers_osm",
        bash_command=f"cd {DATA} && python {SCRIPTS}/api_overpass.py",
        # 21 catégories × jusqu'à 3 miroirs Overpass, chacun pouvant retenter
        # sur 429/504 : un run complet réussi a été mesuré à plus de 15 min en
        # conditions réelles (2026-08-05), et les 504 récurrents des miroirs
        # publics sur les catégories à fort volume peuvent dépasser cette
        # marge même en cas de succès final. Portée à 45 min.
        execution_timeout=timedelta(minutes=45),
    )

    # Enrichit le CSV cavaliers avec le code postal via API Data Gouv
    # Lit/Écrit : backend/data/cavaliers_lyon.csv
    step_enrich = BashOperator(
        task_id="enrich_cavaliers_cp",
        bash_command=f"cd {SCRIPTS} && python enrich_cavaliers_cp.py",
    )

    step_scrape >> step_enrich
