"""
DAG : Analyse hebdomadaire des prix immobiliers
Génère des rapports et statistiques sur l'évolution du marché
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
import json
from pathlib import Path

default_args = {
    'owner': 'oracle',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'analyze_prices_weekly',
    default_args=default_args,
    description='Analyse hebdomadaire des prix immobiliers',
    schedule_interval='0 9 * * 1',  # Tous les lundis à 9h
    catchup=False,
    tags=['oracle', 'analysis', 'weekly']
)

def load_immo_data():
    """Charger les données immobilières"""
    df = pd.read_csv('/opt/airflow/backend/data/master_immo_final.csv')
    print(f"📊 {len(df)} offres immobilières chargées")
    return df.to_json()

def calculate_stats(**context):
    """Calculer les statistiques par arrondissement"""
    df_json = context['task_instance'].xcom_pull(task_ids='load_data')
    df = pd.read_json(df_json)
    
    # Stats par arrondissement
    stats_by_cp = df.groupby('code_postal').agg({
        'prix': ['mean', 'median', 'min', 'max', 'count'],
        'prix_m2': ['mean', 'median']
    }).round(2)
    
    print("\n📈 STATISTIQUES PAR ARRONDISSEMENT")
    print(stats_by_cp)
    
    # Sauvegarder
    output_path = '/opt/airflow/backend/data/weekly_stats.json'
    stats_dict = stats_by_cp.to_dict()
    
    with open(output_path, 'w') as f:
        json.dump({
            'date': datetime.now().isoformat(),
            'stats': stats_dict
        }, f, indent=2)
    
    print(f"✅ Stats sauvegardées : {output_path}")
    return output_path

def detect_trends(**context):
    """Détecter les tendances de prix"""
    df_json = context['task_instance'].xcom_pull(task_ids='load_data')
    df = pd.read_json(df_json)
    
    # Comparer avec la semaine dernière (si disponible)
    trends = {
        'total_offres': len(df),
        'prix_moyen_global': round(df['prix'].mean(), 2),
        'prix_m2_moyen_global': round(df['prix_m2'].mean(), 2),
        'arrondissement_plus_cher': df.groupby('code_postal')['prix_m2'].mean().idxmax(),
        'arrondissement_moins_cher': df.groupby('code_postal')['prix_m2'].mean().idxmin()
    }
    
    print("\n🔍 TENDANCES DÉTECTÉES")
    for key, value in trends.items():
        print(f"  {key}: {value}")
    
    return trends

def generate_report(**context):
    """Générer un rapport récapitulatif"""
    stats_path = context['task_instance'].xcom_pull(task_ids='calculate_stats')
    trends = context['task_instance'].xcom_pull(task_ids='detect_trends')
    
    report = f"""
    ═══════════════════════════════════════════
    📊 RAPPORT HEBDOMADAIRE - Oracle Loyers
    ═══════════════════════════════════════════
    
    Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}
    
    📈 STATISTIQUES GLOBALES
    ───────────────────────────────────────────
    • Total d'offres : {trends['total_offres']}
    • Prix moyen : {trends['prix_moyen_global']}€
    • Prix/m² moyen : {trends['prix_m2_moyen_global']}€
    
    🏆 CLASSEMENT
    ───────────────────────────────────────────
    • Arrondissement le plus cher : {trends['arrondissement_plus_cher']}
    • Arrondissement le moins cher : {trends['arrondissement_moins_cher']}
    
    📁 Détails complets : {stats_path}
    
    ═══════════════════════════════════════════
    """
    
    print(report)
    
    # Sauvegarder le rapport
    report_path = '/opt/airflow/backend/data/weekly_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Rapport sauvegardé : {report_path}")
    return report_path

# Tâches
task_load = PythonOperator(
    task_id='load_data',
    python_callable=load_immo_data,
    dag=dag
)

task_stats = PythonOperator(
    task_id='calculate_stats',
    python_callable=calculate_stats,
    dag=dag
)

task_trends = PythonOperator(
    task_id='detect_trends',
    python_callable=detect_trends,
    dag=dag
)

task_report = PythonOperator(
    task_id='generate_report',
    python_callable=generate_report,
    dag=dag
)

# Flux
task_load >> [task_stats, task_trends] >> task_report
