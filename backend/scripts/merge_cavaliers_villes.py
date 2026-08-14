"""
L'Oracle des Loyers — Fusion des cavaliers par ville

Concatène les cavaliers_<slug>.csv de chaque ville déclarée dans
scraping_config.json en un seul cavaliers_all.csv, le fichier réellement
consommé par clean_immo.py (calcul des features de distance BallTree).

Avant ORA-153, rien dans le pipeline ne produisait cavaliers_all.csv
automatiquement : les DAGs cavaliers ne géraient que Lyon, et le fichier
combiné utilisé par clean_immo.py était recréé à la main lors des sessions
multi-ville. Ce script est le point de jonction entre les DAGs cavaliers
désormais scindés par ville et le pipeline annonces, qui reste pour
l'instant un run global multi-villes (cf. ORA-154 pour le découpage du
modèle, préalable à un découpage complet par ville du reste de la chaîne).
"""
import os

import pandas as pd

from data_fusion import load_declared_villes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'cavaliers_all.csv')


def merge_all_villes(data_dir=DATA_DIR, output_file=OUTPUT_FILE):
    villes = load_declared_villes()
    dfs = []
    for slug in villes:
        path = os.path.join(data_dir, f'cavaliers_{slug}.csv')
        if os.path.exists(path):
            df = pd.read_csv(path)
            dfs.append(df)
            print(f"📂 {slug} : {len(df)} lignes")
        else:
            print(f"⚠️  {path} introuvable, ignoré.")

    if not dfs:
        print("❌ Aucun fichier cavaliers_*.csv trouvé, cavaliers_all.csv non régénéré.")
        return

    merged = pd.concat(dfs, ignore_index=True)
    merged.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"🎉 {output_file} régénéré : {len(merged)} lignes ({len(dfs)} ville(s)).")


if __name__ == "__main__":
    merge_all_villes()
