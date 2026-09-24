"""Localisation d'une annonce par son texte libre (étape 3 de step_geocoding).

Déterministe, sans réseau ni LLM : gazetteer normalisé (casse, accents,
tirets, « 3e/3ème/III ») + analyse de portée par clause (marqueur de lieu,
proximité, négation, repère). Un faux négatif est préféré à un faux positif :
au moindre doute on ne décide pas (renvoie None) et l'annonce retombe sur le
jitter de repli.

Zone renvoyée : nom de quartier pour Lille (clés de QUARTIERS_LILLE, plus
Lomme/Hellemmes/Euralille) ; code postal d'arrondissement (« 69003 ») pour
Lyon — la seule zone de jitter Lyon existante est l'arrondissement.
"""
import re
import unicodedata

LILLE_ALIASES = {
    "Lille-Centre": ["lille centre"],
    "Vieux-Lille": ["vieux lille"],
    "Wazemmes": ["wazemmes"],
    "Lille-Moulins": ["lille moulins", "moulins"],
    "Vauban-Esquermes": ["vauban esquermes", "esquermes", "vauban"],
    "Lille-Sud": ["lille sud"],
    "Faubourg de Béthune": ["faubourg de bethune"],
    "Bois Blancs": ["bois blancs", "bois blanc"],
    "Fives": ["fives"],
    "Saint-Maurice Pellevoisin": ["saint maurice pellevoisin", "saint maurice", "pellevoisin"],
    "Lomme": ["lomme"],
    "Hellemmes": ["hellemmes"],
    "Euralille": ["euralille"],
}

# Noms de quartiers Lyon (cf. trouver_quartier) rattachés à leur arrondissement.
# Volontairement absents car à cheval sur deux arrondissements ou trop
# génériques : « Croix-Rousse » seul (69001/69004), Hôtel de Ville, Préfecture, Foch.
LYON_ALIASES = {
    "69001": ["terreaux", "pentes de la croix rousse", "pentes croix rousse"],
    "69002": ["perrache", "confluence", "ainay", "bellecour", "cordeliers"],
    "69003": ["part dieu", "villette", "montchat"],
    "69004": ["plateau de la croix rousse", "plateau croix rousse"],
    "69005": ["vieux lyon", "saint just", "point du jour"],
    "69006": ["brotteaux"],
    "69007": ["guillotiere", "jean mace", "gerland"],
    "69008": ["monplaisir", "bachut"],
    "69009": ["vaise", "valmy", "duchere"],
}

_ROMAIN = {"ii": 2, "iii": 3, "iv": 4, "vi": 6, "vii": 7, "viii": 8, "ix": 9}
_ARR_RE = re.compile(
    r"(?<![a-z0-9])(?:"
    r"lyon\s*(?P<n1>\d{1,2})\s*(?:e|eme|er|ere)\b"
    r"|lyon\s+(?P<r1>ii|iii|iv|vi|vii|viii|ix)\b"
    r"|lyon\s*0(?P<n3>[1-9])\b"
    r"|(?P<n2>\d{1,2})\s*(?:e|eme|er|ere)?\s+arrondissement\b)"
)


def _gazetteer(aliases):
    zone_de = {a: z for z, als in aliases.items() for a in als}
    alternance = "|".join(re.escape(a) for a in sorted(zone_de, key=len, reverse=True))
    return re.compile(r"(?<![a-z0-9])(?:%s)(?![a-z0-9])" % alternance), zone_de


_GAZ = {"lille": _gazetteer(LILLE_ALIASES), "lyon": _gazetteer(LYON_ALIASES)}

_REPERE_AVANT = re.compile(
    r"(?:^|\s)(?:rue|place|avenue|av|boulevard|bd|cours|quai|impasse|allee|passage|pont|square|"
    r"parc|jardin|marche|ecole|lycee|college|universite|fac|hopital|clinique|gare|station|metro|"
    r"tram|tramway|bus|arret|centre commercial|residence|commissariat|mairie|eglise|stade|salle|"
    r"cinema|theatre|musee|pharmacie|boulangerie|commerces?)(?:\s+(?:de|du|des|d|la|le|les|l))*$"
)
_REPERE_APRES = re.compile(r"^(?:gare|station|metro|tram|tramway|bus|centre commercial)\b")
_PROXIMITE = re.compile(
    r"\b(?:proche|proches|proximite|pres|cote|deux pas|\d+\s*(?:min|mn|minutes?|metres?|km)|"
    r"voisin\w*|bordure|portes|limitrophe|autour|environs|alentours|distance|loin|face|entre|"
    r"desservi\w*|dessert|acces|accessible|ligne|au pied|gare|station|metro|tram|tramway|bus|arret)\b"
)
_NEGATION = re.compile(r"\b(?:hors|pas|ni|sans|excepte|sauf|contrairement|en dehors|eloigne\w*)\b")
_VERBE_LIEU = re.compile(r"\b(?:situe\w*|localise\w*|implante\w*|sis|sise|trouve)\b")
_MARQUEUR_LIEU = re.compile(
    r"(?:^|\s)(?:a|au|aux|dans|sur|quartier|secteur|coeur|plein)"
    r"(?:\s+(?:le|la|les|l|du|de|des|d|quartier|secteur|coeur|plein))*$"
)
_PHRASES = re.compile(r"[.!?;\n\r|•]+")
_CLAUSES = re.compile(r"[,:()/]+|\s[-–—]\s")


def _normaliser(texte):
    t = unicodedata.normalize("NFKD", str(texte).lower().replace("œ", "oe"))
    return "".join(c for c in t if not unicodedata.combining(c))


def _clause_propre(clause):
    return re.sub(r"\s+", " ", re.sub(r"[-_'’`]", " ", clause)).strip()


def _mentions(clause, ville):
    """[(debut, fin, zone, est_arrondissement)] dans une clause normalisée."""
    trouvees = []
    if ville == "lyon":
        for m in _ARR_RE.finditer(clause):
            n = int(m["n1"] or m["n2"] or m["n3"] or _ROMAIN[m["r1"]])
            if 1 <= n <= 9:
                trouvees.append((m.start(), m.end(), f"6900{n}", True))
    regex, zone_de = _GAZ[ville]
    for m in regex.finditer(clause):
        trouvees.append((m.start(), m.end(), zone_de[m.group()], False))
    return trouvees


def _evaluer(pre, post, arrondissement, prox_phrase_avant):
    """(accepté, raison) pour une mention, d'après ce qui la précède/suit dans sa clause."""
    if _NEGATION.search(" ".join(pre.split()[-5:])):
        return False, "négation"
    if _REPERE_AVANT.search(pre) or _REPERE_APRES.match(post):
        return False, "repère (rue/gare/station/commerce)"
    prox = list(_PROXIMITE.finditer(pre))
    if prox and not any(v.start() >= prox[-1].end() for v in _VERBE_LIEU.finditer(pre)):
        return False, "proximité/distance"
    if arrondissement:
        return True, "arrondissement explicite"
    if _MARQUEUR_LIEU.search(pre):
        return True, "marqueur de lieu"
    if pre == "" and not prox_phrase_avant:
        return True, "mention en tête de clause"
    return False, "aucun marqueur de lieu"


def extraire_zone(texte, ville):
    """(zone | None, raison courte) pour un texte et une ville ('lille'/'lyon')."""
    ville = (ville or "").lower()
    if ville not in _GAZ:
        return None, "ville inconnue"
    if not isinstance(texte, str) or not texte.strip():
        return None, "texte vide"

    acceptees, refus = {}, []
    for phrase in _PHRASES.split(_normaliser(texte)):
        prox_avant = False
        for clause in _CLAUSES.split(phrase):
            clause = _clause_propre(clause)
            for debut, fin, zone, arr in _mentions(clause, ville):
                ok, raison = _evaluer(clause[:debut].strip(), clause[fin:].strip(), arr, prox_avant)
                extrait = clause[max(0, debut - 25):fin]
                if ok:
                    acceptees.setdefault(zone, f"{raison} « {extrait} »")
                else:
                    refus.append(f"{raison} « {extrait} »")
            prox_avant = prox_avant or bool(_PROXIMITE.search(clause))

    if len(acceptees) > 1:
        return None, "contradiction : " + " / ".join(sorted(acceptees))
    if acceptees:
        return next(iter(acceptees.items()))
    return None, ("refusé : " + refus[0]) if refus else "aucune mention de quartier"


def localiser_par_texte(textes, ville):
    """Premier texte (dans l'ordre donné) qui décide ; une contradiction est
    définitive (pas de repli sur un texte moins prioritaire)."""
    raison = "texte vide"
    for texte in textes:
        zone, r = extraire_zone(texte, ville)
        if zone or r.startswith("contradiction"):
            return zone, r
        if r != "texte vide":
            raison = r
    return None, raison
