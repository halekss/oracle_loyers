"""
L'Oracle des Loyers — DAGs Cavaliers (POI), un par ville

Scrape les points d'intérêt ("cavaliers" : Vice/Gentrification/Nuisance/
Superstition) via Overpass (OSM) et les enrichit avec leur code postal, pour
chaque ville déclarée dans scraping_config.json.

ORA-153 : un run mensuel groupant toutes les villes rendait chaque ajout de
ville (Lille) plus long à scraper, forçait à mutualiser son planning avec
celui de Lyon, et poussait à éditer `ville_active` dans scraping_config.json
à la main entre deux scrapes (le script Overpass ne prenait jusqu'ici aucun
argument de ville). Une DAG distincte par ville, générée dynamiquement à
partir des villes déclarées, permet de scraper/replanifier chaque ville
indépendamment sans toucher au code.

Cadence mensuelle, volontairement découplée du DAG annonces
(oracle_annonces_dag.py) : ces lieux ne bougent pas d'un jour à l'autre,
contrairement aux annonces, et l'API Overpass publique est rate-limitée
(21 catégories × jusqu'à 3 miroirs, retries sur 429/504 — un run complet
mesuré en conditions réelles dépasse déjà 15 min, cf. execution_timeout
ci-dessous).

Architecture (par ville) : scrape_cavaliers_osm → enrich_cavaliers_cp
                                                 → merge_cavaliers_all
`merge_cavaliers_all` régénère cavaliers_all.csv (toutes villes confondues)
à partir des cavaliers_<ville>.csv actuellement sur disque — c'est ce
fichier combiné, et lui seul, que lit clean_immo.py (DAG annonces). Étape
volontairement dupliquée dans chaque DAG ville plutôt que mutualisée entre
elles : c'est une simple concaténation de fichiers déjà scrapés (pas d'appel
réseau), donc rejouable sans coût à chaque run, sans dépendance inter-DAG.
"""

import json
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

SCRIPTS = "/opt/airflow/backend/scripts"
DATA = "/opt/airflow/backend/data"
SCRAPING_CONFIG_PATH = "/opt/airflow/scripts/scraping_config.json"

default_args = {
    "owner": "aymeric",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with open(SCRAPING_CONFIG_PATH, encoding="utf-8") as f:
    VILLES = json.load(f)["villes"]

for slug, ville_config in VILLES.items():
    ville_nom = ville_config["nom"]

    with DAG(
        dag_id=f"oracle_cavaliers_pipeline_{slug}",
        default_args=default_args,
        description=f"Pipeline ETL : POI (cavaliers) via Overpass — {ville_nom}, cadence mensuelle",
        # 22h Europe/Paris (pas 2h du matin) : c'est le créneau où la machine qui
        # héberge Airflow a le plus de chances d'être allumée. Timezone explicite
        # (pas juste un décalage UTC figé) pour rester correct malgré les
        # changements d'heure été/hiver.
        schedule="0 22 1 * *",
        start_date=pendulum.datetime(2026, 2, 18, tz="Europe/Paris"),
        catchup=False,
        tags=["oracle", "etl", "immo", "cavaliers", slug],
    ) as dag:

        # Scrape les 21 catégories de lieux via Overpass (OSM) pour cette ville
        # Écrit : backend/data/cavaliers_<slug>.csv
        step_scrape = BashOperator(
            task_id="scrape_cavaliers_osm",
            bash_command=f"cd {DATA} && python {SCRIPTS}/api_overpass.py --ville {slug}",
            # 21 catégories × jusqu'à 3 miroirs Overpass, chacun pouvant retenter
            # sur 429/504 : un run complet réussi a été mesuré à plus de 15 min en
            # conditions réelles (2026-08-05), et les 504 récurrents des miroirs
            # publics sur les catégories à fort volume peuvent dépasser cette
            # marge même en cas de succès final. Portée à 45 min.
            execution_timeout=timedelta(minutes=45),
        )

        # Enrichit le CSV cavaliers de cette ville avec le code postal (API Data Gouv)
        # Lit/Écrit : backend/data/cavaliers_<slug>.csv
        step_enrich = BashOperator(
            task_id="enrich_cavaliers_cp",
            bash_command=f"cd {SCRIPTS} && python enrich_cavaliers_cp.py --ville {slug}",
        )

        # Régénère cavaliers_all.csv (toutes villes) à partir des cavaliers_<ville>.csv
        # actuellement sur disque — le fichier réellement lu par clean_immo.py.
        step_merge = BashOperator(
            task_id="merge_cavaliers_all",
            bash_command=f"cd {SCRIPTS} && python merge_cavaliers_villes.py",
        )

        step_scrape >> step_enrich >> step_merge

    # Idiome Airflow pour l'enregistrement de DAGs générées dynamiquement en
    # boucle : le DagFileProcessor découvre les DAG par leurs objets exposés
    # dans les globals du module, pas seulement au niveau top-level du fichier.
    globals()[dag.dag_id] = dag
