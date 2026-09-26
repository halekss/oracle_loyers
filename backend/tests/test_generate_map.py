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

    def test_handles_toggle_layer_via_the_key_to_featuregroup_dictionary(self):
        """Remplace l'ancienne correspondance par texte de <label> (fragile,
        cassait dès que le contrôle Folium était cassé/masqué) par un accès
        direct map.addLayer/removeLayer via `window.oracleLayerGroups[key]`,
        rempli par build_layer_groups_script. Le contrat TOGGLE_LAYER utilise
        désormais `key` (mapLayers.config.json), plus `name`."""
        script = generate_map.build_bridge_message_script("map_abc123")

        self.assertIn("TOGGLE_LAYER", script)
        self.assertIn("oracleLayerGroups", script)
        self.assertIn("e.data.key", script)
        self.assertIn("map_abc123.addLayer(", script)
        self.assertIn("map_abc123.removeLayer(", script)
        self.assertIn("map_abc123.hasLayer(", script)

    def test_no_longer_depends_on_layercontrol_label_text(self):
        script = generate_map.build_bridge_message_script("map_abc123")

        self.assertNotIn("getElementsByTagName('label')", script)
        self.assertNotIn("box.click()", script)
        self.assertNotIn("e.data.name", script)

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

    def test_handles_set_tile_url_and_validates_the_url_template(self):
        """L'URL du proxy de tuiles arrive au runtime (dépend du déploiement) :
        validée (http(s), modèle {z}/{x}/{y}{r}.png, pas de caractère dangereux)."""
        script = generate_map.build_bridge_message_script("map_abc123")

        self.assertIn("SET_TILE_URL", script)
        self.assertIn("indexOf('https://')", script)
        self.assertIn("/{z}/{x}/{y}{r}.png", script)
        self.assertIn("map_abc123.eachLayer(", script)
        self.assertIn("setUrl(tileUrl)", script)

    def test_handles_set_focus_by_styling_markers_per_focus_or_dim_state(self):
        """v3 (ORA-183) : tous les pings d'un cavalier actif restent visibles,
        rayon actif ou non. Le rayon les met seulement en avant (FOCUS_STYLE) :
        14px/opacité 1/halo dans le rayon, 10px/opacité >= 0.75 hors du rayon
        — plus jamais un ping quasi invisible sur fond sombre."""
        script = generate_map.build_bridge_message_script("map_abc123")

        self.assertIn("SET_FOCUS", script)
        self.assertIn("distanceTo(", script)
        self.assertIn("setOpacity(", script)
        self.assertIn("e.data.radius_m", script)
        self.assertNotIn("0.25", script)
        self.assertIn(str(generate_map.FOCUS_STYLE["dim"]["opacity"]), script)
        self.assertGreaterEqual(generate_map.FOCUS_STYLE["dim"]["opacity"], 0.75)

    def test_set_focus_scales_the_marker_shape_and_adds_a_halo_in_focus(self):
        script = generate_map.build_bridge_message_script("map_abc123")

        set_focus_branch = script.split("'SET_FOCUS'")[1].split("else if")[0]
        self.assertIn("oracle-cav-outer", set_focus_branch)
        self.assertIn("scale(", set_focus_branch)
        self.assertIn("drop-shadow(", set_focus_branch)
        self.assertIn("entry.color", set_focus_branch)

    def test_handles_set_focus_by_drawing_a_filled_dashed_leaflet_circle(self):
        script = generate_map.build_bridge_message_script("map_abc123")

        set_focus_branch = script.split("'SET_FOCUS'")[1].split("else if")[0]
        self.assertIn("L.circle(", set_focus_branch)
        self.assertIn("e.data.lat", set_focus_branch)
        self.assertIn("e.data.lng", set_focus_branch)
        self.assertIn("dashArray", set_focus_branch)
        self.assertIn("fillOpacity", set_focus_branch)
        self.assertIn("map_abc123.addLayer(", set_focus_branch)

    def test_replaces_the_previous_focus_circle_instead_of_stacking_them(self):
        """Un second SET_FOCUS (nouveau rayon) ne doit pas laisser l'ancien
        cercle affiché en plus du nouveau."""
        script = generate_map.build_bridge_message_script("map_abc123")

        set_focus_branch = script.split("'SET_FOCUS'")[1].split("else if")[0]
        self.assertIn("removeLayer(", set_focus_branch)

    def test_handles_clear_focus_by_restoring_full_opacity_and_removing_the_circle(self):
        script = generate_map.build_bridge_message_script("map_abc123")

        self.assertIn("CLEAR_FOCUS", script)
        clear_focus_branch = script.split("'CLEAR_FOCUS'")[1]
        self.assertIn("setOpacity(1)", clear_focus_branch)
        self.assertIn("map_abc123.removeLayer(", clear_focus_branch)

    def test_clear_focus_resets_the_marker_shape_scale_and_halo(self):
        script = generate_map.build_bridge_message_script("map_abc123")

        clear_focus_branch = script.split("'CLEAR_FOCUS'")[1]
        self.assertIn("oracle-cav-outer", clear_focus_branch)


class FocusStyleConstantTest(unittest.TestCase):
    """FOCUS_STYLE (ORA-183) : source unique des tailles/opacités appliquées
    par SET_FOCUS/CLEAR_FOCUS, dans le rayon (`focus`) et hors du rayon
    (`dim`) — base 12px (CAVALIER_ICON_CSS .oracle-cav-outer)."""

    def test_focus_state_is_full_size_full_opacity(self):
        self.assertAlmostEqual(generate_map.FOCUS_STYLE["focus"]["scale"], 14 / 12)
        self.assertEqual(generate_map.FOCUS_STYLE["focus"]["opacity"], 1)

    def test_dim_state_stays_readable_on_a_dark_background(self):
        self.assertAlmostEqual(generate_map.FOCUS_STYLE["dim"]["scale"], 10 / 12)
        self.assertGreaterEqual(generate_map.FOCUS_STYLE["dim"]["opacity"], 0.75)


class TileLayerNeverEmbedsAKeyTest(unittest.TestCase):
    """Aucune clé, ni URL CARTO, dans la carte générée (fichier versionné)."""

    def test_placeholder_is_an_inline_pixel_without_network_or_key(self):
        self.assertTrue(generate_map.TILE_PLACEHOLDER_URL.startswith("data:image/gif;base64,"))
        self.assertNotIn("carto", generate_map.TILE_PLACEHOLDER_URL.lower())
        self.assertFalse(hasattr(generate_map, "CARTO_API_KEY"))


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

    def test_cavalier_layers_declare_a_shape_for_the_map_marker_icon(self):
        """Source unique (mapLayers.config.json) couleur+forme, lue à la
        fois par ce script (icônes DivIcon des pings) et par React
        (CavalierRow, légende carte) — plus de dict COLORS séparé ici."""
        layers_by_key = {layer["key"]: layer for layer in generate_map.load_layers_config()}
        expected_shapes = {
            "Vice": "circle",
            "Gentrification": "diamond",
            "Nuisance": "triangle",
            "Superstition": "square",
        }
        for key, shape in expected_shapes.items():
            self.assertEqual(layers_by_key[key]["shape"], shape, key)

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


class CavalierIconHtmlTest(unittest.TestCase):
    """Remplace les anciens folium.CircleMarker (couleur figée dans un dict
    COLORS) par des DivIcon aux mêmes formes/couleurs que le panneau React
    (CavalierRow.jsx) — une classe CSS par forme plutôt qu'un SVG inline par
    marker (des centaines de cavaliers par carte), pour ne pas alourdir le
    HTML généré."""

    def test_uses_a_shared_css_class_per_shape_rather_than_inline_svg(self):
        html_out = generate_map.cavalier_icon_html("circle", "#F87171")

        self.assertIn("oracle-cav-circle", html_out)
        self.assertNotIn("<svg", html_out)

    def test_applies_the_given_color_as_inline_background(self):
        html_out = generate_map.cavalier_icon_html("diamond", "#C084FC")

        self.assertIn("#C084FC", html_out)
        self.assertIn("oracle-cav-diamond", html_out)

    def test_falls_back_to_circle_for_an_unrecognized_shape(self):
        html_out = generate_map.cavalier_icon_html("hexagon", "#FFFFFF")

        self.assertIn("oracle-cav-circle", html_out)


class BuildCavalierMarkersScriptTest(unittest.TestCase):
    """Référence JS de chaque marker de cavalier (variable Folium + lat/lng +
    famille) : nécessaire pour que SET_FOCUS (build_bridge_message_script)
    puisse faire varier son opacité selon la distance au point choisi."""

    def test_declares_a_global_array_with_one_entry_per_marker(self):
        script = generate_map.build_cavalier_markers_script([
            {"js_var": "marker_abc", "lat": 45.75, "lng": 4.83, "famille": "vice", "color": "#F87171"},
            {"js_var": "marker_def", "lat": 45.76, "lng": 4.84, "famille": "gentrification", "color": "#C084FC"},
        ])

        self.assertIn("oracleCavalierMarkers", script)
        self.assertIn("marker_abc", script)
        self.assertIn("marker_def", script)
        self.assertIn("45.75", script)
        self.assertIn("vice", script)

    def test_includes_the_marker_color_for_the_in_focus_halo(self):
        """SET_FOCUS (build_bridge_message_script) lit `entry.color` pour
        dessiner le halo drop-shadow des pings dans le rayon."""
        script = generate_map.build_cavalier_markers_script([
            {"js_var": "marker_abc", "lat": 45.75, "lng": 4.83, "famille": "vice", "color": "#F87171"},
        ])

        self.assertIn("color:\"#F87171\"", script.replace(" ", "").replace("'", '"'))

    def test_returns_an_empty_array_for_no_entries(self):
        script = generate_map.build_cavalier_markers_script([])

        self.assertIn("oracleCavalierMarkers=[]", script.replace(" ", ""))

    def test_assigns_to_window_rather_than_declaring_a_local_var(self):
        """Doit rester accessible une fois englobé dans une fonction (le
        callback `window.addEventListener('load', ...)`, cf. bug #1/#3/#5/#8 :
        un `var` s'y serait limité à la portée de cette fonction, invisible
        depuis le listener 'message' (build_bridge_message_script)."""
        script = generate_map.build_cavalier_markers_script([
            {"js_var": "marker_abc", "lat": 45.75, "lng": 4.83, "famille": "vice", "color": "#F87171"},
        ])

        self.assertIn("window.oracleCavalierMarkers", script)
        self.assertNotIn("var oracleCavalierMarkers", script)


class BuildLayerGroupsScriptTest(unittest.TestCase):
    """Dictionnaire JS {clé mapLayers.config.json -> FeatureGroup Folium},
    construit une fois la carte rendue (load) — remplace la correspondance
    par texte de <label> pour TOGGLE_LAYER (bugs #1/#2/#3/#5/#8)."""

    def test_declares_a_global_dict_keyed_by_layer_key(self):
        script = generate_map.build_layer_groups_script({
            "Vice": "feature_group_abc",
            "Quartiers": "geo_json_def",
        })

        self.assertIn("window.oracleLayerGroups", script)
        self.assertNotIn("var oracleLayerGroups", script)
        self.assertIn('"Vice"', script)
        self.assertIn("feature_group_abc", script)
        self.assertIn('"Quartiers"', script)
        self.assertIn("geo_json_def", script)

    def test_returns_an_empty_dict_for_no_entries(self):
        script = generate_map.build_layer_groups_script({})

        self.assertIn("oracleLayerGroups={}", script.replace(" ", ""))


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


class ScaleScriptTest(unittest.TestCase):
    """ORA-183 (v3) : l'ancienne légende Folium (build_legend_html, groupes
    Annonces/Métro/Cavaliers & quartiers) est supprimée — elle se
    superposait à la légende React (MapComponent) et cachait l'échelle
    métrique. Seule l'échelle survit côté carte générée."""

    def test_scale_script_waits_for_load_and_adds_the_metric_scale(self):
        script = generate_map.build_scale_script('map_abc')

        self.assertIn("addEventListener('load'", script)
        self.assertIn('L.control.scale', script)
        self.assertIn("position: 'bottomleft'", script)

    def test_no_longer_builds_a_folium_side_legend(self):
        self.assertFalse(hasattr(generate_map, 'build_legend_html'))
        self.assertFalse(hasattr(generate_map, 'build_legend_and_scale_script'))


class MainRegeneratesAWorkingLyonMapTest(unittest.TestCase):
    """Test d'intégration (données réelles versionnées, backend/data/) : exécute
    generate_map.main('lyon') pour de vrai et inspecte le HTML produit —
    seule façon fiable de vérifier que le script injecté ne référence pas des
    variables pas-encore-définies (bugs #1/#2/#3/#5/#8 : un crash JS en tête
    du <script> empêchait tout le reste, y compris SET_TILE_URL/TOGGLE_LAYER,
    de s'exécuter). Réécrit le fichier committé (même effet que la commande
    de régénération manuelle), pas un fichier temporaire : c'est le fichier
    qu'on veut justement tenir à jour et vérifier."""

    @classmethod
    def setUpClass(cls):
        generate_map.main('lyon')
        output_path = generate_map.resolve_ville_paths('lyon')['output_html']
        with open(output_path, 'r', encoding='utf-8') as f:
            cls.html = f.read()

    def test_the_tile_layer_is_present(self):
        self.assertIn("CartoDB dark_matter", self.html)
        self.assertIn(generate_map.TILE_PLACEHOLDER_URL, self.html)

    def test_cavalier_markers_are_declared_after_the_load_listener_opens(self):
        """Ordre textuel : oracleCavalierMarkers doit être à l'intérieur du
        callback `addEventListener('load', ...)`, pas avant — sinon il
        s'exécute avant que Folium ait défini les variables `marker_xxx`
        (rendues par Folium après `</body>`) et plante (bug #1/#2/#3/#5/#8)."""
        load_pos = self.html.find("addEventListener('load'")
        markers_pos = self.html.find("oracleCavalierMarkers=")

        self.assertNotEqual(load_pos, -1)
        self.assertNotEqual(markers_pos, -1)
        self.assertLess(load_pos, markers_pos)

    def test_layer_groups_are_declared_after_the_load_listener_opens(self):
        load_pos = self.html.find("addEventListener('load'")
        groups_pos = self.html.find("oracleLayerGroups=")

        self.assertNotEqual(load_pos, -1)
        self.assertNotEqual(groups_pos, -1)
        self.assertLess(load_pos, groups_pos)

    def test_all_four_cavalier_families_have_at_least_one_marker(self):
        for famille in ('vice', 'gentrification', 'nuisance', 'superstition'):
            self.assertIn(f'famille:"{famille}"', self.html, f"aucun marker pour {famille}")

    def test_layer_groups_dict_has_an_entry_for_each_cavalier_and_quartiers(self):
        for key in ('Vice', 'Gentrification', 'Nuisance', 'Superstition', 'Quartiers', 'Metro'):
            self.assertIn(f'"{key}":', self.html, f"pas d'entrée oracleLayerGroups pour {key}")

    def test_cavaliers_are_no_longer_rendered_as_circlemarker(self):
        """Un seul marker par lieu (folium.Marker/DivIcon, cf. cavalier_icon_html)
        — plus l'ancien folium.CircleMarker (bug #4, doublons suspectés)."""
        self.assertIn("oracle-cav-circle", self.html)
        self.assertIn("oracle-cav-diamond", self.html)
        self.assertIn("oracle-cav-triangle", self.html)
        self.assertIn("oracle-cav-square", self.html)

    def test_toggle_layer_no_longer_matches_by_label_text(self):
        self.assertNotIn("getElementsByTagName('label')", self.html)

    def test_no_folium_side_legend_in_the_generated_html(self):
        """ORA-183 (v3) : une seule légende (React, MapComponent) — celle
        générée côté Folium (oracle-legend) est retirée pour ne plus se
        superposer à elle et masquer l'échelle métrique."""
        self.assertNotIn("oracle-legend", self.html)

    def test_the_metric_scale_is_still_present(self):
        self.assertIn("L.control.scale", self.html)


if __name__ == "__main__":
    unittest.main()
