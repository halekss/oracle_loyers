"""
DAG : Enrichissement quotidien des cavaliers avec codes postaux
Utilise l'API Data Gouv pour géocoder les codes postaux
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
import requests
import io
import time
import os

default_args = {
    'owner': 'oracle',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'enrich_cavaliers_daily',
    default_args=default_args,
    description='Enrichissement quotidien des cavaliers avec codes postaux',
    schedule_interval='0 3 * * *',  # Tous les jours à 3h du matin
    catchup=False,
    tags=['oracle', 'cavaliers', 'geocoding']
)

def check_cavaliers_file():
    """Vérifier que le fichier cavaliers existe"""
    file_path = '/opt/airflow/backend/data/cavaliers_lyon.csv'
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier cavaliers introuvable : {file_path}")
    
    df = pd.read_csv(file_path)
    
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        raise ValueError("Colonnes latitude/longitude manquantes")
    
    print(f"✅ Fichier cavaliers OK : {len(df)} lignes")
    return len(df)

def enrich_with_api(**context):
    """Enrichir les cavaliers avec l'API Data Gouv"""
    file_path = '/opt/airflow/backend/data/cavaliers_lyon.csv'
    api_url = "https://api-adresse.data.gouv.fr/reverse/csv/"
    
    # Charger les données
    df = pd.read_csv(file_path)
    print(f"📊 Traitement de {len(df)} cavaliers...")
    
    # Préparer le CSV pour l'API
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_content = csv_buffer.getvalue()
    
    files = {'data': ('cavaliers.csv', csv_content, 'text/csv')}
    data = {
        'columns': ['latitude', 'longitude'],
        'result_columns': ['result_postcode']
    }
    
    # Appel API
    print("🔄 Appel API Data Gouv...")
    start_time = time.time()
    
    try:
        response = requests.post(api_url, files=files, data=data, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Erreur API : {response.status_code}")
        
        duration = time.time() - start_time
        print(f"✅ Réponse API reçue en {duration:.2f}s")
        
        # Parser la réponse
        df_enriched = pd.read_csv(io.StringIO(response.text))
        
        # Nettoyer les codes postaux
        if 'result_postcode' in df_enriched.columns:
            df_enriched['code_postal'] = df_enriched['result_postcode']
            df_enriched = df_enriched.drop(columns=['result_postcode'])
        
        df_enriched['code_postal'] = df_enriched['code_postal'].fillna(0).astype(str).apply(lambda x: x.split('.')[0])
        
        # Sauvegarder temporairement
        temp_file = '/opt/airflow/backend/data/temp_cavaliers_update.csv'
        df_enriched.to_csv(temp_file, index=False)
        
        # Remplacer l'original
        os.replace(temp_file, file_path)
        
        # Stats
        stats = df_enriched['code_postal'].value_counts().sort_index()
        total_found = len(df_enriched[df_enriched['code_postal'] != '0'])
        
        print("\n" + "="*60)
        print("📊 STATISTIQUES D'ENRICHISSEMENT")
        print("="*60)
        print(f"✅ {total_found} cavaliers enrichis sur {len(df_enriched)}")
        print("\nRépartition par code postal :")
        for cp, count in stats.head(10).items():
            label = cp if cp != '0' else "HORS ZONE"
            print(f"  {label}: {count}")
        
        return {
            'total': len(df_enriched),
            'enriched': total_found,
            'success_rate': round((total_found / len(df_enriched)) * 100, 2)
        }
        
    except Exception as e:
        print(f"❌ Erreur lors de l'enrichissement : {e}")
        raise

def verify_enrichment(**context):
    """Vérifier que l'enrichissement a fonctionné"""
    stats = context['task_instance'].xcom_pull(task_ids='enrich_api')
    
    if not stats or stats['enriched'] == 0:
        raise ValueError("Aucun cavalier enrichi !")
    
    print(f"✅ Vérification OK : {stats['enriched']} cavaliers enrichis ({stats['success_rate']}%)")
    return True

def generate_report(**context):
    """Générer un rapport d'enrichissement"""
    stats = context['task_instance'].xcom_pull(task_ids='enrich_api')
    
    report = f"""
    ═══════════════════════════════════════════
    📍 RAPPORT ENRICHISSEMENT CAVALIERS
    ═══════════════════════════════════════════
    
    Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}
    
    📊 RÉSULTATS
    ───────────────────────────────────────────
    • Total cavaliers : {stats['total']}
    • Enrichis avec succès : {stats['enriched']}
    • Taux de succès : {stats['success_rate']}%
    • Non localisés : {stats['total'] - stats['enriched']}
    
    ✅ Le fichier cavaliers_lyon.csv a été mis à jour
    
    ═══════════════════════════════════════════
    """
    
    print(report)
    
    # Sauvegarder le rapport
    report_path = '/opt/airflow/backend/data/cavaliers_enrichment_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📄 Rapport sauvegardé : {report_path}")
    return report_path

# Tâches
task_check = PythonOperator(
    task_id='check_file',
    python_callable=check_cavaliers_file,
    dag=dag
)

task_enrich = PythonOperator(
    task_id='enrich_api',
    python_callable=enrich_with_api,
    dag=dag
)

task_verify = PythonOperator(
    task_id='verify_enrichment',
    python_callable=verify_enrichment,
    dag=dag
)

task_report = PythonOperator(
    task_id='generate_report',
    python_callable=generate_report,
    dag=dag
)

# Flux
task_check >> task_enrich >> task_verify >> task_report
