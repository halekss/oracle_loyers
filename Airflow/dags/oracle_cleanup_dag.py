"""
L'Oracle des Loyers — DAG Cleanup (ORA-134 bis)

Vérification HTTP asynchrone quotidienne des annonces à statut incertain
(`a_verifier`, ou `active` périmées) — tier 2 du nettoyage non-destructif.
Ne supprime jamais de ligne, met uniquement à jour la colonne `statut`
(active/a_verifier/inactive) de master_immo_final.csv puis annonces.db.

Volontairement séparé de oracle_annonces_pipeline (hebdomadaire, lundi 22h) :
cadence différente (quotidienne vs hebdomadaire) et ce DAG ne doit pas être
bloqué par la durée du pipeline ML complet (fusion + features + entraînement).
Exécuté à 3h du matin (Europe/Paris), en dehors du créneau du pipeline
principal, pour éviter tout chevauchement d'écriture sur master_immo_final.csv.

Ne couvre que le tier HTTP rapide (aiohttp) : le tier navigateur headless
(Selenium, pour les 403/CAPTCHA constatés sur SeLoger) reste un script manuel
hors Airflow (scripts/recheck_dead_annonces.py, scripts/.venv) — décision
délibérée pour ne pas alourdir l'image Airflow avec Chrome/Selenium,
cohérente avec le choix déjà fait pour le pipeline principal.
"""

from datetime import timedelta
import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

BACKEND_SCRIPTS = "/opt/airflow/backend/scripts"

default_args = {
    "owner": "aymeric",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="oracle_cleanup_pipeline",
    default_args=default_args,
    description="Vérification HTTP asynchrone des annonces à statut incertain — cadence quotidienne",
    schedule="0 3 * * *",
    start_date=pendulum.datetime(2026, 8, 8, tz="Europe/Paris"),
    catchup=False,
    tags=["oracle", "etl", "immo", "cleanup"],
) as dag:

    step_verify = BashOperator(
        task_id="verify_annonces_async",
        bash_command=f"cd {BACKEND_SCRIPTS} && python verify_annonces_async.py --concurrency 5 --ttl-days 15",
    )
