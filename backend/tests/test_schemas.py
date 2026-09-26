import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schemas import (
    CavaliersRequestSchema,
    ChatRequestSchema,
    PredictRequestSchema,
    QuartierStatsRequestSchema,
    ValidationError,
)


class ChatRequestSchemaTest(unittest.TestCase):
    def test_accepts_a_valid_payload(self):
        payload = ChatRequestSchema(message="Que vaut un T2 à Gerland ?", context="Quartier: Gerland")
        self.assertEqual(payload.message, "Que vaut un T2 à Gerland ?")
        self.assertEqual(payload.context, "Quartier: Gerland")

    def test_context_is_optional(self):
        payload = ChatRequestSchema(message="Salut")
        self.assertEqual(payload.context, "")

    def test_rejects_blank_message(self):
        with self.assertRaises(ValidationError):
            ChatRequestSchema(message="   ")

    def test_rejects_missing_message(self):
        with self.assertRaises(ValidationError):
            ChatRequestSchema()

    def test_rejects_non_string_message(self):
        with self.assertRaises(ValidationError):
            ChatRequestSchema(message=["not", "a", "string"])


class QuartierStatsRequestSchemaTest(unittest.TestCase):
    def test_accepts_a_valid_payload(self):
        payload = QuartierStatsRequestSchema(quartier="Gerland", type_local="T2")
        self.assertEqual(payload.quartier, "Gerland")
        self.assertEqual(payload.type_local, "T2")

    def test_type_local_defaults_to_tout(self):
        payload = QuartierStatsRequestSchema(quartier="Gerland")
        self.assertEqual(payload.type_local, "Tout")

    def test_rejects_blank_quartier(self):
        with self.assertRaises(ValidationError):
            QuartierStatsRequestSchema(quartier="  ")

    def test_rejects_non_string_quartier(self):
        with self.assertRaises(ValidationError):
            QuartierStatsRequestSchema(quartier={"nested": "object"})

    def test_ville_is_optional_and_defaults_to_none(self):
        payload = QuartierStatsRequestSchema(quartier="Gerland")
        self.assertIsNone(payload.ville)

    def test_accepts_a_ville(self):
        payload = QuartierStatsRequestSchema(quartier="Gerland", ville="lyon")
        self.assertEqual(payload.ville, "lyon")


class PredictRequestSchemaTest(unittest.TestCase):
    def test_accepts_a_valid_payload(self):
        payload = PredictRequestSchema(surface=45, quartier="Gerland", type_local="T2")
        self.assertEqual(payload.surface, 45.0)

    def test_accepts_an_empty_payload_leaving_semantic_validation_to_the_route(self):
        payload = PredictRequestSchema()
        self.assertIsNone(payload.surface)
        self.assertIsNone(payload.quartier)

    def test_rejects_non_numeric_surface(self):
        with self.assertRaises(ValidationError):
            PredictRequestSchema(surface="pas un nombre", quartier="Gerland", type_local="T2")

    def test_rejects_quartier_shaped_as_a_list(self):
        with self.assertRaises(ValidationError):
            PredictRequestSchema(quartier=["Gerland"], type_local="T2", surface=45)


class CavaliersRequestSchemaTest(unittest.TestCase):
    def test_accepts_a_valid_payload(self):
        payload = CavaliersRequestSchema(lat="45.75", lng="4.83", ville="lyon", rayon_m="300")
        self.assertEqual(payload.lat, 45.75)
        self.assertEqual(payload.lng, 4.83)
        self.assertEqual(payload.rayon_m, 300)

    def test_rayon_m_defaults_to_500(self):
        payload = CavaliersRequestSchema(lat=45.75, lng=4.83, ville="lyon")
        self.assertEqual(payload.rayon_m, 500)

    def test_rejects_a_rayon_m_outside_300_500_1000(self):
        with self.assertRaises(ValidationError):
            CavaliersRequestSchema(lat=45.75, lng=4.83, ville="lyon", rayon_m=400)

    def test_rejects_missing_lat(self):
        with self.assertRaises(ValidationError):
            CavaliersRequestSchema(lng=4.83, ville="lyon")

    def test_rejects_missing_ville(self):
        with self.assertRaises(ValidationError):
            CavaliersRequestSchema(lat=45.75, lng=4.83)

    def test_rejects_blank_ville(self):
        with self.assertRaises(ValidationError):
            CavaliersRequestSchema(lat=45.75, lng=4.83, ville="   ")

    def test_rayon_m_none_string_means_no_radius(self):
        """Rayon "Aucun" (ORA-183, v3) : le sélecteur segmenté envoie la
        valeur "none" (query string GET, toujours une chaîne) pour demander
        les totaux à l'échelle de la ville plutôt qu'un rayon précis."""
        payload = CavaliersRequestSchema(lat=45.75, lng=4.83, ville="lyon", rayon_m="none")
        self.assertIsNone(payload.rayon_m)

    def test_rayon_m_none_string_is_case_insensitive(self):
        payload = CavaliersRequestSchema(lat=45.75, lng=4.83, ville="lyon", rayon_m="NONE")
        self.assertIsNone(payload.rayon_m)

    def test_rayon_m_python_none_is_also_accepted(self):
        payload = CavaliersRequestSchema(lat=45.75, lng=4.83, ville="lyon", rayon_m=None)
        self.assertIsNone(payload.rayon_m)

    def test_absent_rayon_m_still_defaults_to_500_not_none(self):
        """Non-régression : seul un "none" explicite retire le rayon — un
        appel qui omet rayon_m garde le comportement historique (500m)."""
        payload = CavaliersRequestSchema(lat=45.75, lng=4.83, ville="lyon")
        self.assertEqual(payload.rayon_m, 500)


if __name__ == "__main__":
    unittest.main()
