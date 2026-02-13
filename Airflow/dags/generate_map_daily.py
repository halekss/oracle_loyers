"""
DAG : Génération quotidienne de la carte Oracle Loyers
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import sys
import os

sys.path.insert(0, '/opt/airflow/backend')

default_args = {
    'owner': 'oracle',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'generate_map_daily',
    default_args=default_args,
    description='Génération quotidienne de la carte',
    schedule_interval='0 4 * * *',  # 4h du matin (après enrichissement cavaliers)
    catchup=False,
    tags=['oracle', 'map', 'daily']
)

def check_data_files():
    """Vérifier que les fichiers existent"""
    required_files = [
        '/opt/airflow/backend/data/master_immo_final.csv',
        '/opt/airflow/backend/data/cavaliers_lyon.csv',
        '/opt/airflow/backend/data/metro_lyon.json'
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier manquant : {file_path}")
    
    print("✅ Tous les fichiers présents")
    return True

def generate_map():
    """Générer la carte"""
    import subprocess
    
    result = subprocess.run(
        ['python3', '/opt/airflow/backend/scripts/generate_map.py'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Erreur : {result.stderr}")
    
    print(result.stdout)
    print("🗺️ Carte générée")
    return True

def verify_output():
    """Vérifier la carte générée"""
    output_file = '/opt/airflow/frontend/public/data/map_pings_lyon_calques.html'
    
    if not os.path.exists(output_file):
        raise FileNotFoundError(f"Carte non générée : {output_file}")
    
    file_size = os.path.getsize(output_file)
    if file_size < 1000:
        raise ValueError(f"Fichier trop petit : {file_size} bytes")
    
    print(f"✅ Carte générée : {file_size} bytes")
    return True

task_check = PythonOperator(task_id='check_data_files', python_callable=check_data_files, dag=dag)
task_generate = PythonOperator(task_id='generate_map', python_callable=generate_map, dag=dag)
task_verify = PythonOperator(task_id='verify_output', python_callable=verify_output, dag=dag)
task_notify = BashOperator(task_id='notify_success', bash_command='echo "🎉 Carte à jour"', dag=dag)

task_check >> task_generate >> task_verify >> task_notify
