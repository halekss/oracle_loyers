import os
import sys
import tempfile
import unittest
import json
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import data_fusion
from data_fusion import (
    clean_price_integer,
    clean_surface,
    extract_postal_code,
    extract_type,
    format_description,
    load_declared_villes,
    resolve_default_cp,
    resolve_seloger_lieu,
    run_fusion,
    site_files_config,
)


class CleanPriceIntegerTest(unittest.TestCase):
    def test_strips_currency_symbol_and_spaces(self):
        self.assertEqual(clean_price_integer("850 €"), 850)

    def test_strips_eur_and_cc_suffixes(self):
        self.assertEqual(clean_price_integer("650€ cc"), 650)
        self.assertEqual(clean_price_integer("700 eur"), 700)

    def test_handles_thousands_separator_space(self):
        self.assertEqual(clean_price_integer("1 200 €"), 1200)

    def test_returns_none_for_nan(self):
        self.assertIsNone(clean_price_integer(pd.NA))
        self.assertIsNone(clean_price_integer(float("nan")))

    def test_returns_none_when_no_digits_present(self):
        self.assertIsNone(clean_price_integer("Prix sur demande"))


class CleanSurfaceTest(unittest.TestCase):
    def test_extracts_integer_surface_before_m2_marker(self):
        self.assertEqual(clean_surface("Appartement 45 m2 lumineux"), 45.0)

    def test_extracts_decimal_surface_with_comma(self):
        self.assertEqual(clean_surface("62,5 m²"), 62.5)

    def test_extracts_decimal_surface_with_dot(self):
        self.assertEqual(clean_surface("62.5 m2"), 62.5)

    def test_returns_none_when_no_surface_marker_found(self):
        self.assertIsNone(clean_surface("Bel appartement lumineux"))

    def test_returns_none_for_nan(self):
        self.assertIsNone(clean_surface(pd.NA))


class ExtractPostalCodeTest(unittest.TestCase):
    def test_extracts_explicit_lyon_postal_code(self):
        self.assertEqual(extract_postal_code("Appartement Lyon 69007"), "69007")

    def test_derives_postal_code_from_arrondissement_mention(self):
        self.assertEqual(extract_postal_code("Lyon 3eme, quartier Part-Dieu"), "69003")

    def test_defaults_to_69000_when_nothing_found(self):
        self.assertEqual(extract_postal_code("Bel appartement"), "69000")

    def test_defaults_to_69000_for_nan(self):
        self.assertEqual(extract_postal_code(pd.NA), "69000")

    def test_extracts_explicit_lille_postal_code(self):
        self.assertEqual(extract_postal_code("Appartement Lille 59800"), "59800")

    def test_extracts_lille_postal_code_from_free_text(self):
        self.assertEqual(extract_postal_code("Studio quartier Wazemmes, 59000 Lille"), "59000")

    def test_uses_given_default_cp_when_nothing_found(self):
        self.assertEqual(extract_postal_code("Bel appartement", default_cp="59000"), "59000")

    def test_uses_given_default_cp_for_nan(self):
        self.assertEqual(extract_postal_code(pd.NA, default_cp="59000"), "59000")

    def test_default_cp_defaults_to_69000_when_not_given(self):
        self.assertEqual(extract_postal_code("Bel appartement"), "69000")


class ResolveSelogerLieuTest(unittest.TestCase):
    """ORA-71 POC follow-up : le champ Lieu de SeLoger contient parfois une
    vraie commune limitrophe (pas Lille), et parfois un attribut du bien
    ("Première occupation", "logement étudiant" — constatés en conditions
    réelles) plutôt qu'un lieu, auquel cas le vrai lieu reste en tête
    d'Infos ("Lieu - détails")."""

    def test_returns_cp_for_a_known_commune_in_lieu(self):
        self.assertEqual(resolve_seloger_lieu("Lambersart", "3 pièces, 67 m²", "59000"), "59130")

    def test_is_case_insensitive(self):
        self.assertEqual(resolve_seloger_lieu("LAMBERSART", "3 pièces", "59000"), "59130")

    def test_lille_itself_resolves_too(self):
        self.assertEqual(resolve_seloger_lieu("Lille", "1 pièce, 12 m²", "59000"), "59000")

    def test_falls_back_to_infos_prefix_when_lieu_is_not_a_place(self):
        result = resolve_seloger_lieu("Première occupation", "Lambersart - 3 pièces, 67 m²", "59000")
        self.assertEqual(result, "59130")

    def test_falls_back_to_infos_prefix_for_logement_etudiant(self):
        result = resolve_seloger_lieu("logement étudiant", "Lille - 1 pièce, 19 m²", "59000")
        self.assertEqual(result, "59000")

    def test_returns_none_when_lieu_and_infos_prefix_are_both_unresolvable(self):
        result = resolve_seloger_lieu("Première occupation", "Studio meublé - 1 pièce", "59000")
        self.assertIsNone(result)

    def test_returns_none_when_infos_is_missing(self):
        self.assertIsNone(resolve_seloger_lieu("Première occupation", None, "59000"))

    def test_returns_none_when_infos_has_no_separator(self):
        self.assertIsNone(resolve_seloger_lieu("Première occupation", "pas de séparateur ici", "59000"))


class ExtractTypeTest(unittest.TestCase):
    def test_detects_colocation(self):
        self.assertEqual(extract_type("Chambre en Colocation"), "Colocation")

    def test_detects_maison(self):
        self.assertEqual(extract_type("Belle Maison avec jardin"), "Maison")

    def test_detects_studio(self):
        self.assertEqual(extract_type("Studio meublé centre-ville"), "Studio")

    def test_detects_parking(self):
        self.assertEqual(extract_type("Location Garage sécurisé"), "Parking")

    def test_defaults_to_appartement(self):
        self.assertEqual(extract_type("T3 lumineux avec balcon"), "Appartement")

    def test_defaults_to_appartement_for_nan(self):
        self.assertEqual(extract_type(pd.NA), "Appartement")


class FormatDescriptionTest(unittest.TestCase):
    def test_extracts_room_count_prefix(self):
        result = format_description("T3 Lyon 69003 Appartement lumineux avec balcon")
        self.assertTrue(result.startswith("T3"))
        self.assertNotIn("69003", result)
        self.assertNotIn("Lyon", result)

    def test_returns_empty_string_for_nan(self):
        self.assertEqual(format_description(pd.NA), "")

    def test_strips_lille_and_postal_code(self):
        result = format_description("T2 Lille 59800 Appartement lumineux avec balcon")
        self.assertNotIn("59800", result)
        self.assertNotIn("Lille", result)


class LoadDeclaredVillesTest(unittest.TestCase):
    def test_reads_villes_from_scraping_config(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "scraping_config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "ville_active": "lyon",
                    "villes": {
                        "lyon": {"nom": "Lyon", "slug": "lyon"},
                        "lille": {"nom": "Lille", "slug": "lille"},
                    },
                }, f)

            villes = load_declared_villes(config_path)

        self.assertEqual(set(villes.keys()), {"lyon", "lille"})
        self.assertEqual(villes["lille"]["nom"], "Lille")


class ResolveDefaultCpTest(unittest.TestCase):
    def test_returns_the_configured_code_postal_defaut(self):
        cp = resolve_default_cp({"nom": "Lille", "code_postal_defaut": "59000"}, "Lille")

        self.assertEqual(cp, "59000")

    def test_raises_when_code_postal_defaut_is_missing(self):
        # Régression réelle : un repli silencieux vers "69000" (Lyon) pour une
        # ville dont la config oublierait code_postal_defaut mélangerait ses
        # annonces non résolues avec celles de Lyon, sans que rien ne le signale.
        with self.assertRaises(KeyError):
            resolve_default_cp({"nom": "Marseille"}, "Marseille")


class SiteFilesConfigTest(unittest.TestCase):
    def test_builds_filenames_from_slug(self):
        configs = site_files_config("lille")

        filenames = [c['file'] for c in configs]
        self.assertIn("annonces_lille_century21.csv", filenames)
        self.assertIn("annonces_lille_orpi.csv", filenames)
        self.assertEqual(len(configs), 5)


class RunFusionDateDernierScanTest(unittest.TestCase):
    """ORA-134 : la colonne DerniereVue des scrapers doit survivre à la fusion
    sous le nom date_dernier_scan, exploitée ensuite par clean_immo.py pour la
    purge par TTL. run_fusion() boucle maintenant sur toutes les villes
    déclarées dans scraping_config.json (ORA-71) : seul le fichier Lyon est
    présent dans data_dir pour ce test, les autres villes sont silencieusement
    ignorées (fichiers absents), le fichier de sortie combiné n'a donc que la
    ligne Lyon écrite ici."""

    def _write_century21_csv(self, data_dir, rows):
        path = os.path.join(data_dir, "annonces_lyon_century21.csv")
        pd.DataFrame(
            rows, columns=["Titre", "Prix", "Lieu_Surface", "Lien", "Image", "DerniereVue"]
        ).to_csv(path, index=False)

    def test_propagates_derniere_vue_as_date_dernier_scan(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self._write_century21_csv(tmp_dir, [
                ["T2 Lyon 69003 45 m2", "700 €", "45 m2", "https://example.test/1", "", "2026-08-06"],
            ])

            with patch.object(data_fusion, "data_dir", tmp_dir):
                run_fusion()
                result = pd.read_csv(os.path.join(tmp_dir, "base_de_donnees_immo_complet.csv"))

        self.assertIn("date_dernier_scan", result.columns)
        self.assertEqual(result.loc[0, "date_dernier_scan"], "2026-08-06")

    def test_missing_derniere_vue_column_does_not_crash(self):
        # Compat rétroactive : CSV écrit avant l'ajout de la colonne DerniereVue.
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "annonces_lyon_century21.csv")
            pd.DataFrame(
                [["T2 Lyon 69003 45 m2", "700 €", "45 m2", "https://example.test/1", ""]],
                columns=["Titre", "Prix", "Lieu_Surface", "Lien", "Image"],
            ).to_csv(path, index=False)

            with patch.object(data_fusion, "data_dir", tmp_dir):
                run_fusion()
                result = pd.read_csv(os.path.join(tmp_dir, "base_de_donnees_immo_complet.csv"))

        self.assertIn("date_dernier_scan", result.columns)
        self.assertTrue(result["date_dernier_scan"].isna().all())


class RunFusionSelogerLieuTest(unittest.TestCase):
    """ORA-71 POC follow-up : run_fusion() doit résoudre le vrai lieu
    SeLoger (voire exclure l'annonce si introuvable) plutôt que de tout
    regrouper sous le CP générique de la ville."""

    def _write_seloger_csv(self, data_dir, rows):
        path = os.path.join(data_dir, "annonces_lille_seloger.csv")
        pd.DataFrame(
            rows, columns=["Titre", "Prix", "Lieu", "Infos", "Lien", "Image", "DerniereVue"]
        ).to_csv(path, index=False)

    def test_resolves_a_bordering_commune_to_its_own_postal_code(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # surface < 60 : évite le filtre heuristique "colocation probable"
            # (prix < 800 ET surface > 60) sur run_fusion(), sans rapport
            # avec ce qui est testé ici.
            self._write_seloger_csv(tmp_dir, [
                ["Appartement à louer", "700 €", "Lambersart", "3 pièces, 45 m²",
                 "https://example.test/1", "", "2026-08-06"],
            ])

            with patch.object(data_fusion, "data_dir", tmp_dir):
                run_fusion()
                result = pd.read_csv(os.path.join(tmp_dir, "base_de_donnees_immo_complet.csv"))

        self.assertEqual(len(result), 1)
        self.assertEqual(str(result.loc[0, "code_postal"]), "59130")

    def test_drops_the_row_when_no_place_is_resolvable_anywhere(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self._write_seloger_csv(tmp_dir, [
                ["Studio à louer", "500 €", "Première occupation", "Studio meublé - 1 pièce, 18 m²",
                 "https://example.test/2", "", "2026-08-06"],
            ])

            with patch.object(data_fusion, "data_dir", tmp_dir):
                run_fusion()
                result = pd.read_csv(os.path.join(tmp_dir, "base_de_donnees_immo_complet.csv"))

        self.assertEqual(len(result), 0)


class RunFusionPerVilleTest(unittest.TestCase):
    """ORA-153 : chaque DAG annonces tourne désormais indépendamment par
    ville. run_fusion(ville_slug) ne doit retraiter QUE cette ville, sans
    écraser les annonces des autres villes déjà présentes dans le fichier
    combiné (comportement historique de run_fusion() sans argument : toutes
    les villes déclarées sont reconstruites depuis zéro à chaque appel)."""

    def _write_century21_csv(self, data_dir, slug, rows):
        path = os.path.join(data_dir, f"annonces_{slug}_century21.csv")
        pd.DataFrame(
            rows, columns=["Titre", "Prix", "Lieu_Surface", "Lien", "Image", "DerniereVue"]
        ).to_csv(path, index=False)

    def test_partial_fusion_preserves_other_villes_already_present(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self._write_century21_csv(tmp_dir, "lyon", [
                ["T2 Lyon 69003 45 m2", "700 €", "45 m2", "https://example.test/lyon1", "", "2026-08-06"],
            ])
            self._write_century21_csv(tmp_dir, "lille", [
                ["T2 Lille 59000 40 m2", "650 €", "40 m2", "https://example.test/lille1", "", "2026-08-06"],
            ])

            with patch.object(data_fusion, "data_dir", tmp_dir):
                run_fusion()
                run_fusion("lille")
                result = pd.read_csv(os.path.join(tmp_dir, "base_de_donnees_immo_complet.csv"))

        self.assertEqual(set(result["ville"]), {"Lyon", "Lille"})
        self.assertEqual(len(result), 2)

    def test_partial_fusion_replaces_stale_rows_of_the_targeted_ville_only(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            self._write_century21_csv(tmp_dir, "lyon", [
                ["T2 Lyon 69003 45 m2", "700 €", "45 m2", "https://example.test/lyon1", "", "2026-08-06"],
            ])
            self._write_century21_csv(tmp_dir, "lille", [
                ["T2 Lille 59000 40 m2", "650 €", "40 m2", "https://example.test/lille-old", "", "2026-08-06"],
            ])

            with patch.object(data_fusion, "data_dir", tmp_dir):
                run_fusion()

                # L'annonce Lille "old" n'est plus scrapée (retirée du site) ;
                # une nouvelle la remplace au run partiel Lille suivant, sans
                # toucher à Lyon.
                os.remove(os.path.join(tmp_dir, "annonces_lille_century21.csv"))
                self._write_century21_csv(tmp_dir, "lille", [
                    ["T2 Lille 59000 42 m2", "660 €", "42 m2", "https://example.test/lille-new", "", "2026-08-07"],
                ])
                run_fusion("lille")

                result = pd.read_csv(os.path.join(tmp_dir, "base_de_donnees_immo_complet.csv"))

        self.assertEqual(set(result["url"]), {"https://example.test/lyon1", "https://example.test/lille-new"})


if __name__ == "__main__":
    unittest.main()
