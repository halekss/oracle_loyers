import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd

from scripts import clean_immo

SLUG_URL = "https://www.seloger.com/annonces/locations/appartement/lille-59/moulins/265435343.htm"
QUARTIERS_LYON_3 = {"Montchat", "Préfecture / Quais", "Part-Dieu / Villette"}


def _sans_reseau(adresse, postcode=None):
    return None


def _geocode(geocodeur=_sans_reseau, **champs):
    """Une annonce, colonnes par défaut vides ; renvoie le df après step_geocoding."""
    ligne = {
        "code_postal": "69000", "ville": "Lyon", "url": "https://x/1",
        "latitude": None, "longitude": None,
        "description_detail": "", "description_raw": "", "description": "",
    }
    ligne.update(champs)
    return clean_immo.step_geocoding(pd.DataFrame([ligne]), geocodeur=geocodeur)


def _geocodeur(cp="69007", precision="numero", lat=45.731, lon=4.832):
    appels = []

    def faux(adresse, postcode=None):
        appels.append((adresse, postcode))
        return {"lat": lat, "lon": lon, "precision": precision, "cp": cp}
    faux.appels = appels
    return faux


class AdresseGeocodeeTest(unittest.TestCase):
    def test_adresse_prime_sur_le_cp_sans_jitter(self):
        g = _geocodeur()
        df = _geocode(g, code_postal="69007", description_detail="Situé au 52 rue André Bollier")
        r = df.iloc[0]
        self.assertEqual(r["source_localisation"], "adresse")
        self.assertEqual(r["precision_localisation"], "numero")
        self.assertEqual((r["latitude"], r["longitude"]), (45.731, 4.832))
        self.assertTrue(r["sur_carte"])
        self.assertEqual(g.appels, [("52 rue André Bollier", "69007")])

    def test_gps_prime_sur_l_adresse(self):
        g = _geocodeur()
        r = _geocode(g, latitude=45.75, longitude=4.85, description_detail="au 52 rue André Bollier").iloc[0]
        self.assertEqual(r["source_localisation"], "gps")
        self.assertEqual(g.appels, [])

    def test_cp_ambigu_prend_l_arrondissement_de_l_adresse(self):
        df = _geocode(_geocodeur(cp="69003", lat=45.76, lon=4.89), description_detail="au 14 rue Lavoisier")
        self.assertEqual(df.iloc[0]["source_localisation"], "adresse")
        self.assertEqual(clean_immo.step_quartiers(df).iloc[0]["quartier"], "Montchat")

    def test_cp_incoherent_rejete_et_retombe_sur_le_cp(self):
        df = _geocode(_geocodeur(cp="69003"), code_postal="69007", description_detail="au 14 rue Lavoisier")
        r = df.iloc[0]
        self.assertEqual(r["source_localisation"], "cp")
        self.assertEqual(r["precision_localisation"], "")

    def test_geocodage_en_echec_retombe_sur_la_regle_suivante(self):
        r = _geocode(_sans_reseau, description_detail="Studio Lyon 3e, au 14 rue Lavoisier").iloc[0]
        self.assertEqual(r["source_localisation"], "texte")

    def test_repere_ou_agence_jamais_geocodes(self):
        g = _geocodeur()
        for texte in ["à deux pas de la rue Paul Bert", "Votre agence, 3 rue Zola, vous accueille"]:
            _geocode(g, description_detail=texte)
        self.assertEqual(g.appels, [])

    def test_precision_rue_conservee(self):
        r = _geocode(_geocodeur(precision="rue"), description_detail="situé rue Félix Brun").iloc[0]
        self.assertEqual((r["source_localisation"], r["precision_localisation"]), ("adresse", "rue"))

    def test_lille_non_geocode(self):
        g = _geocodeur()
        _geocode(g, code_postal="59000", ville="Lille", description_detail="au 3 rue Nationale")
        self.assertEqual(g.appels, [])


class OrdrePrioriteLocalisationTest(unittest.TestCase):
    def test_gps_prime_sur_le_texte_et_le_cp(self):
        r = _geocode(latitude=45.75, longitude=4.85, code_postal="69007",
                     description_detail="Situé à Perrache").iloc[0]
        self.assertEqual(r["source_localisation"], "gps")
        self.assertAlmostEqual(r["latitude"], 45.75)
        self.assertAlmostEqual(r["longitude"], 4.85)
        self.assertTrue(r["sur_carte"])

    def test_cp_fiable_prime_sur_le_texte(self):
        df = _geocode(code_postal="69007", description_detail="Situé à Perrache")
        self.assertEqual(df.iloc[0]["source_localisation"], "cp")
        self.assertTrue(df.iloc[0]["sur_carte"])
        self.assertIn(clean_immo.step_quartiers(df).iloc[0]["quartier"],
                      {"Gerland", "Guillotière / Jean Macé"})

    def test_slug_url_seloger_prime_sur_le_texte(self):
        r = _geocode(code_postal="59000", ville="Lille", url=SLUG_URL,
                     description_detail="Situé à Fives").iloc[0]
        self.assertEqual(r["source_localisation"], "url")
        self.assertTrue(r["sur_carte"])

    def test_cp_ambigu_plus_mention_explicite_donne_texte(self):
        df = _geocode(description_detail="Studio Lyon 3e rénové")
        r = df.iloc[0]
        self.assertEqual(r["source_localisation"], "texte")
        self.assertTrue(r["sur_carte"])
        self.assertIn(clean_immo.step_quartiers(df).iloc[0]["quartier"], QUARTIERS_LYON_3)

    def test_texte_lille_donne_quartier_du_texte(self):
        df = _geocode(code_postal="59000", ville="Lille", description_raw="Appartement situé à Fives")
        self.assertEqual(df.iloc[0]["source_localisation"], "texte")
        self.assertEqual(clean_immo.step_quartiers(df).iloc[0]["quartier"], "Fives")

    def test_description_detail_passe_avant_description(self):
        r = _geocode(description_detail="Situé à Perrache", description="Lyon 3e").iloc[0]
        self.assertEqual(r["source_localisation"], "texte")
        self.assertLess(r["latitude"], 45.76)  # 69002 (Perrache), pas 69003

    def test_cp_ambigu_plus_proche_perrache_donne_jitter_hors_carte(self):
        r = _geocode(description_detail="Appartement proche Perrache").iloc[0]
        self.assertEqual(r["source_localisation"], "jitter")
        self.assertFalse(r["sur_carte"])
        self.assertTrue(pd.notna(r["latitude"]) and pd.notna(r["longitude"]))

    def test_lille_sans_indice_donne_jitter_hors_carte(self):
        df = _geocode(code_postal="59000", ville="Lille")
        self.assertEqual(df.iloc[0]["source_localisation"], "jitter")
        self.assertFalse(df.iloc[0]["sur_carte"])
        self.assertEqual(clean_immo.step_quartiers(df).iloc[0]["quartier"], "Lille / Non localisé")

    def test_aucune_ligne_supprimee_et_sur_carte_false_existant_conserve(self):
        df = pd.DataFrame({
            "code_postal": ["69007", "69000", "69000", "59000"],
            "ville": ["Lyon", "Lyon", "Lyon", "Lille"],
            "sur_carte": [True, True, False, True],
            "description_detail": ["", "Lyon 3e", "Lyon 3e", "Situé à Fives"],
        })
        r = clean_immo.step_geocoding(df)
        self.assertEqual(len(r), 4)
        self.assertEqual(list(r["source_localisation"]), ["cp", "texte", "texte", "texte"])
        self.assertEqual(list(r["sur_carte"]), [True, True, False, True])
        self.assertNotIn("description_raw", r.columns)

    def test_deterministe(self):
        pd.testing.assert_frame_equal(
            _geocode(description_detail="Lyon 3e"), _geocode(description_detail="Lyon 3e")
        )


if __name__ == "__main__":
    unittest.main()
