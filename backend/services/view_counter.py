import json
import os
import tempfile
from threading import Lock


class ViewCounterService:
    """Compteur de vues par annonce, persisté dans un fichier JSON avec écriture atomique."""

    def __init__(self, storage_path):
        self.storage_path = storage_path
        self._lock = Lock()

    def _read(self):
        if not os.path.exists(self.storage_path):
            return {}
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, data):
        directory = os.path.dirname(self.storage_path) or '.'
        os.makedirs(directory, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=directory, prefix='.listing_views_', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            os.replace(temp_path, self.storage_path)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def get_count(self, listing_id):
        return int(self._read().get(str(listing_id), 0))

    def increment(self, listing_id):
        with self._lock:
            data = self._read()
            key = str(listing_id)
            data[key] = int(data.get(key, 0)) + 1
            self._write(data)
            return data[key]

    def get_all(self):
        return {key: int(value) for key, value in self._read().items()}
