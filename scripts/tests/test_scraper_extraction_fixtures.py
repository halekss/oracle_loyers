"""
Tests unitaires d'extraction par site (ORA-19), basés sur des fixtures HTML
statiques représentatives d'une page de résultats réelle par portail.

Aucun réseau, aucun navigateur : on réutilise directement les sélecteurs CSS
(CARD_SELECTOR(S), TITRE_SELECTORS, PRIX_SELECTORS, ...) et les fonctions pures
(parse_title_attribute, find_bs4) déjà définies dans chaque scraper_*.py, pour
que ces tests échouent si quelqu'un modifie un sélecteur en production sans
mettre à jour la fixture correspondante.

Century21/Orpi/PAP/SeLoger/Vizzit utilisent l'API Selenium (element.find_element)
pour l'extraction : ce fichier fournit un équivalent BeautifulSoup (bs4_first_text/
bs4_first_attr/bs4_select_first_matching) qui applique la même logique de cascade
de sélecteurs sur du HTML statique parsé. ParuVendu utilise déjà BeautifulSoup en
production : ses fonctions réelles (find_bs4) sont testées directement, sans
équivalent.
"""

import os
import sys
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper_utils import clean_description
import scraper_century_21
import scraper_orpi
import scraper_pap
import scraper_paruvendu
import scraper_seloger
import scraper_vizzit

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


def bs4_first_text(element, selectors, default=""):
    """Équivalent BeautifulSoup de find_first/find_text (cascade de sélecteurs CSS)."""
    for sel in selectors:
        found = element.select_one(sel)
        if found:
            return found.get_text(strip=True)
    return default


def bs4_first_attr(element, selectors, attr, default=""):
    """Équivalent BeautifulSoup de find_attr (cascade de sélecteurs CSS -> attribut)."""
    for sel in selectors:
        found = element.select_one(sel)
        if found:
            val = found.get(attr)
            if val:
                return val
    return default


def bs4_select_first_matching(container, selectors):
    """Équivalent BeautifulSoup de la cascade `for sel in CARD_SELECTORS: driver.find_elements(...)`."""
    for sel in selectors:
        found = container.select(sel)
        if found:
            return found
    return []


class Century21ExtractionTest(unittest.TestCase):
    def test_extracts_titre_prix_surface_lien(self):
        soup = load_fixture("century21.html")
        card = soup.select_one(scraper_century_21.CARD_SELECTOR)
        self.assertIsNotNone(card)

        titre = bs4_first_text(card, scraper_century_21.TITRE_SELECTORS)
        prix = bs4_first_text(card, scraper_century_21.PRIX_SELECTORS)
        infos = bs4_first_text(card, scraper_century_21.INFOS_SELECTORS)
        lien = card.find("a").get("href")

        self.assertEqual(titre, "Appartement T3 à louer")
        self.assertEqual(prix, "1 200 € par mois charges comprises")
        self.assertIn("65 m2", infos)
        self.assertEqual(lien, "https://www.century21.fr/trouver_logement/detail/15336559480/")


class OrpiExtractionTest(unittest.TestCase):
    def test_extracts_titre_prix_surface_lien(self):
        soup = load_fixture("orpi.html")
        cards = bs4_select_first_matching(soup, scraper_orpi.CARD_SELECTORS)
        self.assertEqual(len(cards), 1)
        card = cards[0]

        titre = bs4_first_text(card, scraper_orpi.TITRE_SELECTORS)
        prix = bs4_first_text(card, scraper_orpi.PRIX_SELECTORS)
        infos = bs4_first_text(card, scraper_orpi.INFOS_SELECTORS)
        lien = card.find("a").get("href")

        self.assertEqual(titre, "Bel appartement Croix-Rousse")
        self.assertEqual(prix, "890 €")
        self.assertIn("T2", infos)
        self.assertIn("45 m²", infos)
        self.assertEqual(lien, "https://www.orpi.com/annonce/location-appartement-lyon/12345")

    def test_extracts_quartier_without_ui_labels(self):
        # ORA-159 : le quartier vient de son propre élément, pas du blob Infos
        card = bs4_select_first_matching(load_fixture("orpi.html"), scraper_orpi.CARD_SELECTORS)[0]

        quartier = scraper_orpi.parse_quartier(bs4_first_text(card, scraper_orpi.QUARTIER_SELECTORS))

        self.assertEqual(quartier, "Monplaisir - Frères Lumière")
        for libelle in ("Message", "Favoris", "Ascenseur", "Balcon", "Bon état"):
            self.assertNotIn(libelle, quartier)

    def test_parse_quartier_edge_cases(self):
        self.assertEqual(scraper_orpi.parse_quartier("Lyon 5- Champvert"), "Champvert")
        self.assertEqual(scraper_orpi.parse_quartier("Lyon 4- Parc Popy"), "Parc Popy")
        self.assertEqual(scraper_orpi.parse_quartier("Lyon 5"), "")
        self.assertEqual(scraper_orpi.parse_quartier(""), "")

    def test_extract_price_from_text_fallback(self):
        # Cas limite : pas de sélecteur prix dédié, prix noyé dans le texte brut
        self.assertEqual(scraper_orpi.extract_price_from_text("Loyer : 1 234 € CC"), "1 234 €")
        self.assertEqual(scraper_orpi.extract_price_from_text("Aucun prix ici"), "")


class PapExtractionTest(unittest.TestCase):
    def test_extracts_lieu_prix_details_lien(self):
        soup = load_fixture("pap.html")
        cards = bs4_select_first_matching(soup, scraper_pap.CARD_SELECTORS)
        self.assertEqual(len(cards), 1)
        card = cards[0]

        lieu = bs4_first_text(card, scraper_pap.LIEU_SELECTORS, "Lieu Inconnu")
        prix = bs4_first_text(card, scraper_pap.PRIX_SELECTORS, "N/C")
        details = bs4_first_text(card, scraper_pap.DETAILS_SELECTORS)
        lien = card.find("a").get("href")

        self.assertEqual(lieu, "Lyon 8e")
        self.assertEqual(prix, "750 €")
        self.assertIn("T2", details)
        self.assertIn("48 m²", details)
        self.assertIn("pap.fr", lien)


class SeLogerExtractionTest(unittest.TestCase):
    def test_extracts_via_title_attribute_parsing(self):
        soup = load_fixture("seloger.html")
        cards = bs4_select_first_matching(soup, scraper_seloger.CARD_SELECTORS)
        self.assertEqual(len(cards), 1)
        card = cards[0]

        lien = card.get("href")
        full_title = card.get("title") or ""
        parsed = scraper_seloger.parse_title_attribute(full_title)

        self.assertIsNotNone(parsed)
        titre, lieu, prix, infos = parsed
        self.assertEqual(titre, "Appartement 3 pièces")
        self.assertEqual(lieu, "Lyon 3e Part-Dieu")
        self.assertEqual(prix, "1 100 €")
        self.assertEqual(infos, "65 m²")
        self.assertIn("seloger.com", lien)

    def test_parse_title_attribute_returns_none_for_unrecognized_format(self):
        # Cas limite : format de titre non parsable (site refondu) -> fallback DOM attendu
        self.assertIsNone(scraper_seloger.parse_title_attribute("Un simple titre sans séparateur"))
        self.assertIsNone(scraper_seloger.parse_title_attribute(""))


class _FakeElement:
    """Reproduit juste ce dont decode_data_o_link a besoin (element.get_attribute),
    sans dépendre de Selenium/bs4 pour ce test précis."""
    def __init__(self, attrs):
        self._attrs = attrs

    def get_attribute(self, name):
        return self._attrs.get(name)


class VizzitExtractionTest(unittest.TestCase):
    def test_extracts_lieu_prix_details(self):
        soup = load_fixture("vizzit.html")
        cards = bs4_select_first_matching(soup, scraper_vizzit.CARD_SELECTORS)
        self.assertEqual(len(cards), 1)
        card = cards[0]

        prix = bs4_first_text(card, scraper_vizzit.PRIX_SELECTORS)
        lieu = bs4_first_text(card, scraper_vizzit.LIEU_SELECTORS)
        details = card.select(scraper_vizzit.DETAIL_SELECTORS[0])

        # info-price contient maintenant un <span class="price-period"> imbriqué
        # ("610 €/mois" observé en réel) ; clean_price_integer() (data_fusion.py)
        # ne garde que les chiffres, donc "/mois" n'est pas un problème en aval.
        self.assertEqual(prix, "920 €/mois")
        self.assertEqual(lieu, "Lyon 6e - Brotteaux")
        self.assertEqual([d.get_text(strip=True) for d in details], ["T2", "42 m²"])

    def test_card_has_no_anchor_link_anymore(self):
        # Refonte observée le 2026-08-11 (ORA-71 POC) : Vizzit n'expose plus
        # de <a href> sur la carte (classes "obf-link obf-blank"), seulement
        # un attribut data-o encodé en base64 — cf. test_decode_data_o_link.
        soup = load_fixture("vizzit.html")
        card = bs4_select_first_matching(soup, scraper_vizzit.CARD_SELECTORS)[0]

        lien = bs4_first_attr(card, scraper_vizzit.LIEN_SELECTORS, "href")

        self.assertEqual(lien, "")

    def test_decode_data_o_link_extracts_the_real_listing_url(self):
        element = _FakeElement({
            "data-o": "aHR0cHM6Ly93d3cudml6eml0LmZyL2ZyL3Byb3BlcnR5L2FwcGFydGVtZW50L2xpbGxlL0F2ZzcwN3JxaHpwcXFvMjk="
        })

        lien = scraper_vizzit.decode_data_o_link(element)

        self.assertEqual(lien, "https://www.vizzit.fr/fr/property/appartement/lille/Avg707rqhzpqqo29")

    def test_decode_data_o_link_returns_empty_string_when_attribute_absent(self):
        element = _FakeElement({})

        self.assertEqual(scraper_vizzit.decode_data_o_link(element), "")

    def test_parse_expected_count_reads_total_from_results_title(self):
        # Garde-fou d'archivage : le nombre annoncé par le site fixe si un run est complet.
        self.assertEqual(scraper_vizzit.parse_expected_count("726 appartements et maisons à louer à Lille (Nord)"), 726)
        self.assertEqual(scraper_vizzit.parse_expected_count("1 204 appartements et maisons à louer"), 1204)
        self.assertEqual(scraper_vizzit.parse_expected_count("0 appartement et maison à louer à Lille"), 0)
        self.assertIsNone(scraper_vizzit.parse_expected_count("Vizzit"))
        self.assertIsNone(scraper_vizzit.parse_expected_count(None))

    def test_build_page_url_uses_base_url_as_is_for_page_one(self):
        base_url = "https://www.vizzit.fr/fr/properties/{}?searchQuery=lg-fr-cn-fr-city_id-gr_3040"

        url = scraper_vizzit.build_page_url(base_url, 1)

        self.assertEqual(url, "https://www.vizzit.fr/fr/properties/1?searchQuery=lg-fr-cn-fr-city_id-gr_3040")

    def test_build_page_url_appends_p_n_query_param_for_later_pages(self):
        # Régression réelle : Vizzit pagine via le paramètre de requête p_n,
        # pas via le numéro dans le chemin de l'URL — un ancien scraper qui
        # changeait seulement le chemin recevait systématiquement la page 1
        # (constaté : mêmes data-advertid quel que soit le numéro dans le
        # chemin), plafonnant la collecte à ~24 annonces quel que soit le
        # nombre réel de résultats (803 pour Lille).
        base_url = "https://www.vizzit.fr/fr/properties/{}?searchQuery=lg-fr-cn-fr-city_id-gr_3040"

        url = scraper_vizzit.build_page_url(base_url, 3)

        self.assertEqual(url, "https://www.vizzit.fr/fr/properties/1?searchQuery=lg-fr-cn-fr-city_id-gr_3040&p_n=3")

    def test_apply_price_band_appends_max_only(self):
        base_url = "https://www.vizzit.fr/fr/properties/{}?searchQuery=lg-fr-cn-fr-city_id-gr_3040"

        url = scraper_vizzit.apply_price_band(base_url, {"max": 600})

        self.assertEqual(url, base_url + "-mx_p-600")

    def test_apply_price_band_appends_min_only(self):
        base_url = "https://www.vizzit.fr/fr/properties/{}?searchQuery=lg-fr-cn-fr-city_id-gr_3040"

        url = scraper_vizzit.apply_price_band(base_url, {"min": 901})

        self.assertEqual(url, base_url + "-mn_p-901")

    def test_apply_price_band_appends_min_and_max(self):
        # Régression réelle (ORA-71 POC) : Vizzit ne renvoie jamais plus de
        # 20 pages (~480 annonces) sur une seule recherche, quel que soit le
        # nombre réel de résultats — 480/803 annonces Lille manquantes tant
        # que la recherche n'est pas subdivisée en tranches de prix.
        base_url = "https://www.vizzit.fr/fr/properties/{}?searchQuery=lg-fr-cn-fr-city_id-gr_3040"

        url = scraper_vizzit.apply_price_band(base_url, {"min": 601, "max": 900})

        self.assertEqual(url, base_url + "-mn_p-601-mx_p-900")

    def test_apply_price_band_returns_base_url_unchanged_for_empty_band(self):
        base_url = "https://www.vizzit.fr/fr/properties/{}?searchQuery=lg-fr-cn-fr-city_id-gr_3040"

        url = scraper_vizzit.apply_price_band(base_url, {})

        self.assertEqual(url, base_url)


class ParuVenduExtractionTest(unittest.TestCase):
    """ParuVendu utilise déjà BeautifulSoup en production : on teste find_bs4
    directement, sans équivalent de test."""

    def test_extracts_titre_prix_lien_with_real_find_bs4(self):
        soup = load_fixture("paruvendu.html")
        annonces = []
        for tag, attrs in scraper_paruvendu.CARD_SELECTORS:
            annonces = soup.find_all(tag, attrs)
            if annonces:
                break
        self.assertEqual(len(annonces), 1)
        annonce = annonces[0]

        titre_elem = scraper_paruvendu.find_bs4(annonce, scraper_paruvendu.TITRE_SELECTORS)
        prix_elem = scraper_paruvendu.find_bs4(annonce, scraper_paruvendu.PRIX_SELECTORS)

        self.assertIsNotNone(titre_elem)
        titre = " ".join(titre_elem.text.split())
        prix = prix_elem.text.strip()
        lien = f"https://www.paruvendu.fr{titre_elem.get('href')}"

        self.assertEqual(titre, "T3 lumineux proche Part-Dieu")
        self.assertEqual(prix, "1 050 €")
        self.assertEqual(lien, "https://www.paruvendu.fr/annonces/location-appartement-lyon-3eme-69003/12345.html")

    def test_paruvendu_link_falls_back_to_card_link_when_title_is_a_heading(self):
        card = load_fixture("paruvendu_h3.html").select_one("div.blocAnnonce")
        titre_elem = scraper_paruvendu.find_bs4(card, scraper_paruvendu.TITRE_SELECTORS)

        self.assertEqual(titre_elem.name, "h3")
        self.assertEqual(
            scraper_paruvendu.find_lien_partiel(card, titre_elem),
            "/immobilier/location/appartement/1295641036A1KILHAP000",
        )

    def test_find_bs4_returns_none_when_no_selector_matches(self):
        soup = BeautifulSoup("<article class='blocAnnonce'></article>", "html.parser")
        annonce = soup.select_one("article")

        self.assertIsNone(scraper_paruvendu.find_bs4(annonce, scraper_paruvendu.TITRE_SELECTORS))


class DetailDescriptionExtractionTest(unittest.TestCase):
    """ORA-161 : description libre lue sur la page détail de l'annonce."""

    def _description(self, fixture, selectors):
        soup = load_fixture(fixture)
        for selector in selectors:
            for element in soup.select(selector):
                text = clean_description(element.get_text(" ", strip=True))
                if text:
                    return text
        return ""

    def test_century21_uses_the_real_description_not_the_ai_summary(self):
        text = self._description("century21_detail.html", scraper_century_21.DESCRIPTION_SELECTORS)

        self.assertTrue(text.startswith("A louer à Lyon 3ème, quartier Montchat"))
        self.assertNotIn("Résumé généré", text)
        self.assertFalse(text.lower().startswith("description"))

    def test_paruvendu_description_excludes_site_navigation(self):
        soup = load_fixture("paruvendu_detail.html")

        text = scraper_paruvendu.find_description_bs4(soup)

        self.assertIn("151 AVENUE BERTHELOT 69007 LYON", text)
        self.assertNotIn("Ventes immobilières", text)

    def test_paruvendu_captcha_redirect_is_an_error_not_an_empty_description(self):
        from unittest import mock
        blocked = mock.Mock(status_code=200, url="https://www.paruvendu.fr/communfo/antiaspiration/default/getCaptcha?x=1", text="<html></html>")
        with mock.patch.object(scraper_paruvendu, "fetch_page", return_value=blocked):
            with self.assertRaises(RuntimeError):
                scraper_paruvendu.fetch_description("https://www.paruvendu.fr/immobilier/location/appartement/1")

    def test_paruvendu_page_without_description_gives_empty_string(self):
        soup = BeautifulSoup("<html><body><p>Erreur 410</p></body></html>", "html.parser")
        self.assertEqual(scraper_paruvendu.find_description_bs4(soup), "")

    def test_pap_and_seloger_selectors_match_their_fixture_templates(self):
        self.assertIn("Part-Dieu", self._description("pap_detail.html", scraper_pap.DESCRIPTION_SELECTORS))
        seloger = self._description("seloger_detail.html", scraper_seloger.DESCRIPTION_SELECTORS)
        self.assertIn("Bellecour", seloger)
        self.assertFalse(seloger.lower().startswith("description"))

    def test_orpi_description_selector_and_column(self):
        text = self._description("orpi_detail.html", scraper_orpi.DESCRIPTION_SELECTORS)
        self.assertTrue(text.startswith("T2 meublé - Part-Dieu"))
        with open(scraper_orpi.__file__, encoding="utf-8") as f:
            self.assertRegex(f.read(), r"CSV_HEADER = \[[^\]]*'Quartier', 'Description'\]")

    def test_every_scraper_appends_a_description_column_last(self):
        for module, name in ((scraper_century_21, 'century21'), (scraper_pap, 'pap'), (scraper_seloger, 'seloger'), (scraper_paruvendu, 'paruvendu')):
            with open(module.__file__, encoding="utf-8") as f:
                source = f.read()
            self.assertRegex(source, r"CSV_HEADER = \[[^\]]*'DerniereVue', 'Description'\]", name)



if __name__ == "__main__":
    unittest.main()
