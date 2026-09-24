import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import generate_map


class ComputeLayerCountsTest(unittest.TestCase):
    def test_counts_poi_by_category_substring_case_insensitive(self):
        """ORA-172 : même logique de correspondance que le rendu des
        marqueurs (mapping_simple) — "Vice - Bar" compte pour Vice."""
        df_poi = pd.DataFrame({'type': ['Vice - Bar', 'vice - kebab', 'Gentrification - Yoga']})
        df_immo = pd.DataFrame({'type_local': []})

        counts = generate_map.compute_layer_counts(df_poi, df_immo)

        self.assertEqual(counts['Vice'], 2)
        self.assertEqual(counts['Gentrification'], 1)
        self.assertEqual(counts['Nuisance'], 0)
        self.assertEqual(counts['Superstition'], 0)

    def test_counts_immo_by_exact_type_local_bucket(self):
        df_poi = pd.DataFrame({'type': []})
        df_immo = pd.DataFrame({'type_local': ['Studio/T1', 'T2', 'T2', 'T3', 'Grand (T4+)', 'Grand (T4+)']})

        counts = generate_map.compute_layer_counts(df_poi, df_immo)

        self.assertEqual(counts['Studio'], 1)
        self.assertEqual(counts['T2'], 2)
        self.assertEqual(counts['T3'], 1)
        self.assertEqual(counts['T4'], 2)

    def test_returns_an_empty_dict_when_neither_dataframe_has_the_expected_column(self):
        counts = generate_map.compute_layer_counts(pd.DataFrame(), pd.DataFrame())
        self.assertEqual(counts, {})


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

    def test_tracks_the_click_via_postmessage_when_annonce_id_is_known(self):
        """ORA-107 : parité avec AnnonceCard.jsx (api.logAnnonceClick), sans
        dupliquer la connaissance de l'URL backend dans le HTML statique
        généré — la carte notifie le parent React via le contrat postMessage
        (ORA-125/126), qui appelle le même api.logAnnonceClick que React."""
        html_out = generate_map.build_immo_popup_html(
            type_local="T2", prix="750", quartier="Perrache",
            listing_url="https://example.com/annonce/7", annonce_id=42,
        )

        self.assertIn("ANNONCE_CLICK", html_out)
        self.assertIn("id: 42", html_out)
        self.assertIn("window.location.origin", html_out)

    def test_omits_click_tracking_when_annonce_id_is_unknown(self):
        html_out = generate_map.build_immo_popup_html(
            type_local="T2", prix="750", quartier="Perrache",
            listing_url="https://example.com/annonce/7", annonce_id=None,
        )

        self.assertNotIn("ANNONCE_CLICK", html_out)


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


class LoadLayersConfigTest(unittest.TestCase):
    """ORA-130 : la liste des calques (nom Folium/TOGGLE_LAYER, visibilité par
    défaut, libellé et couleur du panneau React) vient d'un unique JSON
    partagé avec frontend/src/config/mapLayers.config.json (import JS direct
    du même fichier côté React), pour ne plus avoir à synchroniser à la main
    LAYER_MAPPING (MapComponent.jsx) et les FeatureGroup/GeoJson (ce script)
    à chaque nouveau calque."""

    def test_loads_the_committed_shared_config_by_default(self):
        layers = generate_map.load_layers_config()

        self.assertIsInstance(layers, list)
        keys = {layer["key"] for layer in layers}
        self.assertEqual(
            keys,
            {"Studio", "T2", "T3", "T4", "Metro", "Funicular", "Vice", "Gentrification", "Nuisance", "Superstition", "Quartiers"},
        )

    def test_each_layer_has_the_fields_required_by_both_sides(self):
        for layer in generate_map.load_layers_config():
            self.assertIn("key", layer)
            self.assertIn("name", layer)
            self.assertIn("label", layer)
            self.assertIn("group", layer)
            self.assertIsInstance(layer["defaultVisible"], bool)

    def test_preserves_current_default_visibility_per_layer(self):
        """Non-régression ORA-130 : le refactor ne doit rien changer à l'état
        initial des calques (ex. Quartiers/Nuisance/Gentrification/Superstition
        off par défaut, cf. ORA-104)."""
        layers_by_key = {layer["key"]: layer for layer in generate_map.load_layers_config()}

        expected_defaults = {
            "Studio": True,
            "T2": True,
            "T3": True,
            "T4": True,
            "Metro": True,
            "Vice": True,
            "Gentrification": False,
            "Nuisance": False,
            "Superstition": False,
            "Quartiers": False,
        }
        for key, expected in expected_defaults.items():
            self.assertEqual(layers_by_key[key]["defaultVisible"], expected, key)

    def test_loads_from_an_explicit_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "layers.json")
            payload = [{"key": "Test", "name": "Test", "label": "Test", "group": "contexte", "defaultVisible": True}]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)

            self.assertEqual(generate_map.load_layers_config(path), payload)

    def test_raises_when_the_config_file_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = os.path.join(tmp_dir, "missing.json")

            with self.assertRaises(FileNotFoundError):
                generate_map.load_layers_config(missing_path)


class LoadGeojsonFileTest(unittest.TestCase):
    """ORA-104 : chargement de la couche GeoJSON des quartiers, versionnée
    dans le repo (pas de dépendance réseau à runtime)."""

    def test_returns_none_when_the_file_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = os.path.join(tmp_dir, "missing.geojson")

            self.assertIsNone(generate_map.load_geojson_file(missing_path))

    def test_loads_a_valid_geojson_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "quartiers.geojson")
            geojson = {"type": "FeatureCollection", "features": [{"type": "Feature"}]}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(geojson, f)

            self.assertEqual(generate_map.load_geojson_file(path), geojson)

    def test_returns_none_for_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "broken.geojson")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not valid json")

            self.assertIsNone(generate_map.load_geojson_file(path))


class BuildImmoTooltipHtmlTest(unittest.TestCase):
    def test_includes_type_and_price(self):
        html_out = generate_map.build_immo_tooltip_html(type_local="T2", prix="750")

        self.assertIn("T2", html_out)
        self.assertIn("750", html_out)

    def test_never_renders_a_link(self):
        # Un tooltip Leaflet (survol) ne peut pas héberger de contenu cliquable
        # de façon fiable (cf. ORA-99) : le lien reste réservé au popup (clic).
        html_out = generate_map.build_immo_tooltip_html(type_local="T2", prix="750")

        self.assertNotIn("<a ", html_out)

    def test_never_renders_an_image_tag(self):
        html_out = generate_map.build_immo_tooltip_html(type_local="T2", prix="750")

        self.assertNotIn("<img", html_out)

    def test_escapes_hostile_type_value(self):
        html_out = generate_map.build_immo_tooltip_html(type_local="<script>alert(1)</script>", prix="750")

        self.assertNotIn("<script>alert(1)</script>", html_out)


class ResolveVillePathsTest(unittest.TestCase):
    def test_lyon_paths_match_existing_filenames(self):
        paths = generate_map.resolve_ville_paths("lyon")

        self.assertTrue(paths["output_html"].endswith("map_pings_lyon_calques.html"))
        self.assertTrue(paths["metadata_json"].endswith("map_metadata_lyon.json"))
        self.assertTrue(paths["poi_csv"].endswith("cavaliers_lyon.csv"))
        self.assertTrue(paths["metro_json"].endswith("metro_lyon.json"))
        self.assertTrue(paths["quartiers_geojson"].endswith("lyon_arrondissements.geojson"))
        self.assertEqual(paths["center"], [45.7640, 4.8357])

    def test_lille_paths_are_distinct_from_lyon(self):
        paths = generate_map.resolve_ville_paths("lille")

        self.assertTrue(paths["output_html"].endswith("map_pings_lille_calques.html"))
        self.assertTrue(paths["poi_csv"].endswith("cavaliers_lille.csv"))
        self.assertEqual(paths["center"], [50.6292, 3.0573])

    def test_raises_for_an_undeclared_ville(self):
        with self.assertRaises(KeyError):
            generate_map.resolve_ville_paths("marseille")


class FilterByVilleTest(unittest.TestCase):
    def test_keeps_only_rows_matching_the_ville_case_insensitively(self):
        df = pd.DataFrame({"ville": ["Lyon", "Lille", "Lyon"], "prix": [800, 700, 900]})

        result = generate_map.filter_by_ville(df, "lyon")

        self.assertEqual(list(result["prix"]), [800, 900])

    def test_returns_dataframe_unchanged_when_ville_column_is_missing(self):
        df = pd.DataFrame({"prix": [800, 700]})

        result = generate_map.filter_by_ville(df, "lyon")

        self.assertEqual(len(result), 2)


BANDS = {
    'thresholdPct': 5,
    'bands': {
        'below': {'label': 'Sous le marché', 'color': '#22c55e'},
        'within': {'label': 'Dans le marché', 'color': '#facc15'},
        'above': {'label': 'Au-dessus du marché', 'color': '#e9003a'},
    },
}


class MarketBandTest(unittest.TestCase):
    """ORA-165 : seuils ±5 % (mêmes bornes que services/marketBand.js)."""

    def test_thresholds(self):
        cases = [(-30, 'below'), (-5.1, 'below'), (-5, 'within'), (0, 'within'), (5, 'within'), (5.1, 'above'), (40, 'above')]
        for ecart, expected in cases:
            self.assertEqual(generate_map.market_band(ecart, 5), expected, ecart)

    def test_shared_config_uses_a_5_percent_threshold(self):
        self.assertEqual(generate_map.load_market_bands()['thresholdPct'], 5)

    def test_ecart_vs_median(self):
        self.assertEqual(generate_map.ecart_vs_median(900, 800), 12)
        self.assertEqual(generate_map.ecart_vs_median(700, 800), -12)
        self.assertIsNone(generate_map.ecart_vs_median(700, 0))
        self.assertIsNone(generate_map.ecart_vs_median('n/a', 800))


class ReferenceMediansTest(unittest.TestCase):
    def test_uses_quartier_median_or_falls_back_to_type_median(self):
        df = pd.DataFrame({
            'quartier': ['A', 'A', 'A', 'B'],
            'type_local': ['T2'] * 4,
            'prix': [700, 800, 900, 1500],
        })

        medians = generate_map.compute_reference_medians(df)

        self.assertEqual(medians.iloc[0], 800)   # A : 3 annonces -> médiane du quartier
        self.assertEqual(medians.iloc[3], 850)   # B : 1 annonce -> médiane du type (700, 800, 900, 1500)


class PricePillAndGroupingTest(unittest.TestCase):
    def test_pill_colored_by_band_and_escaped(self):
        html_pill = generate_map.build_price_pill_html('<b>765</b>', 'below', BANDS)

        self.assertIn('#22c55e', html_pill)
        self.assertIn('&lt;b&gt;765&lt;/b&gt;', html_pill)
        self.assertNotIn('oracle-pill-count', html_pill)

    def test_group_pill_shows_the_count(self):
        self.assertIn('>3</span>', generate_map.build_price_pill_html('850', 'above', BANDS, count=3))

    def test_groups_listings_with_identical_coordinates_only(self):
        entries = [
            {'lat': 45.75, 'lon': 4.85, 'id': 1},
            {'lat': 45.750001, 'lon': 4.850001, 'id': 2},  # même point à ~0,1 m
            {'lat': 45.76, 'lon': 4.86, 'id': 3},
        ]

        groups = generate_map.group_by_exact_position(entries)

        self.assertEqual([[e['id'] for e in g] for g in groups], [[1, 2], [3]])

    def test_group_popup_lists_rows_and_vizzit_mention(self):
        group = [
            {'type_local': 'T2', 'surface': 45, 'prix': '850', 'ecart': -10, 'site': 'Vizzit', 'url': 'https://x.test/a', 'annonce_id': 7},
            {'type_local': 'T3', 'surface': 70, 'prix': '1200', 'ecart': 12, 'site': 'Vizzit', 'url': None, 'annonce_id': None},
        ]

        popup = generate_map.build_group_popup_html(group, BANDS)

        self.assertIn('2 annonces · même adresse', popup)
        self.assertIn('45 m²', popup)
        self.assertIn('-10 %', popup)
        self.assertIn('+12 %', popup)
        self.assertIn('Géolocalisées sur la même rue (Vizzit)', popup)
        self.assertIn("ANNONCE_CLICK", popup)

    def test_group_popup_without_vizzit_uses_generic_note(self):
        group = [
            {'type_local': 'T2', 'surface': 45, 'prix': '850', 'ecart': 0, 'site': 'PAP'},
            {'type_local': 'T2', 'surface': 46, 'prix': '860', 'ecart': 1, 'site': 'Vizzit'},
        ]

        popup = generate_map.build_group_popup_html(group, BANDS)

        self.assertNotIn('Vizzit)', popup)
        self.assertIn('Coordonnées identiques', popup)


class QuartierLabelsAndLegendTest(unittest.TestCase):
    def test_labels_are_uppercase_and_skip_fallback_quartiers(self):
        df = pd.DataFrame({
            'quartier': ['Ainay'] * 3 + ['Lyon / Non localisé'] * 3 + ['Peu'] * 2,
            'latitude': [45.75, 45.76, 45.77] + [45.7] * 3 + [45.8] * 2,
            'longitude': [4.82, 4.83, 4.84] + [4.9] * 3 + [4.7] * 2,
        })

        labels = generate_map.compute_quartier_labels(df)

        self.assertEqual([l[0] for l in labels], ['AINAY'])
        self.assertAlmostEqual(labels[0][1], 45.76)

    def test_legend_lists_layers_bands_and_thresholds(self):
        layers = [
            {'name': 'Immo T2', 'label': 'Apparts T2', 'group': 'immobilier', 'uiColor': '#22c55e'},
            {'name': 'Metro', 'label': 'Métro', 'group': 'transports', 'uiColor': '#818181'},
        ]

        legend = generate_map.build_legend_html(layers, BANDS)

        self.assertIn("data-layer='Immo T2'", legend)
        self.assertIn('Écart au loyer médian du quartier', legend)
        for label in ('Sous le marché', 'Dans le marché', 'Au-dessus du marché'):
            self.assertIn(label, legend)
        self.assertIn('−5 %', legend)

    def test_scale_script_waits_for_load_and_tracks_layers(self):
        script = generate_map.build_legend_and_scale_script('map_abc', '<div class="oracle-legend"></div>')

        self.assertIn("addEventListener('load'", script)
        self.assertIn('L.control.scale', script)
        self.assertIn('overlayremove', script)


if __name__ == "__main__":
    unittest.main()
