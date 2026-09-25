import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.adresse_texte import extraire_adresse, localiser_adresse


class AdresseDuBienTest(unittest.TestCase):
    def assertAdresse(self, texte, attendu):
        self.assertEqual(extraire_adresse(texte)[0], attendu, texte)

    def test_adresse_avec_numero(self):
        self.assertAdresse("Idéalement situé au 14 rue Lavoisier, au cœur du 3ème", "14 rue Lavoisier")
        self.assertAdresse("T2 - 24 rue d'Essling 69003 LYON. Ce T3", "24 rue d'Essling")
        self.assertAdresse("Lyon 7 - 26 rue Jean François Raclet. Appartement meublé", "26 rue Jean François Raclet")
        self.assertAdresse("appartement au 8 Bis rue Hugues Guérin à Lyon", "8 Bis rue Hugues Guérin")

    def test_numero_separe_par_une_virgule(self):
        self.assertAdresse("62, rue Chevreul (angle rue Elie Rochette) 69007 Lyon", "62 rue Chevreul")

    def test_rue_sans_numero_seulement_si_situee(self):
        self.assertAdresse("appartement de type 2, situé rue Félix Brun, dans une résidence", "rue Félix Brun")
        self.assertAdresse("A LOUER APPARTEMENT T4 (rue Maryse Bastié 69008 Lyon) PINEL", "rue Maryse Bastié")

    def test_bruit_apres_le_nom_est_coupe(self):
        self.assertAdresse("112 rue Professeur Beauvisage BAT B , LYON 8", "112 rue Professeur Beauvisage")
        self.assertAdresse("172 rue Marcel Mérieux-LYON-69007", "172 rue Marcel Mérieux")
        self.assertAdresse("rue Domremy- Spacieux T3", "rue Domremy")

    def test_reperes_refuses(self):
        for texte in [
            "à proximité de la rue Garibaldi et du métro",
            "à deux pas de la place Bellecour",
            "situé derrière l'hôpital, à 5 minutes de la rue Paul Bert",
            "au pied de la place Bir-Hakeim. Disponible de suite",
            "hors rue Victor Hugo",
        ]:
            self.assertAdresse(texte, None)

    def test_adresse_agence_refusee(self):
        self.assertAdresse("Votre cabinet vous accueille au 3 rue Zola. Bel appartement", None)
        self.assertAdresse("Honoraires à la charge du locataire. Agence : 12 rue des Lilas", None)

    def test_place_sans_numero_est_un_repere(self):
        self.assertAdresse("situé place Bellecour", None)
        self.assertAdresse("appartement au 4 place d'Ainay", "4 place d'Ainay")

    def test_deux_adresses_differentes_donnent_une_contradiction(self):
        adresse, raison = extraire_adresse("au 3 rue Zola. Parking au 9 rue Hugo")
        self.assertIsNone(adresse)
        self.assertTrue(raison.startswith("contradiction"))

    def test_adresse_avec_numero_prime_sur_rue_seule(self):
        self.assertAdresse("situé rue Zola. Il se trouve au 3 rue Zola", "3 rue Zola")

    def test_textes_vides(self):
        for t in (None, "", "   ", float("nan")):
            self.assertEqual(extraire_adresse(t)[0], None)

    def test_localiser_adresse_premier_texte_qui_decide(self):
        self.assertEqual(localiser_adresse(["", "Lyon 3e", "au 14 rue Lavoisier"])[0], "14 rue Lavoisier")
        self.assertEqual(localiser_adresse(["au 3 rue Zola. au 9 rue Hugo", "au 14 rue Lavoisier"])[0], None)


if __name__ == "__main__":
    unittest.main()
