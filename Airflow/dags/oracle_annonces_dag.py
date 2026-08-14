"""
L'Oracle des Loyers — DAG Annonces (scraping + modèle)

Fusionne les annonces immobilières scrapées (6 sites), calcule les features
de distance aux POI, ré-entraîne le modèle et régénère la carte statique.

ORA-153 : la fusion (data_fusion.py) et la génération de carte
(generate_map.py) sont scindées par ville — chacune tourne indépendamment
pour chaque ville déclarée dans scraping_config.json, sans dépendance
forcée aux autres. `clean_immo` et `train_model` restent en revanche un
step PARTAGÉ, unique pour toutes les villes : le modèle actif est encore
un seul price_predictor.pkl combiné (`ville` en feature, pas un modèle par
ville). Le scinder par ville reviendrait à lancer deux réentraînements
concurrents sur le même fichier de sortie — cf. ORA-154 (modèle séparé par
ville), préalable nécessaire à un vrai découpage par ville de cette partie
de la chaîne. En attendant, `clean_immo`/`train_model` tournent une seule
fois par run, après que TOUTES les fusions par ville se sont terminées.

Cadence hebdomadaire, volontairement découplée du DAG cavaliers
(oracle_cavaliers_pipeline_<ville>.py) : les annonces ont besoin d'un
rafraîchissement plus fréquent que les POI, et ce pipeline ne doit pas
rester bloqué par la lenteur/flakiness de l'API Overpass externe.
`clean_immo` lit cavaliers_all.csv, régénéré par chaque DAG cavaliers
(merge_cavaliers_villes.py) — pas de dépendance inter-DAG directe, juste le
fichier le plus récent sur disque au moment du run.

Architecture : [data_fusion_<ville> pour chaque ville] → clean_immo →
               train_model → [generate_map_<ville> pour chaque ville]
"""

import json
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

SCRIPTS = "/opt/airflow/backend/scripts"
SCRAPING_CONFIG_PATH = "/opt/airflow/scripts/scraping_config.json"

default_args = {
    "owner": "aymeric",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with open(SCRAPING_CONFIG_PATH, encoding="utf-8") as f:
    VILLES = json.load(f)["villes"]

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

    # Fusionne les CSV d'annonces (Century21, Orpi, SeLoger, PAP, ParuVendu,
    # Vizzit) d'une ville, sans toucher aux annonces des autres villes déjà
    # présentes dans le fichier combiné (ORA-153).
    # Écrit : backend/data/base_de_donnees_immo_complet.csv
    steps_fusion = [
        BashOperator(
            task_id=f"data_fusion_{slug}",
            bash_command=f"cd {SCRIPTS} && python data_fusion.py --ville {slug}",
        )
        for slug in VILLES
    ]

    # Calcule les features de distance (BallTree) + géocodage + quartiers,
    # sur toutes les villes du fichier combiné. Doit attendre que CHAQUE
    # fusion par ville soit à jour : une ville non encore fusionnée ce run-ci
    # garde simplement ses données du run précédent (pas de blocage).
    # Lit : base_de_donnees_immo_complet.csv + cavaliers_all.csv (le plus
    # récent sur disque, produit par les DAGs cavaliers — pas forcément du
    # même jour)
    # Écrit : master_immo_final.csv
    step_features = BashOperator(
        task_id="clean_immo",
        bash_command=f"cd {SCRIPTS} && python clean_immo.py",
    )

    # Entraîne XGBoost sur le master (toutes villes confondues, cf. docstring)
    # Écrit : backend/models/price_predictor.pkl
    step_train = BashOperator(
        task_id="train_model",
        bash_command=f"cd {SCRIPTS} && python train_model.py",
    )

    # Régénère la carte statique de chaque ville à partir des données/modèle
    # à jour, pour éviter toute péremption silencieuse (ORA-54).
    # Écrit : frontend/public/data/map_pings_<ville>_calques.html + map_metadata_<ville>.json
    steps_generate_map = [
        BashOperator(
            task_id=f"generate_map_{slug}",
            bash_command=f"cd {SCRIPTS} && python generate_map.py --ville {slug}",
        )
        for slug in VILLES
    ]

    steps_fusion >> step_features >> step_train >> steps_generate_map
