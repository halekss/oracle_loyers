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


class SanitizeListingUrlTest(unittest.TestCase):
    def test_accepts_http_url(self):
        self.assertEqual(
            generate_map.sanitize_listing_url("http://example.com/annonce/1"),
            "http://example.com/annonce/1",
        )

    def test_accepts_https_url_and_strips_whitespace(self):
        self.assertEqual(
            generate_map.sanitize_listing_url("  https://example.com/annonce/2  "),
            "https://example.com/annonce/2",
        )

    def test_rejects_javascript_scheme(self):
        self.assertIsNone(generate_map.sanitize_listing_url("javascript:alert(1)"))

    def test_rejects_non_string_values(self):
        self.assertIsNone(generate_map.sanitize_listing_url(float("nan")))
        self.assertIsNone(generate_map.sanitize_listing_url(None))

    def test_rejects_empty_string(self):
        self.assertIsNone(generate_map.sanitize_listing_url("   "))


class BuildImmoPopupHtmlTest(unittest.TestCase):
    def test_includes_price_type_and_quartier(self):
        html_out = generate_map.build_immo_popup_html(
            type_local="T2", prix="750", quartier="Perrache", listing_url="https://example.com/annonce/6",
        )

        self.assertIn("T2", html_out)
        self.assertIn("750", html_out)
        self.assertIn("Perrache", html_out)

    def test_renders_link_when_url_present(self):
        html_out = generate_map.build_immo_popup_html(
            type_local="T2", prix="750", quartier="Perrache", listing_url="https://example.com/annonce/7",
        )

        self.assertIn("https://example.com/annonce/7", html_out)
        self.assertIn("<a ", html_out)

    def test_never_renders_an_image_tag(self):
        # Décision légale ORA-94 (LEGAL_DECISIONS.md) : aucune photo scrapée ne
        # doit jamais être reproduite, même si les données en fournissaient une.
        html_out = generate_map.build_immo_popup_html(
            type_local="T2", prix="750", quartier="Perrache", listing_url="https://example.com/annonce/7",
        )

        self.assertNotIn("<img", html_out)

    def test_omits_link_when_no_url(self):
        html_out = generate_map.build_immo_popup_html(
            type_local="T2", prix="750", quartier="Perrache", listing_url=None,
        )

        self.assertNotIn("<a ", html_out)

    def test_escapes_hostile_quartier_value(self):
        html_out = generate_map.build_immo_popup_html(
            type_local="T2", prix="750", quartier="<script>alert(1)</script>", listing_url=None,
        )

        self.assertNotIn("<script>alert(1)</script>", html_out)


class BuildMarkerClickScriptTest(unittest.TestCase):
    def test_returns_empty_string_when_no_redirect_url(self):
        script = generate_map.build_marker_click_script("circle_marker_abc", redirect_url=None)

        self.assertEqual(script, "")

    def test_binds_click_handler_and_opens_redirect_url(self):
        script = generate_map.build_marker_click_script(
            "circle_marker_abc", redirect_url="https://example.com/annonce/8",
        )

        self.assertIn("circle_marker_abc.on('click'", script)
        self.assertIn("window.open(", script)
        self.assertIn('"https://example.com/annonce/8"', script)

    def test_escapes_redirect_url_against_js_injection(self):
        hostile_url = 'https://example.com/");alert(document.cookie);//'

        script = generate_map.build_marker_click_script("circle_marker_abc", redirect_url=hostile_url)

        self.assertNotIn('window.open("https://example.com/");alert', script)
        self.assertIn('\\"', script)

    def test_rejects_non_http_redirect_url(self):
        script = generate_map.build_marker_click_script("circle_marker_abc", redirect_url="javascript:alert(1)")

        self.assertEqual(script, "")


class BuildBridgeMessageScriptTest(unittest.TestCase):
    """Contrat postMessage carte (ORA-125) : la carte générée ne doit traiter
    un message que s'il provient de la même origine que la page qui l'embarque,
    et doit gérer tous les types de messages documentés (FLY_TO, TOGGLE_LAYER)."""

    def test_rejects_messages_from_a_different_origin(self):
        script = generate_map.build_bridge_message_script("map_abc123")

        self.assertIn("e.origin", script)
        self.assertIn("window.location.origin", script)

    def test_handles_toggle_layer_by_clicking_matching_checkbox(self):
        script = generate_map.build_bridge_message_script("map_abc123")

        self.assertIn("TOGGLE_LAYER", script)
        self.assertIn("box.click()", script)

    def test_handles_fly_to_by_calling_flyto_on_the_map_instance(self):
        script = generate_map.build_bridge_message_script("map_abc123")

        self.assertIn("FLY_TO", script)
        self.assertIn("map_abc123.flyTo(", script)
        self.assertIn("e.data.lat", script)
        self.assertIn("e.data.lng", script)

    def test_handles_fly_to_bounds_by_calling_flytobounds_on_the_map_instance(self):
        """ORA-105 : recentrage sur la bounding-box des résultats filtrés."""
        script = generate_map.build_bridge_message_script("map_abc123")

        self.assertIn("FLY_TO_BOUNDS", script)
        self.assertIn("map_abc123.flyToBounds(", script)
        self.assertIn("e.data.bounds", script)


if __name__ == "__main__":
    unittest.main()
