from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# On ajoute le chemin du backend pour qu'Airflow trouve le script
# Dans le container, le volume sera monté dans /opt/airflow/backend
sys.path.append('/opt/airflow/backend')

def execute_generation():
    from generate_map import main
    main()

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 1,
}

with DAG(
    'oracle_map_refresh',
    default_args=default_args,
    description='Génération quotidienne de la carte Lyon',
    schedule_interval='@daily',
    catchup=False,
) as dag:

    run_script = PythonOperator(
        task_id='generate_folium_map',
        python_callable=execute_generation,
    )