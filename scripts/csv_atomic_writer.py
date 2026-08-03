import csv
import os
from contextlib import contextmanager


@contextmanager
def atomic_csv_writer(output_path, header):
    """
    Écrit dans un fichier temporaire à côté de `output_path` et ne remplace
    ce dernier (os.replace atomique) qu'à la fin d'un run réussi. Si une
    exception non gérée survient pendant le scraping, le fichier temporaire
    est supprimé et le CSV précédent reste intact (pas de perte de données).
    """
    tmp_path = f"{output_path}.tmp"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        with open(tmp_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            yield writer
        os.replace(tmp_path, output_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
