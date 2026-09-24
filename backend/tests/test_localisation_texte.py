import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.localisation_texte import extraire_zone, localiser_par_texte

# (texte, ville, zone attendue ou None)
CAS = [
    # --- ACCEPTER ---
    ("Bel appartement situé à Perrache, lumineux.", "lyon", "69002"),
    ("Appartement quartier Confluence, 3 pièces", "lyon", "69002"),
    ("T2 meublé Lyon 3e, proche commerces", "lyon", "69003"),
    ("Studio Lyon 3ème rénové", "lyon", "69003"),
    ("Studio Lyon 3eme rénové", "lyon", "69003"),
    ("Appartement Lyon III lumineux", "lyon", "69003"),
    ("Lyon 1er, pentes de la Croix-Rousse", "lyon", "69001"),
    ("Appartement dans le 8ème arrondissement", "lyon", "69008"),
    ("Lyon 02. Studio meublé de 25 m²", "lyon", "69002"),
    ("Pied-à-terre meublé au coeur de Montchat", "lyon", "69003"),
    ("Charmant T3 au coeur du Vieux Lyon", "lyon", "69005"),
    ("Vieux-Lille : appartement de charme", "lille", "Vieux-Lille"),
    ("Appartement dans le quartier de Wazemmes", "lille", "Wazemmes"),
    ("Studio situé à Fives, refait à neuf", "lille", "Fives"),
    ("Appartement situé dans le quartier Vauban-Esquermes", "lille", "Vauban-Esquermes"),
    ("Proche métro, situé à Hellemmes", "lille", "Hellemmes"),
    ("Résidence sécurisée à Lomme", "lille", "Lomme"),
    ("Situé à Fives. Idéal étudiant, à 5 min du Vieux-Lille", "lille", "Fives"),
    # --- REFUSER : proximité / distance / comparaison ---
    ("Appartement proche Perrache", "lyon", None),
    ("Studio à côté de la Part-Dieu", "lyon", None),
    ("T2 à 5 min du Vieux-Lille", "lille", None),
    ("Appartement à proximité de Wazemmes", "lille", None),
    ("Situé à deux pas de Fives", "lille", None),
    ("Appartement en bordure de Confluence", "lyon", None),
    ("Proche des transports, commerces et écoles, Wazemmes", "lille", None),
    # --- REFUSER : négation ---
    ("Appartement hors Vieux-Lille", "lille", None),
    ("Ce n'est pas à Fives mais plus calme", "lille", None),
    # --- REFUSER : repère (rue, station, commerce, école) ---
    ("Appartement rue de Wazemmes", "lille", None),
    ("Métro Wazemmes à 2 pas", "lille", None),
    ("Près du marché de Wazemmes", "lille", None),
    ("Appartement, gare Part-Dieu accessible à pied", "lyon", None),
    ("Agence Century 21, 12 rue Vendôme 69003 Lyon, vous propose ce T2", "lyon", None),
    # --- REFUSER : contradiction / ambigu / vide ---
    ("Situé à Fives, quartier Wazemmes", "lille", None),
    ("Appartement Lyon 3e, ou Lyon 7e selon les envies", "lyon", None),
    ("Appartement près de la Croix-Rousse", "lyon", None),
    ("Bel appartement lumineux, 3 pièces", "lille", None),
    ("", "lille", None),
    (None, "lyon", None),
    ("Lyon 3 pièces refait à neuf", "lyon", None),
    # --- cohérence ville : un quartier d'une autre ville ne compte pas ---
    ("Appartement situé à Wazemmes", "lyon", None),
    ("Appartement situé à Perrache", "lille", None),
    ("Appartement situé à Fives", None, None),
]


class ExtraireZoneTest(unittest.TestCase):
    def test_cas(self):
        for texte, ville, attendu in CAS:
            with self.subTest(texte=texte, ville=ville):
                zone, raison = extraire_zone(texte, ville)
                self.assertEqual(zone, attendu, raison)
                self.assertTrue(raison)

    def test_au_moins_25_phrases(self):
        self.assertGreaterEqual(len(CAS), 25)

    def test_proche_perrache_ne_place_jamais_a_perrache(self):
        self.assertIsNone(extraire_zone("Studio proche Perrache", "lyon")[0])

    def test_premier_texte_qui_decide(self):
        # « proche Fives » ne décide pas : on passe au texte suivant.
        self.assertEqual(localiser_par_texte(["", "Proche Fives", "Situé à Fives"], "lille")[0], "Fives")

    def test_contradiction_bloque_le_repli_sur_le_texte_suivant(self):
        zone, raison = localiser_par_texte(["Situé à Fives, quartier Wazemmes", "Situé à Fives"], "lille")
        self.assertIsNone(zone)
        self.assertIn("contradiction", raison)


if __name__ == "__main__":
    unittest.main()
