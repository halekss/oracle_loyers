import pandas as pd
import os
import io
import time

from http_retry import request_with_retry

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
TARGET_FILE = os.path.join(DATA_DIR, 'cavaliers_lyon.csv')

# API de géocodage inversé (Batch)
API_URL = "https://api-adresse.data.gouv.fr/reverse/csv/"

def enrich_and_overwrite():
    print("🚀 Démarrage de l'enrichissement (Mode : Écrasement du fichier original)...")

    # 1. Vérification
    if not os.path.exists(TARGET_FILE):
        print(f"❌ Erreur : Fichier introuvable : {TARGET_FILE}")
        return

    try:
        df = pd.read_csv(TARGET_FILE)
        print(f"📂 Fichier chargé : {len(df)} lignes.")
    except Exception as e:
        print(f"❌ Erreur lecture CSV : {e}")
        return

    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        print("❌ Erreur : Colonnes 'latitude'/'longitude' manquantes.")
        return

    # 2. Préparation du batch
    print("📡 Envoi à l'API Data Gouv...")
    
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_content = csv_buffer.getvalue()

    files = {'data': ('cavaliers.csv', csv_content, 'text/csv')}
    data = {
        'columns': ['latitude', 'longitude'],
        'result_columns': ['result_postcode']
    }

    try:
        start_time = time.time()
        # Timeout généreux pour le traitement batch, avec retry/backoff sur erreur transitoire
        response = request_with_retry("POST", API_URL, files=files, data=data, timeout=60)

        if response is None:
            print("❌ Échec définitif de l'appel à l'API Data Gouv après plusieurs tentatives.")
            print("⚠️ Le fichier original n'a pas été touché.")
            return

        if response.status_code == 200:
            duration = time.time() - start_time
            print(f"✅ Réponse reçue en {duration:.2f} s.")
            
            # Lecture du résultat renvoyé par l'API
            df_enriched = pd.read_csv(io.StringIO(response.text))
            
            # Récupération et nettoyage de la colonne code postal
            if 'result_postcode' in df_enriched.columns:
                df_enriched['code_postal'] = df_enriched['result_postcode']
                df_enriched = df_enriched.drop(columns=['result_postcode']) # On nettoie la colonne technique
            
            # Formatage propre (pas de .0, gestion des vides)
            df_enriched['code_postal'] = df_enriched['code_postal'].fillna(0).astype(str).apply(lambda x: x.split('.')[0])
            
            # 3. ÉCRASEMENT SÉCURISÉ
            # On sauvegarde d'abord dans un fichier temporaire
            temp_file = os.path.join(DATA_DIR, 'temp_cavaliers_update.csv')
            df_enriched.to_csv(temp_file, index=False)
            
            # Si la sauvegarde a marché, on remplace l'original
            os.replace(temp_file, TARGET_FILE)
            
            # --- BILAN ---
            stats = df_enriched['code_postal'].value_counts().sort_index()
            total_trouves = len(df_enriched[df_enriched['code_postal'] != '0'])
            
            print("\n" + "="*60)
            print("🏆 MISE À JOUR TERMINÉE")
            print("="*60)
            print(f"✅ Le fichier {TARGET_FILE} a été mis à jour.")
            print(f"📍 {total_trouves} établissements localisés sur {len(df_enriched)}.")
            print("-" * 60)
            print(f"{'CODE POSTAL':<15} | {'NOMBRE'}")
            print("-" * 60)
            for cp, count in stats.items():
                label = cp if cp != '0' else "HORS ZONE/INCONNU"
                print(f"{label:<15} | {count}")
            print("-" * 60)

        else:
            print(f"❌ Erreur API ({response.status_code}) : Pas de modification effectuée.")

    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        print("⚠️ Le fichier original n'a pas été touché.")

if __name__ == "__main__":
    enrich_and_overwrite()