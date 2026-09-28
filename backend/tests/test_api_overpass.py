import json
import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from api_overpass import fetch_elements, merge_cavaliers, resolve_active_city_name, resolve_city_name


def _row(lat, lon, type_osm, categorie, nom):
    return {
        'categorie_cavalier': categorie,
        'type_osm': type_osm,
        'nom_lieu': nom,
        'latitude': lat,
        'longitude': lon,
    }


class MergeCavaliersTest(unittest.TestCase):
    def test_strictly_identical_row_is_deduplicated(self):
        df_old = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Le Zinc")])
        df_new = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Le Zinc")])

        result = merge_cavaliers(df_old, df_new)

        self.assertEqual(len(result), 1)

    def test_recategorized_poi_is_not_silently_lost(self):
        df_old = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Le Zinc")])
        # Même point OSM (lat/lon), mais ré-étiqueté sous une autre catégorie/nom
        df_new = pd.DataFrame([_row(45.75, 4.85, "bar", "Gentrification - Torréfacteur", "Le Zinc Café")])

        result = merge_cavaliers(df_old, df_new)

        self.assertEqual(len(result), 2)
        self.assertIn("Vice - Bar", result['categorie_cavalier'].values)
        self.assertIn("Gentrification - Torréfacteur", result['categorie_cavalier'].values)

    def test_renamed_poi_keeps_both_versions_when_only_name_changes(self):
        df_old = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Ancien Nom")])
        df_new = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Nouveau Nom")])

        result = merge_cavaliers(df_old, df_new)

        # Nom différent => clé différente => les deux versions sont conservées,
        # conformément au comportement documenté (pas de perte silencieuse).
        self.assertEqual(len(result), 2)

    def test_unrelated_pois_are_all_kept(self):
        df_old = pd.DataFrame([_row(45.75, 4.85, "bar", "Vice - Bar", "Le Zinc")])
        df_new = pd.DataFrame([_row(45.76, 4.86, "kebab", "Vice - Kebab", "Chez Ali")])

        result = merge_cavaliers(df_old, df_new)

        self.assertEqual(len(result), 2)


class ResolveActiveCityNameTest(unittest.TestCase):
    def test_resolves_name_of_the_currently_active_city(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "scraping_config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "ville_active": "lyon",
                    "villes": {"lyon": {"nom": "Lyon", "slug": "lyon"}},
                }, f)

            self.assertEqual(resolve_active_city_name(config_path), "Lyon")

    def test_switching_active_city_requires_no_code_change(self):
        """ORA-71 (AC#1) : ajouter une ville en config (même fictive) et basculer
        `ville_active` dessus suffit à changer la ville résolue par ce script,
        sans toucher au code Python."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "scraping_config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "ville_active": "villefictivetest",
                    "villes": {
                        "lyon": {"nom": "Lyon", "slug": "lyon"},
                        "villefictivetest": {"nom": "VilleFictiveTest", "slug": "villefictivetest"},
                    },
                }, f)

            self.assertEqual(resolve_active_city_name(config_path), "VilleFictiveTest")


class ResolveCityNameTest(unittest.TestCase):
    """ORA-153 : resolve_city_name(slug) cible explicitement une ville, sans
    dépendre ni modifier `ville_active` — chaque DAG cavaliers par ville
    passe son propre slug plutôt que de mutualiser un réglage global partagé
    entre villes (jusqu'ici modifié à la main entre deux scrapes)."""

    def test_resolves_a_given_ville_regardless_of_ville_active(self):
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

            self.assertEqual(resolve_city_name("lille", config_path), "Lille")
            self.assertEqual(resolve_city_name("lyon", config_path), "Lyon")


if __name__ == "__main__":
    unittest.main()


class _Resp:
    def __init__(self, status, elements=None):
        self.status_code = status
        self._elements = elements or []

    def json(self):
        return {"elements": self._elements}


class FetchElementsTest(unittest.TestCase):
    """Overpass sature souvent (429/504) : on réessaie le serveur principal
    avec une attente croissante au lieu de basculer sur des miroirs morts qui
    bloquaient chacun jusqu'au timeout (DAG Lille tué à 45 min, 2026-09-28)."""

    def _run(self, outcomes):
        calls, sleeps = iter(outcomes), []

        def get(*args, **kwargs):
            outcome = next(calls)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        return fetch_elements("q", get=get, sleep=sleeps.append), sleeps

    def test_retries_with_growing_backoff_until_success(self):
        elements, sleeps = self._run([_Resp(429), OSError("timeout"), _Resp(200, [{"id": 1}])])

        self.assertEqual(elements, [{"id": 1}])
        self.assertEqual(sleeps, [15, 30])

    def test_gives_up_after_four_attempts(self):
        elements, sleeps = self._run([_Resp(504)] * 4)

        self.assertIsNone(elements)
        self.assertEqual(sleeps, [15, 30, 60])
