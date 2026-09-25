import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from complete_data_extraction import (
    advert_id,
    coordinates_from_api_response,
    extract_coordinates_from_html,
    fetch_api_coordinates,
    get_gps_from_url,
    process_row,
    resolve_paths,
)


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


class ApiCoordinatesTest(unittest.TestCase):
    PAYLOAD = {"advertsCoordinates": [
        {"advertId": "Aaa", "latitude": 50.63, "longitude": 3.06, "countByLocation": 1},
        {"advertId": "Abb", "latitude": None, "longitude": 3.07},
        {"advertId": "Acc", "latitude": 50.64, "longitude": 3.08},
    ]}

    def test_advert_id_is_the_last_url_segment(self):
        self.assertEqual(advert_id("https://www.vizzit.fr/fr/property/appartement/lille/Aaa/"), "Aaa")

    def test_response_parsing_skips_points_without_coordinates(self):
        self.assertEqual(coordinates_from_api_response(self.PAYLOAD), {"Aaa": (50.63, 3.06), "Acc": (50.64, 3.08)})
        self.assertEqual(coordinates_from_api_response({}), {})

    def test_process_row_prefers_api_then_falls_back_to_the_listing_page(self):
        api = {"Aaa": (50.63, 3.06)}
        with patch("complete_data_extraction.get_gps_from_url", return_value=(50.1, 3.1)) as fiche:
            self.assertEqual(process_row((0, {"Lien": "https://x/lille/Aaa"}), api), (0, 50.63, 3.06))
            fiche.assert_not_called()
            self.assertEqual(process_row((1, {"Lien": "https://x/lille/Zzz"}), api), (1, 50.1, 3.1))
            self.assertEqual(process_row((2, {"Lien": "https://x/lille/Zzz"})), (2, 50.1, 3.1))  # API indisponible

    def _session(self, page_status=200, page_html='id="__AjaxAntiForgeryForm" x><input name="__RequestVerificationToken" type="hidden" value="TOK">', post_status=200):
        session = MagicMock()
        session.get.return_value = SimpleNamespace(status_code=page_status, text=page_html)
        session.post.return_value = SimpleNamespace(status_code=post_status, json=lambda: self.PAYLOAD)
        return session

    def test_fetch_sends_the_antiforgery_token_and_returns_positions(self):
        session = self._session()
        with patch("complete_data_extraction.requests.Session", return_value=session):
            result = fetch_api_coordinates("https://www.vizzit.fr/fr/properties/1?searchQuery=lg-fr-type-rentals&x=1")

        self.assertEqual(set(result), {"Aaa", "Acc"})
        self.assertEqual(session.post.call_args.kwargs["headers"]["RequestVerificationToken"], "TOK")
        self.assertEqual(session.post.call_args.kwargs["json"]["searchQuery"], "lg-fr-type-rentals")

    def test_fetch_returns_empty_when_token_missing_or_api_fails(self):
        for session in (self._session(page_html="<html></html>"), self._session(post_status=400)):
            with patch("complete_data_extraction.requests.Session", return_value=session):
                self.assertEqual(fetch_api_coordinates("https://www.vizzit.fr/fr/properties/1?searchQuery=q"), {})

    def test_fetch_returns_empty_on_network_error(self):
        import requests
        with patch("complete_data_extraction.requests.Session", side_effect=requests.ConnectionError("down")):
            self.assertEqual(fetch_api_coordinates("https://www.vizzit.fr/fr/properties/1?searchQuery=q"), {})


if __name__ == "__main__":
    unittest.main()
