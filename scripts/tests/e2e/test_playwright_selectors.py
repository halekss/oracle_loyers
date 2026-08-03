"""
Tests Playwright "canari" (ORA-20) : naviguent vers la page de résultats réelle
de chaque site source et vérifient que les sélecteurs CSS actuellement utilisés
en production (scraper_*.py) retournent encore des annonces exploitables.

Contrairement à scripts/tests/test_scraper_extraction_fixtures.py (ORA-19), ces
tests font un VRAI accès réseau vers les 6 portails et lancent un VRAI navigateur
(Playwright/Chromium) : ils sont lents, potentiellement fragiles (CAPTCHA,
blocage anti-bot ponctuel) et ne tournent PAS dans le job CI standard (push/PR) —
voir le job dédié `playwright-selectors` planifié quotidiennement (ORA-21).

Un échec ici signifie l'une de deux choses, que ce fichier s'efforce de
distinguer explicitement dans ses messages d'échec :
- "SÉLECTEUR CASSÉ" : la page a chargé mais aucun sélecteur ne matche ou le
  contenu extrait est vide -> refonte de site probable, action requise sur les
  scrapers de production.
- toute autre exception (timeout de navigation, DNS, connexion refusée) :
  probablement un problème réseau ponctuel, pas nécessairement un site cassé.

Ces tests ne remplacent PAS les scrapers de production (undetected_chromedriver
reste nécessaire pour le contournement anti-bot) : ils servent uniquement de
canari de détection de changement HTML.
"""

import os
import sys
import unittest

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import scraper_century_21
import scraper_orpi
import scraper_pap
import scraper_paruvendu
import scraper_seloger
import scraper_vizzit

MIN_ANNONCES = 3
NAV_TIMEOUT_MS = 30000


def find_first_locator_text(card, selectors, default=""):
    """Équivalent Playwright de find_first/find_text : cascade de sélecteurs CSS."""
    for sel in selectors:
        locator = card.locator(sel)
        if locator.count() > 0:
            text = locator.first.inner_text().strip()
            if text:
                return text
    return default


def assert_selector_canary(test_case, *, site_name, url, card_selectors, title_selectors, price_selectors):
    """Navigue vers `url`, vérifie qu'au moins MIN_ANNONCES cartes matchent l'un des
    `card_selectors`, et que titre/prix sont non vides pour la première carte.

    Lève une AssertionError explicite ("SÉLECTEUR CASSÉ") en cas d'échec
    d'extraction, distincte des exceptions réseau/navigation laissées telles quelles.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")

            cards = None
            matched_selector = None
            for sel in card_selectors:
                locator = page.locator(sel)
                count = locator.count()
                if count > 0:
                    cards = locator
                    matched_selector = sel
                    break

            if cards is None:
                test_case.fail(
                    f"SÉLECTEUR CASSÉ ({site_name}) : aucun des sélecteurs de carte "
                    f"{card_selectors} ne matche sur {url}. Refonte de site probable."
                )

            count = cards.count()
            if count < MIN_ANNONCES:
                test_case.fail(
                    f"SÉLECTEUR CASSÉ ({site_name}) : seulement {count} annonce(s) trouvée(s) "
                    f"via '{matched_selector}' sur {url} (minimum attendu : {MIN_ANNONCES})."
                )

            first_card = cards.first
            titre = find_first_locator_text(first_card, title_selectors)
            prix = find_first_locator_text(first_card, price_selectors)

            if not titre:
                test_case.fail(
                    f"SÉLECTEUR CASSÉ ({site_name}) : titre vide pour la première annonce "
                    f"(sélecteurs testés : {title_selectors})."
                )
            if not prix:
                test_case.fail(
                    f"SÉLECTEUR CASSÉ ({site_name}) : prix vide pour la première annonce "
                    f"(sélecteurs testés : {price_selectors})."
                )
        finally:
            browser.close()


class Century21SelectorCanaryTest(unittest.TestCase):
    def test_selectors_still_match_live_page(self):
        assert_selector_canary(
            self,
            site_name="Century21",
            url=scraper_century_21.base_url.format(1),
            card_selectors=[scraper_century_21.CARD_SELECTOR],
            title_selectors=scraper_century_21.TITRE_SELECTORS,
            price_selectors=scraper_century_21.PRIX_SELECTORS,
        )


class OrpiSelectorCanaryTest(unittest.TestCase):
    def test_selectors_still_match_live_page(self):
        assert_selector_canary(
            self,
            site_name="Orpi",
            url=scraper_orpi.base_url.format(1),
            card_selectors=scraper_orpi.CARD_SELECTORS,
            title_selectors=scraper_orpi.TITRE_SELECTORS,
            price_selectors=scraper_orpi.PRIX_SELECTORS,
        )


class PapSelectorCanaryTest(unittest.TestCase):
    def test_selectors_still_match_live_page(self):
        assert_selector_canary(
            self,
            site_name="PAP",
            url=scraper_pap.BASE_URL.format(1),
            card_selectors=scraper_pap.CARD_SELECTORS,
            title_selectors=scraper_pap.LIEU_SELECTORS,
            price_selectors=scraper_pap.PRIX_SELECTORS,
        )


class SeLogerSelectorCanaryTest(unittest.TestCase):
    def test_selectors_still_match_live_page(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(scraper_seloger.base_url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")

                cards = None
                for sel in scraper_seloger.CARD_SELECTORS:
                    locator = page.locator(sel)
                    if locator.count() > 0:
                        cards = locator
                        break

                if cards is None:
                    self.fail(
                        f"SÉLECTEUR CASSÉ (SeLoger) : aucun des sélecteurs de carte "
                        f"{scraper_seloger.CARD_SELECTORS} ne matche. Refonte de site probable."
                    )
                if cards.count() < MIN_ANNONCES:
                    self.fail(f"SÉLECTEUR CASSÉ (SeLoger) : seulement {cards.count()} annonce(s) trouvée(s).")

                # SeLoger encode titre/lieu/prix/infos dans l'attribut title de la carte
                full_title = cards.first.get_attribute("title") or ""
                parsed = scraper_seloger.parse_title_attribute(full_title)
                if parsed is None:
                    self.fail(
                        "SÉLECTEUR CASSÉ (SeLoger) : l'attribut title de la carte ne suit plus le "
                        f"format 'Type - Lieu - Prix - Infos' attendu (valeur reçue : {full_title!r})."
                    )
                titre, lieu, prix, infos = parsed
                if not titre or not prix:
                    self.fail(f"SÉLECTEUR CASSÉ (SeLoger) : titre ou prix vide après parsing ({parsed!r}).")
            finally:
                browser.close()


class VizzitSelectorCanaryTest(unittest.TestCase):
    def test_selectors_still_match_live_page(self):
        assert_selector_canary(
            self,
            site_name="Vizzit",
            url=scraper_vizzit.SEARCH_URL.format(1),
            card_selectors=scraper_vizzit.CARD_SELECTORS,
            title_selectors=scraper_vizzit.LIEU_SELECTORS,
            price_selectors=scraper_vizzit.PRIX_SELECTORS,
        )


class ParuVenduSelectorCanaryTest(unittest.TestCase):
    """ParuVendu utilise `requests`/BeautifulSoup en production (pas de rendu JS
    nécessaire), mais le canari passe par Playwright comme les 5 autres sites
    pour un mécanisme de détection uniforme."""

    def test_selectors_still_match_live_page(self):
        assert_selector_canary(
            self,
            site_name="ParuVendu",
            url=scraper_paruvendu.base_url,
            card_selectors=["article.blocAnnonce"],
            title_selectors=["a.popinphoto_liste_titre"],
            price_selectors=["div.popinphoto_liste_prix"],
        )


if __name__ == "__main__":
    unittest.main()
