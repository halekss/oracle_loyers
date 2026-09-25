import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from types import SimpleNamespace
from unittest.mock import patch

from complete_data_extraction import extract_coordinates_from_html, get_gps_from_url, resolve_paths


class ExtractCoordinatesFromHtmlTest(unittest.TestCase):
    def test_extracts_from_window_advert_coordinates(self):
        html = """
        <script>
            window.advert = {
                coordinates: {
                    latitude: 50.63381,
                    longitude: 3.06689,
                    precise: false
                },
                cityId: 123
            };
        </script>
        """

        lat, lon = extract_coordinates_from_html(html)

        self.assertEqual(lat, 50.63381)
        self.assertEqual(lon, 3.06689)

    def test_ignores_the_country_center_decoy(self):
        # "CurrentCountryCoordinates" est le centre géographique de la
        # France (~46.6, ~1.9), pas la position de l'annonce — présent sur
        # chaque fiche Vizzit, ne doit jamais être confondu avec les vraies
        # coordonnées de l'annonce.
        html = """
        <script>window.currentCountryLatitude = '46,603354';</script>
        <script>"CurrentCountryCoordinates":{"Latitude":46.603354,"Longitude":1.8883335}</script>
        <script>
            window.advert = {
                coordinates: {
                    latitude: 50.63381,
                    longitude: 3.06689,
                    precise: false
                }
            };
        </script>
        """

        lat, lon = extract_coordinates_from_html(html)

        self.assertEqual(lat, 50.63381)
        self.assertEqual(lon, 3.06689)

    def test_falls_back_to_meta_tags_when_advert_coordinates_absent(self):
        html = """
        <meta property="og:latitude" content="45.764" />
        <meta property="og:longitude" content="4.8357" />
        """

        lat, lon = extract_coordinates_from_html(html)

        self.assertEqual(lat, 45.764)
        self.assertEqual(lon, 4.8357)

    def test_returns_none_none_when_nothing_found(self):
        self.assertEqual(extract_coordinates_from_html("<html><body>Rien ici</body></html>"), (None, None))

    def test_works_for_lille_coordinates_not_just_lyon_prefixes(self):
        # Régression : les anciennes stratégies étaient codées en dur sur
        # des préfixes lyonnais (lat "45.", lon "4.") et ne matchaient donc
        # jamais les coordonnées Lille (lat "50.", lon "3.").
        html = "window.advert = { coordinates: { latitude: 50.6243, longitude: 3.0466 } };"

        lat, lon = extract_coordinates_from_html(html)

        self.assertEqual(lat, 50.6243)
        self.assertEqual(lon, 3.0466)


class ResolvePathsTest(unittest.TestCase):
    def test_builds_filenames_from_ville_slug(self):
        input_file, output_file = resolve_paths("lille")

        self.assertTrue(input_file.endswith("annonces_lille_vizzit.csv"))
        self.assertTrue(output_file.endswith("annonces_lille_vizzit_geoloc_complete.csv"))

    def test_defaults_still_produce_lyon_filenames(self):
        input_file, output_file = resolve_paths("lyon")

        self.assertTrue(input_file.endswith("annonces_lyon_vizzit.csv"))
        self.assertTrue(output_file.endswith("annonces_lyon_vizzit_geoloc_complete.csv"))


class GetGpsFromUrlTest(unittest.TestCase):
    HTML = "window.advert = { coordinates: { latitude: 50.63718, longitude: 3.07383 } }"

    def _get(self, status, final_url):
        response = SimpleNamespace(status_code=status, url=final_url, text=self.HTML)
        with patch("complete_data_extraction.request_with_retry", return_value=response):
            return get_gps_from_url("https://www.vizzit.fr/fr/property/appartement/lille/Axxx")

    def test_reads_coordinates_even_when_vizzit_answers_http_410(self):
        # Régression réelle : les fiches Vizzit en 410 contiennent leurs coordonnées.
        self.assertEqual(self._get(410, "https://www.vizzit.fr/fr/property/appartement/lille/Axxx"), (50.63718, 3.07383))

    def test_ignores_a_listing_redirected_to_another_site(self):
        self.assertEqual(self._get(200, "https://www.leboncoin.fr:443/ad/locations/1"), (None, None))


if __name__ == "__main__":
    unittest.main()
