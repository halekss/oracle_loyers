import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import generate_map


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


class ResolveListingVisualTest(unittest.TestCase):
    def test_prefers_legit_photo_over_link(self):
        row = {"image_url": "https://cdn.example.com/photo.jpg", "url": "https://example.com/annonce/3"}

        visual = generate_map.resolve_listing_visual(row, "https://example.com/annonce/3")

        self.assertEqual(visual, {"kind": "photo", "url": "https://cdn.example.com/photo.jpg"})

    def test_falls_back_to_link_when_no_photo_column(self):
        row = {"url": "https://example.com/annonce/4"}

        visual = generate_map.resolve_listing_visual(row, "https://example.com/annonce/4")

        self.assertEqual(visual, {"kind": "link", "url": "https://example.com/annonce/4"})

    def test_falls_back_to_link_when_photo_url_invalid(self):
        row = {"photo": "javascript:alert(1)", "url": "https://example.com/annonce/5"}

        visual = generate_map.resolve_listing_visual(row, "https://example.com/annonce/5")

        self.assertEqual(visual, {"kind": "link", "url": "https://example.com/annonce/5"})

    def test_none_when_neither_photo_nor_url(self):
        visual = generate_map.resolve_listing_visual({}, None)

        self.assertEqual(visual, {"kind": "none", "url": None})


class BuildImmoPopupHtmlTest(unittest.TestCase):
    def test_includes_price_type_and_quartier(self):
        html = generate_map.build_immo_popup_html(
            type_local="T2",
            prix="750",
            quartier="Perrache",
            visual={"kind": "link", "url": "https://example.com/annonce/6"},
        )

        self.assertIn("T2", html)
        self.assertIn("750", html)
        self.assertIn("Perrache", html)

    def test_renders_photo_thumbnail_when_visual_is_photo(self):
        html = generate_map.build_immo_popup_html(
            type_local="T2",
            prix="750",
            quartier="Perrache",
            visual={"kind": "photo", "url": "https://cdn.example.com/photo.jpg"},
        )

        self.assertIn("<img", html)
        self.assertIn("https://cdn.example.com/photo.jpg", html)

    def test_renders_link_when_visual_is_link(self):
        html = generate_map.build_immo_popup_html(
            type_local="T2",
            prix="750",
            quartier="Perrache",
            visual={"kind": "link", "url": "https://example.com/annonce/7"},
        )

        self.assertNotIn("<img", html)
        self.assertIn("https://example.com/annonce/7", html)
        self.assertIn("<a ", html)

    def test_escapes_hostile_quartier_value(self):
        html = generate_map.build_immo_popup_html(
            type_local="T2",
            prix="750",
            quartier="<script>alert(1)</script>",
            visual={"kind": "none", "url": None},
        )

        self.assertNotIn("<script>alert(1)</script>", html)

    def test_includes_view_count_when_provided(self):
        html = generate_map.build_immo_popup_html(
            type_local="T2",
            prix="750",
            quartier="Perrache",
            visual={"kind": "none", "url": None},
            views=42,
        )

        self.assertIn("42", html)


class BuildMarkerClickScriptTest(unittest.TestCase):
    def test_returns_empty_string_when_no_redirect_url(self):
        script = generate_map.build_marker_click_script(
            "circle_marker_abc", listing_id="1", redirect_url=None, api_base_url="http://localhost:5000/api"
        )

        self.assertEqual(script, "")

    def test_binds_click_handler_and_opens_redirect_url(self):
        script = generate_map.build_marker_click_script(
            "circle_marker_abc", listing_id="1", redirect_url="https://example.com/annonce/8",
            api_base_url="http://localhost:5000/api",
        )

        self.assertIn("circle_marker_abc.on('click'", script)
        self.assertIn("window.open(", script)
        self.assertIn('"https://example.com/annonce/8"', script)

    def test_escapes_redirect_url_against_js_injection(self):
        hostile_url = 'https://example.com/");alert(document.cookie);//'

        script = generate_map.build_marker_click_script(
            "circle_marker_abc", listing_id="1", redirect_url=hostile_url, api_base_url="http://localhost:5000/api"
        )

        self.assertNotIn('window.open("https://example.com/");alert', script)
        self.assertIn('\\"', script)

    def test_posts_view_increment_before_redirect_when_listing_id_present(self):
        script = generate_map.build_marker_click_script(
            "circle_marker_abc", listing_id="42", redirect_url="https://example.com/annonce/9",
            api_base_url="http://localhost:5000/api",
        )

        self.assertIn("fetch(", script)
        self.assertIn("http://localhost:5000/api/listings/42/views", script)

    def test_skips_view_increment_when_no_listing_id(self):
        script = generate_map.build_marker_click_script(
            "circle_marker_abc", listing_id=None, redirect_url="https://example.com/annonce/10",
            api_base_url="http://localhost:5000/api",
        )

        self.assertNotIn("fetch(", script)


if __name__ == "__main__":
    unittest.main()
