import re
import unicodedata

from rapidfuzz import fuzz, process

# ORA-109 : seuils de tolérance aux fautes de frappe. score_cutoff détermine
# quand on considère un quartier "trouvé" ; suggestion_cutoff (plus bas) fixe
# la barre en dessous de laquelle un quartier n'est même plus suggéré.
DEFAULT_MATCH_SCORE_CUTOFF = 75
DEFAULT_SUGGESTION_SCORE_CUTOFF = 50
DEFAULT_MAX_SUGGESTIONS = 3


def normalize_text(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def compact_text(value):
    return re.sub(r"[^a-z0-9]+", "", normalize_text(value))


def searchable_text(value):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", normalize_text(value))).strip()


def match_quartier(
    query,
    known_quartiers,
    score_cutoff=DEFAULT_MATCH_SCORE_CUTOFF,
    suggestion_cutoff=DEFAULT_SUGGESTION_SCORE_CUTOFF,
    max_suggestions=DEFAULT_MAX_SUGGESTIONS,
):
    """Fait correspondre `query` (texte libre, éventuellement fautif ou noyé
    dans une phrase) à l'un des quartiers de `known_quartiers`, avec tolérance
    aux fautes de frappe (rapidfuzz).

    Renvoie {"found": bool, "match": str|None, "score": float|None,
    "suggestions": [str, ...]}. `suggestions` reste vide si aucun quartier
    n'est raisonnablement proche : permet un "vouliez-vous dire..." explicite
    plutôt qu'un échec silencieux quand `found` est False.
    """
    normalized_query = normalize_text(query).strip()
    candidates = {str(q): normalize_text(q) for q in known_quartiers if str(q).strip()}

    if not normalized_query or not candidates:
        return {"found": False, "match": None, "score": None, "suggestions": []}

    ranked = process.extract(normalized_query, candidates, scorer=fuzz.WRatio, limit=max_suggestions)
    ranked.sort(key=lambda item: item[1], reverse=True)

    best_value, best_score, best_key = ranked[0]
    if best_score >= score_cutoff:
        return {"found": True, "match": best_key, "score": best_score, "suggestions": []}

    suggestions = [key for _, score, key in ranked if score >= suggestion_cutoff]
    return {"found": False, "match": None, "score": None, "suggestions": suggestions}


def resolve_quartier(query, known_quartiers, score_cutoff=DEFAULT_MATCH_SCORE_CUTOFF):
    """Résout `query` vers le libellé canonique d'un quartier de
    `known_quartiers`, ou None si aucun n'est raisonnablement proche
    (ORA-110). Point d'entrée partagé par toute route qui matche un quartier
    saisi par l'utilisateur contre les quartiers connus du dataset."""
    return match_quartier(query, known_quartiers, score_cutoff=score_cutoff)["match"]
