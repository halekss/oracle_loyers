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

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import scraper_century_21
import scraper_orpi
import scraper_pap
import scraper_paruvendu
import scraper_seloger
import scraper_vizzit
from scraper_utils import pick_user_agent

MIN_ANNONCES = 3
NAV_TIMEOUT_MS = 30000
# Délai laissé à CHAQUE sélecteur candidat pour apparaître : ces sites sont en
# grande partie rendus côté client (React/Next.js), le contenu n'existe pas
# encore au moment de "domcontentloaded". Nettement plus court que les 60-120s
# tolérés par les scrapers de production (qui gèrent aussi cookies/CAPTCHA),
# suffisant pour un simple canari de présence de sélecteur.
CARD_WAIT_MS = 20000

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Répertoire d'artefacts de diagnostic (capture écran + HTML brut), peuplé
# uniquement en cas d'échec afin de distinguer un vrai changement de site d'un
# blocage anti-bot/cookie-wall sans avoir à reproduire le test en local (voir
# le workflow scraper-selector-canary.yml, qui upload ce dossier en artefact
# CI). Volontairement ignoré par git (contenu éphémère, propre à chaque run).
DIAG_DIR = os.path.join(os.path.dirname(__file__), "diagnostics")


def save_diagnostics(page, site_name):
    """Capture une screenshot pleine page et un dump HTML brut de `page` sous
    DIAG_DIR/<site_name>.{png,html}, sur la meilleure tentative (n'importe
    quelle erreur Playwright pendant la capture est avalée : le diagnostic est
    un bonus, il ne doit jamais masquer l'échec réel du test)."""
    os.makedirs(DIAG_DIR, exist_ok=True)
    safe_name = site_name.lower().replace(" ", "_")
    try:
        page.screenshot(path=os.path.join(DIAG_DIR, f"{safe_name}.png"), full_page=True)
    except PlaywrightError:
        pass
    try:
        html = page.content()
    except PlaywrightError:
        html = None
    if html is not None:
        with open(os.path.join(DIAG_DIR, f"{safe_name}.html"), "w", encoding="utf-8") as f:
            f.write(html)


def new_page(browser):
    """Contexte Playwright avec un User-Agent réaliste (cf. scraper_utils.pick_user_agent),
    pour limiter le risque de faux-positif "SÉLECTEUR CASSÉ" causé par un blocage anti-bot
    basique plutôt qu'un vrai changement de structure."""
    context = browser.new_context(user_agent=pick_user_agent() or DEFAULT_USER_AGENT)
    return context.new_page()


def find_cards(page, card_selectors, wait_ms=CARD_WAIT_MS):
    """Essaie chaque sélecteur de `card_selectors` dans l'ordre, en lui laissant
    `wait_ms` pour apparaître dans le DOM avant de passer au suivant. Renvoie
    (locator, sélecteur_matché) ou (None, None) si aucun n'apparaît à temps."""
    for sel in card_selectors:
        try:
            page.wait_for_selector(sel, timeout=wait_ms, state="attached")
        except PlaywrightError:
            continue
        locator = page.locator(sel)
        if locator.count() > 0:
            return locator, sel
    return None, None


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
            page = new_page(browser)
            page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")

            cards, matched_selector = find_cards(page, card_selectors)

            if cards is None:
                save_diagnostics(page, site_name)
                test_case.fail(
                    f"SÉLECTEUR CASSÉ ({site_name}) : aucun des sélecteurs de carte "
                    f"{card_selectors} ne matche sur {url}. Refonte de site probable."
                )

            count = cards.count()
            if count < MIN_ANNONCES:
                save_diagnostics(page, site_name)
                test_case.fail(
                    f"SÉLECTEUR CASSÉ ({site_name}) : seulement {count} annonce(s) trouvée(s) "
                    f"via '{matched_selector}' sur {url} (minimum attendu : {MIN_ANNONCES})."
                )

            first_card = cards.first
            titre = find_first_locator_text(first_card, title_selectors)
            prix = find_first_locator_text(first_card, price_selectors)

            if not titre or not prix:
                save_diagnostics(page, site_name)
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
    # Bloqué en permanence par un challenge Cloudflare ("Just a moment...")
    # dès qu'un Chromium headless non-stealth y accède : confirmé via
    # canary-diagnostics le 2026-08-03 (voir README, section canari). Playwright
    # n'a pas les patchs anti-détection d'undetected_chromedriver (scrapers de
    # production) ; ce n'est pas corrigeable par un ajustement de sélecteur.
    # xfail plutôt que fail pour ne pas spammer l'issue GitHub chaque nuit —
    # un "unexpected success" signalerait que le blocage a changé.
    @unittest.expectedFailure
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
    # Bloqué en permanence par un CAPTCHA DataDome dès qu'un Chromium headless
    # non-stealth y accède : confirmé via canary-diagnostics le 2026-08-03 (voir
    # README, section canari). Même raisonnement xfail que PapSelectorCanaryTest.
    @unittest.expectedFailure
    def test_selectors_still_match_live_page(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = new_page(browser)
                page.goto(scraper_seloger.base_url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")

                cards, _ = find_cards(page, scraper_seloger.CARD_SELECTORS)

                if cards is None:
                    save_diagnostics(page, "SeLoger")
                    self.fail(
                        f"SÉLECTEUR CASSÉ (SeLoger) : aucun des sélecteurs de carte "
                        f"{scraper_seloger.CARD_SELECTORS} ne matche. Refonte de site probable."
                    )
                if cards.count() < MIN_ANNONCES:
                    save_diagnostics(page, "SeLoger")
                    self.fail(f"SÉLECTEUR CASSÉ (SeLoger) : seulement {cards.count()} annonce(s) trouvée(s).")

                # SeLoger encode titre/lieu/prix/infos dans l'attribut title de la carte
                full_title = cards.first.get_attribute("title") or ""
                parsed = scraper_seloger.parse_title_attribute(full_title)
                if parsed is None:
                    save_diagnostics(page, "SeLoger")
                    self.fail(
                        "SÉLECTEUR CASSÉ (SeLoger) : l'attribut title de la carte ne suit plus le "
                        f"format 'Type - Lieu - Prix - Infos' attendu (valeur reçue : {full_title!r})."
                    )
                titre, lieu, prix, infos = parsed
                if not titre or not prix:
                    save_diagnostics(page, "SeLoger")
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
            card_selectors=["div.blocAnnonce", "article.blocAnnonce"],
            title_selectors=["a.popinphoto_liste_titre", "h3"],
            price_selectors=["div.popinphoto_liste_prix", "div.encoded-lnk"],
        )


if __name__ == "__main__":
    unittest.main()
