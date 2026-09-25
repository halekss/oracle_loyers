"""Adresse du bien extraite d'un texte libre (ORA-180) : « 52 rue André Bollier ».

Même philosophie que localisation_texte : déterministe, sans réseau, et un faux
négatif est préféré à un faux positif. Une rue n'est retenue que si elle est
l'adresse du bien — pas un repère (« à 2 pas de la place X », « angle rue Y »),
pas l'adresse de l'agence (« notre cabinet, 3 rue Z »), pas niée.
"""
import re

from services.localisation_texte import (
    _CLAUSES, _NEGATION, _PHRASES, _PROXIMITE, _VERBE_LIEU, _clause_propre, _normaliser,
)

_VOIE = r"(?i:rue|avenue|av\.?|boulevard|bd|cours|quai|impasse|all[ée]e|chemin|route|place|montée|passage)"
_PARTICULE = r"(?:de\s+la|de\s+l['’]|du|des|de|d['’]|la|le|l['’])"
_MOT = r"[A-ZÀ-Ý][\w'’\-]*"
_ADRESSE = re.compile(
    r"(?<![\d,.])(?:(?P<num>\d{1,3}(?:\s?(?i:bis|ter))?)\s+)?"
    r"(?P<voie>" + _VOIE + r")\s+"
    r"(?P<nom>(?:" + _PARTICULE + r"\s*)?" + _MOT + r"(?:\s+(?:" + _PARTICULE + r"\s*)?" + _MOT + r"){0,2})"
)
# Mots capitalisés qui ne font plus partie d'un nom de rue (ville, bâtiment, début de phrase).
_FIN_NOM = {
    "lyon", "lille", "bat", "batiment", "appartement", "studio", "garage", "parking", "disponible", "libre",
    "ce", "cet", "cette", "il", "elle", "au", "aux", "dans", "situe", "situee", "proche", "ideal",
    "idealement", "decouvrez", "orpi", "nous", "vous", "les", "un", "une", "loyer", "charges",
    "quartier", "sur", "tram", "metro", "spacieux", "bel", "beau", "superbe", "lumineux",
}
_AGENCE = re.compile(r"\b(?:agence|cabinet|honoraires|bureaux|contactez|permanence|nous vous accueill\w*)\b")
_REPERE_ADRESSE = re.compile(r"\b(?:angle|coin|face|derriere|entre|croisement|carrefour|parallele)\b")
# Une « place », un « quai » ou un « cours » sans numéro est presque toujours un repère.
_NUMERO_REQUIS = re.compile(r"(?i)^(?:place|quai|cours)$")


def _nom_propre(nom):
    mots = re.sub(r"(?i)-(?:lyon|\d).*", "", nom).rstrip("- ").split()
    for i, mot in enumerate(mots):
        if _normaliser(mot).strip(".,") in _FIN_NOM or any(c.isdigit() for c in mot):
            mots = mots[:i]
            break
    return " ".join(mots).rstrip("- ")


def _candidats(phrase):
    """[(adresse, avec_numero)] acceptées dans une phrase brute."""
    if _AGENCE.search(_normaliser(phrase)):
        return []
    phrase = re.sub(r"(\d)\s*,\s*(?=" + _VOIE + r"\b)", r"\1 ", phrase)  # « 62, rue X » → « 62 rue X »
    trouvees = []
    for clause in _CLAUSES.split(phrase):
        for m in _ADRESSE.finditer(clause):
            nom = _nom_propre(m["nom"])
            pre = _clause_propre(_normaliser(clause[:m.start()]))
            derniers = " ".join(pre.split()[-5:])
            a_num = bool(m["num"])
            if not nom or (not a_num and _NUMERO_REQUIS.match(m["voie"])):
                continue
            if _NEGATION.search(derniers) or _REPERE_ADRESSE.search(derniers) or _PROXIMITE.search(pre):
                continue
            if not a_num and pre and not _VERBE_LIEU.search(pre):
                continue  # rue sans numéro : uniquement « situé rue X » ou tête de clause
            trouvees.append((" ".join(filter(None, [m["num"], m["voie"].lower(), nom])), a_num))
    return trouvees


def extraire_adresse(texte):
    """(adresse | None, raison courte). Contradiction = None."""
    if not isinstance(texte, str) or not texte.strip():
        return None, "texte vide"
    trouvees = [c for p in _PHRASES.split(texte) for c in _candidats(p)]
    if not trouvees:
        return None, "aucune adresse retenue"
    avec_numero = {a for a, n in trouvees if n}
    distinctes = avec_numero or {a for a, _ in trouvees}
    if len(distinctes) > 1:
        return None, "contradiction : " + " / ".join(sorted(distinctes))
    return next(iter(distinctes)), "adresse du bien"


def localiser_adresse(textes):
    """Premier texte (dans l'ordre donné) qui décide ; une contradiction est définitive."""
    raison = "texte vide"
    for texte in textes:
        adresse, r = extraire_adresse(texte)
        if adresse or r.startswith("contradiction"):
            return adresse, r
        if r != "texte vide":
            raison = r
    return None, raison
