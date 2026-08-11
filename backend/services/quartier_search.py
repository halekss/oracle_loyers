"""Résolution d'une recherche utilisateur (texte libre) en un sous-ensemble
du DataFrame immo — partagée par /api/quartier-stats, /api/quartier-historique
et price_history.py, pour que les deux endpoits appliquent la même règle
(ORA-71 POC : bornage par ville active + recherche par nom de ville entière).

S'appuie sur le matching flou partagé (services.text_matching.match_quartier,
ORA-110/ORA-111 : tolérance aux fautes de frappe + suggestions "vouliez-vous
dire...") pour la résolution du nom de quartier lui-même, une fois le
DataFrame borné à la ville active.
"""

from services.text_matching import match_quartier


def resolve_quartier_filter(df, quartier_input, ville=None):
    """Sous-ensemble de `df` correspondant à la recherche `quartier_input`,
    et les infos de matching associées.

    - Bornée à `ville` si fournie (ex: empêche "Ainay" de remonter quand
      l'utilisateur est sur l'onglet Lille) — recherche non bornée sur
      toutes les villes si `ville` est absent (compatibilité avec un client
      qui ne l'envoie pas encore).
    - Si `quartier_input` correspond exactement (insensible à la casse) au
      nom d'une ville connue dans les données (`df['ville']`), c'est une
      recherche par ville entière : renvoie TOUTES les annonces de cette
      ville, pas une correspondance de nom de quartier.
    - Sinon, résolution floue (tolérance aux fautes de frappe, suggestions)
      via match_quartier, au sein du sous-ensemble borné par `ville`.

    Renvoie (filtered_df, match_info). `match_info` a la même forme que
    match_quartier() (found/match/score/suggestions), avec une clé
    supplémentaire `is_city_search` (True pour une recherche par ville
    entière, jamais accompagnée d'un `match` de quartier).

    Le bornage par ville et la recherche par ville entière sont ignorés si
    `df` n'a pas de colonne `ville` (jeu de données à une seule ville, ex:
    certains fixtures de test) : on retombe sur une résolution de quartier
    non bornée plutôt que de planter.
    """
    has_ville_column = 'ville' in df.columns

    scoped = df
    if ville and has_ville_column:
        scoped = scoped[scoped['ville'].str.lower() == ville.strip().lower()]

    villes_connues = set(df['ville'].dropna().str.lower().unique()) if has_ville_column else set()
    quartier_norm = quartier_input.strip().lower()

    if quartier_norm in villes_connues:
        filtered = scoped[scoped['ville'].str.lower() == quartier_norm]
        return filtered, {
            "found": True, "match": None, "score": None, "suggestions": [],
            "is_city_search": True,
        }

    known_quartiers = scoped['quartier'].dropna().unique().tolist()
    match = match_quartier(quartier_input, known_quartiers)
    match["is_city_search"] = False

    if not match["found"]:
        return scoped.iloc[0:0], match

    filtered = scoped[scoped['quartier'] == match["match"]]
    return filtered, match
