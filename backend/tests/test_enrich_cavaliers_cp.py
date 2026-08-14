import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from enrich_cavaliers_cp import resolve_target_file


class ResolveTargetFileTest(unittest.TestCase):
    """ORA-153 : avant cette correction, le script ciblait en dur
    cavaliers_lyon.csv — Lille n'était jamais enrichi en code postal tant que
    ce nom de fichier restait hardcodé."""

    def test_targets_the_csv_of_the_given_ville(self):
        self.assertTrue(resolve_target_file("lyon").endswith(os.path.join("data", "cavaliers_lyon.csv")))
        self.assertTrue(resolve_target_file("lille").endswith(os.path.join("data", "cavaliers_lille.csv")))


if __name__ == "__main__":
    unittest.main()
