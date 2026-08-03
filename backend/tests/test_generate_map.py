import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import generate_map


class WriteMapMetadataTest(unittest.TestCase):
    """Vérifie le contrôle de fraîcheur de la carte statique (ORA-54) :
    `write_map_metadata` doit écrire un JSON avec un timestamp ISO valide,
    sans nécessiter une régénération complète de la carte (pas de données lourdes)."""

    def test_writes_metadata_file_with_valid_iso_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            metadata_path = os.path.join(tmp_dir, "map_metadata.json")

            before = datetime.now(timezone.utc)
            result = generate_map.write_map_metadata(metadata_path)
            after = datetime.now(timezone.utc)

            self.assertTrue(os.path.exists(metadata_path))

            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)

            self.assertIn("generated_at", metadata)
            self.assertEqual(metadata, result)

            # Le timestamp doit être un ISO 8601 valide et parseable, situé
            # entre le début et la fin de l'appel (pas figé/codé en dur).
            generated_at = datetime.fromisoformat(metadata["generated_at"])
            self.assertLessEqual(before, generated_at)
            self.assertLessEqual(generated_at, after)

    def test_includes_map_file_and_extra_fields_when_provided(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            metadata_path = os.path.join(tmp_dir, "map_metadata.json")
            output_html = os.path.join(tmp_dir, "map_pings_lyon_calques.html")

            result = generate_map.write_map_metadata(
                metadata_path,
                output_html=output_html,
                extra={"rows_immo": 42},
            )

            self.assertEqual(result["map_file"], "map_pings_lyon_calques.html")
            self.assertEqual(result["rows_immo"], 42)

    def test_creates_parent_directory_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            nested_dir = os.path.join(tmp_dir, "data")
            metadata_path = os.path.join(nested_dir, "map_metadata.json")

            self.assertFalse(os.path.exists(nested_dir))
            generate_map.write_map_metadata(metadata_path)
            self.assertTrue(os.path.exists(metadata_path))

    def test_overwrites_existing_metadata_with_fresh_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            metadata_path = os.path.join(tmp_dir, "map_metadata.json")

            first = generate_map.write_map_metadata(metadata_path)
            second = generate_map.write_map_metadata(metadata_path)

            # Un deuxième appel doit rafraîchir la date de génération (contrôle
            # de fraîcheur), pas conserver l'ancienne valeur silencieusement.
            self.assertGreaterEqual(second["generated_at"], first["generated_at"])


if __name__ == "__main__":
    unittest.main()
