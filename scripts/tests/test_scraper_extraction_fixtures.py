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


class VizzitExtractionTest(unittest.TestCase):
    def test_extracts_lieu_prix_details_lien(self):
        soup = load_fixture("vizzit.html")
        cards = bs4_select_first_matching(soup, scraper_vizzit.CARD_SELECTORS)
        self.assertEqual(len(cards), 1)
        card = cards[0]

        lien = bs4_first_attr(card, scraper_vizzit.LIEN_SELECTORS, "href")
        prix = bs4_first_text(card, scraper_vizzit.PRIX_SELECTORS)
        lieu = bs4_first_text(card, scraper_vizzit.LIEU_SELECTORS)
        details = card.select(scraper_vizzit.DETAIL_SELECTORS[0])

        self.assertIn("vizzit.fr", lien)
        self.assertEqual(prix, "920 €")
        self.assertEqual(lieu, "Lyon 6e - Brotteaux")
        self.assertEqual([d.get_text(strip=True) for d in details], ["T2", "42 m²"])


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

    def test_find_bs4_returns_none_when_no_selector_matches(self):
        soup = BeautifulSoup("<article class='blocAnnonce'></article>", "html.parser")
        annonce = soup.select_one("article")

        self.assertIsNone(scraper_paruvendu.find_bs4(annonce, scraper_paruvendu.TITRE_SELECTORS))


if __name__ == "__main__":
    unittest.main()
