import json
import os
import unittest

GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "lille_quartiers.geojson")


class LilleQuartiersGeojsonTest(unittest.TestCase):
    """ORA-157 : contours réels (polygones), pas des bbox à 4 points."""

    def setUp(self):
        with open(GEOJSON_PATH, encoding="utf-8") as f:
            self.geojson = json.load(f)

    def test_has_at_least_ten_real_polygons(self):
        features = self.geojson["features"]
        self.assertGreaterEqual(len(features), 10)
        for feature in features:
            geometry = feature["geometry"]
            self.assertIn(geometry["type"], ("Polygon", "MultiPolygon"))
            ring = geometry["coordinates"][0] if geometry["type"] == "Polygon" else geometry["coordinates"][0][0]
            self.assertGreater(len(ring), 5, feature["properties"]["nom"])

    def test_documents_source_and_licence(self):
        self.assertIn("ODbL 1.0", self.geojson["properties"]["licence"])


if __name__ == "__main__":
    unittest.main()
