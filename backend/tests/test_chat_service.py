import os
import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.chat_service import ChatService


class FakeModels:
    def __init__(self, text="Réponse Gemini"):
        self.text = text
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(text=self.text)


class FakeClient:
    instances = []

    def __init__(self, api_key):
        self.api_key = api_key
        self.models = FakeModels()
        FakeClient.instances.append(self)


class ChatServiceTest(unittest.TestCase):
    def setUp(self):
        FakeClient.instances = []

    def _fake_google_modules(self):
        google_module = types.ModuleType("google")
        genai_module = types.ModuleType("google.genai")
        genai_module.Client = FakeClient
        genai_module.types = types.SimpleNamespace(
            GenerateContentConfig=lambda **kwargs: types.SimpleNamespace(**kwargs)
        )
        google_module.genai = genai_module
        return {
            "google": google_module,
            "google.genai": genai_module,
        }

    def test_returns_clean_error_when_gemini_key_is_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            service = ChatService()

            response = service.get_response("Quel prix à Gerland ?", "", pd.DataFrame())

        self.assertIn("configuration IA", response)
        self.assertEqual(FakeClient.instances, [])

    def test_calls_gemini_with_configured_model_and_generation_settings(self):
        df = pd.DataFrame()
        env = {
            "GEMINI_API_KEY": "test-key",
            "GEMINI_MODEL": "gemini-test",
            "GEMINI_MAX_OUTPUT_TOKENS": "321",
            "GEMINI_TEMPERATURE": "0.25",
        }

        with patch.dict(os.environ, env, clear=True), patch.dict(sys.modules, self._fake_google_modules()):
            service = ChatService()
            response = service.get_response("Explique ta méthode", "", df)

        self.assertEqual(response, "Réponse Gemini")
        self.assertEqual(FakeClient.instances[0].api_key, "test-key")
        call = FakeClient.instances[0].models.calls[0]
        self.assertEqual(call["model"], "gemini-test")
        self.assertIn("Explique ta méthode", call["contents"])
        self.assertEqual(call["config"].max_output_tokens, 321)
        self.assertEqual(call["config"].temperature, 0.25)
        self.assertIn("Immotep", call["config"].system_instruction)

    def test_limits_rag_context_to_a_small_number_of_relevant_listings(self):
        df = pd.DataFrame(
            [
                {
                    "id_annonce": index,
                    "quartier": "Gerland" if index < 12 else "Part-Dieu",
                    "prix": 700 + index,
                    "surface": 20 + index,
                    "type_local": "T1",
                }
                for index in range(20)
            ]
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            service = ChatService()
            contents = service._format_listings(df, quartier_filter="Gerland", user_message="Des exemples ?")

        listing_lines = [
            line
            for line in contents.splitlines()
            if line.strip().startswith("- ") and " EUR" in line and " | " in line
        ]
        self.assertLessEqual(len(listing_lines), 12)
        self.assertTrue(all("Gerland" in line for line in listing_lines))

    def test_retrieves_lyon_arrondissement_and_quality_signals_from_user_message(self):
        df = pd.DataFrame(
            [
                {
                    "id_annonce": 1,
                    "quartier": "Gerland",
                    "code_postal": 69007,
                    "prix": 790,
                    "surface": 22,
                    "type_local": "T1",
                    "description": "Petit studio proche bars.",
                    "nb_vice_bar_500m": 12,
                },
                {
                    "id_annonce": 2,
                    "quartier": "Lyon 3ème",
                    "code_postal": 69003,
                    "prix": 940,
                    "surface": 52,
                    "type_local": "T2",
                    "description": "Appartement très calme. Proximité tous commerces, superU à 50M.",
                    "nb_vice_bar_500m": 1,
                    "dist_vice_bar": 650,
                    "nb_nuisance_discothèque_500m": 0,
                    "dist_nuisance_discothèque": 1200,
                },
            ]
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            service = ChatService()
            postal = service._extract_postal_code(
                "",
                "Je veux un appart à Lyon 3 sans trop de bruit avec un supermarché pas loin",
            )
            contents = service._format_listings(
                df,
                postal_code=postal,
                user_message="Je veux un appart à Lyon 3 sans trop de bruit avec un supermarché pas loin",
            )

        self.assertIn("Lyon 3ème", contents)
        self.assertIn("superU", contents)
        self.assertIn("calme", contents)
        self.assertIn("bars 500m: 1", contents)
        self.assertNotIn("Gerland", contents)

    def test_returns_structured_compare_result_for_two_neighborhoods(self):
        df = pd.DataFrame(
            [
                {
                    "id_annonce": 1,
                    "quartier": "Ainay",
                    "code_postal": 69002,
                    "prix": 980,
                    "surface": 42,
                    "prix_m2": 23.3,
                    "type_local": "T2",
                    "latitude": 45.753,
                    "longitude": 4.829,
                    "description": "T2 calme proche commerces.",
                    "nb_vice_bar_500m": 2,
                },
                {
                    "id_annonce": 2,
                    "quartier": "Ainay",
                    "code_postal": 69002,
                    "prix": 1120,
                    "surface": 50,
                    "prix_m2": 22.4,
                    "type_local": "T2",
                    "latitude": 45.754,
                    "longitude": 4.83,
                    "description": "T2 lumineux.",
                    "nb_vice_bar_500m": 3,
                },
                {
                    "id_annonce": 3,
                    "quartier": "Part-Dieu",
                    "code_postal": 69003,
                    "prix": 1250,
                    "surface": 48,
                    "prix_m2": 26.0,
                    "type_local": "T2",
                    "latitude": 45.761,
                    "longitude": 4.858,
                    "description": "T2 vers Part-Dieu.",
                    "nb_vice_bar_500m": 6,
                },
            ]
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True), patch.dict(
            sys.modules, self._fake_google_modules()
        ):
            service = ChatService()
            result = service.get_chat_result("Compare moi un T2 à Ainay et à Part-Dieu en terme de prix", "", df)

        self.assertEqual(result["intent"], "compare")
        self.assertEqual(result["parsed"]["type_local"], "T2")
        self.assertEqual(result["parsed"]["locations"], ["Part-Dieu", "Ainay"])
        self.assertEqual(len(result["comparisons"]), 2)
        self.assertEqual(result["comparisons"][0]["quartier"], "Ainay")
        self.assertEqual(result["comparisons"][0]["prix_moyen"], 1050)
        self.assertEqual(result["comparisons"][1]["quartier"], "Part-Dieu")
        self.assertEqual(result["map_focus"]["quartier"], "Ainay")
        self.assertGreaterEqual(len(result["recommendations"]), 2)

    def test_returns_structured_compare_result_for_two_arrondissements(self):
        df = pd.DataFrame(
            [
                {
                    "quartier": "Ainay",
                    "code_postal": 69002,
                    "prix": 900,
                    "surface": 40,
                    "type_local": "T2",
                    "latitude": 45.753,
                    "longitude": 4.829,
                },
                {
                    "quartier": "Brotteaux",
                    "code_postal": 69006,
                    "prix": 1200,
                    "surface": 45,
                    "type_local": "T2",
                    "latitude": 45.766,
                    "longitude": 4.852,
                },
            ]
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True), patch.dict(
            sys.modules, self._fake_google_modules()
        ):
            service = ChatService()
            result = service.get_chat_result("compare Lyon 2 et Lyon 6 pour un T2", "", df)

        self.assertEqual(result["intent"], "compare")
        self.assertEqual(result["parsed"]["postal_codes"], [69002, 69006])
        self.assertEqual(result["parsed"]["locations"], ["Lyon 2", "Lyon 6"])
        self.assertEqual(len(result["comparisons"]), 2)
        self.assertEqual({item["quartier"] for item in result["comparisons"]}, {"Lyon 2", "Lyon 6"})
        self.assertIn("Lyon 6", result["response"])
        self.assertIn("1200", result["response"])

    def test_follow_up_can_use_previous_context_and_multiple_types(self):
        df = pd.DataFrame(
            [
                {
                    "quartier": "Montchat",
                    "code_postal": 69003,
                    "prix": 900,
                    "surface": 42,
                    "type_local": "T2",
                    "latitude": 45.75,
                    "longitude": 4.88,
                    "nb_vice_bar_500m": 1,
                },
                {
                    "quartier": "Montchat",
                    "code_postal": 69003,
                    "prix": 1100,
                    "surface": 60,
                    "type_local": "T3",
                    "latitude": 45.751,
                    "longitude": 4.881,
                    "nb_vice_bar_500m": 1,
                },
                {
                    "quartier": "Ainay",
                    "code_postal": 69002,
                    "prix": 980,
                    "surface": 42,
                    "type_local": "T2",
                    "latitude": 45.753,
                    "longitude": 4.829,
                },
            ]
        )
        context = "Conversation précédente: Lyon 3. Code postal: 69003. Préférences: quiet, shops."

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True), patch.dict(
            sys.modules, self._fake_google_modules()
        ):
            service = ChatService()
            result = service.get_chat_result("je suis plus chaud d'un t2 voir un t3", context, df)

        self.assertEqual(result["parsed"]["postal_code"], 69003)
        self.assertEqual(result["parsed"]["type_locals"], ["T2", "T3"])
        self.assertEqual({item["type_local"] for item in result["recommendations"]}, {"T2", "T3"})
        self.assertTrue(all(item["quartier"] == "Montchat" for item in result["recommendations"]))

    def test_bar_near_preference_prioritizes_nearby_bars(self):
        df = pd.DataFrame(
            [
                {
                    "quartier": "Montchat",
                    "code_postal": 69003,
                    "prix": 850,
                    "surface": 55,
                    "type_local": "T3",
                    "latitude": 45.75,
                    "longitude": 4.88,
                    "nb_vice_bar_500m": 0,
                    "dist_vice_bar": 900,
                },
                {
                    "quartier": "Part-Dieu / Villette",
                    "code_postal": 69003,
                    "prix": 950,
                    "surface": 58,
                    "type_local": "T3",
                    "latitude": 45.761,
                    "longitude": 4.858,
                    "nb_vice_bar_500m": 5,
                    "dist_vice_bar": 120,
                },
            ]
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True), patch.dict(
            sys.modules, self._fake_google_modules()
        ):
            service = ChatService()
            result = service.get_chat_result("T3 à Lyon 3 avec un bar pas loin", "", df)

        self.assertIn("bar_near", result["parsed"]["preferences"])
        self.assertEqual(result["recommendations"][0]["quartier"], "Part-Dieu / Villette")
        self.assertIn("bar", result["recommendations"][0]["why"])

    def test_returns_professional_message_on_provider_timeout(self):
        class TimeoutModels(FakeModels):
            def generate_content(self, **kwargs):
                raise TimeoutError("provider timed out")

        class TimeoutClient(FakeClient):
            def __init__(self, api_key):
                self.api_key = api_key
                self.models = TimeoutModels()
                FakeClient.instances.append(self)

        modules = self._fake_google_modules()
        modules["google.genai"].Client = TimeoutClient

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True), patch.dict(sys.modules, modules):
            service = ChatService()
            response = service.get_response("Bonjour", "", pd.DataFrame())

        self.assertIn("trop de temps", response)


if __name__ == "__main__":
    unittest.main()
