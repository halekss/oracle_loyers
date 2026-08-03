import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from csv_atomic_writer import atomic_csv_writer


class AtomicCsvWriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.output_path = os.path.join(self.tmp_dir.name, "annonces.csv")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _read_rows(self, path):
        with open(path, newline="", encoding="utf-8-sig") as f:
            return list(csv.reader(f))

    def test_writes_header_and_rows_then_replaces_output_on_success(self):
        with atomic_csv_writer(self.output_path, ["Titre", "Prix"]) as writer:
            writer.writerow(["Studio Gerland", "700"])
            writer.writerow(["T2 Croix-Rousse", "850"])

        rows = self._read_rows(self.output_path)
        self.assertEqual(rows, [["Titre", "Prix"], ["Studio Gerland", "700"], ["T2 Croix-Rousse", "850"]])
        self.assertFalse(os.path.exists(f"{self.output_path}.tmp"))

    def test_interruption_during_scraping_preserves_previous_csv(self):
        with atomic_csv_writer(self.output_path, ["Titre", "Prix"]) as writer:
            writer.writerow(["Ancienne annonce valide", "600"])

        with self.assertRaises(RuntimeError):
            with atomic_csv_writer(self.output_path, ["Titre", "Prix"]) as writer:
                writer.writerow(["Nouvelle annonce partielle", "999"])
                raise RuntimeError("Le driver Selenium a planté en cours de scraping")

        rows = self._read_rows(self.output_path)
        self.assertEqual(rows, [["Titre", "Prix"], ["Ancienne annonce valide", "600"]])
        self.assertFalse(os.path.exists(f"{self.output_path}.tmp"))


if __name__ == "__main__":
    unittest.main()
