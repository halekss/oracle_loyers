"""ORA-195 : règle UNIQUE de détection des annonces suspectes (outliers),
partagée par tout le projet — annonces_store.py (SQLite, badge "Donnée
douteuse" + tri en fin de liste), clean_immo.py (pipeline ETL), data_loader.py
(médianes/estimations/comparables/historique) et train_model.py (exclusion de
l'entraînement).

Ne supprime jamais une annonce : signale seulement (`suspect` + `raison`),
à charge de l'appelant d'exclure (agrégats/entraînement) ou d'afficher quand
même en le signalant (liste Annonces).

`detect_outlier` reste volontairement pure (pas de pandas) pour rester
importable depuis annonces_store.py, qui n'a pas cette dépendance.
"""

PRIX_M2_MIN = 6.0
PRIX_M2_MAX = 60.0
SURFACE_MIN = 9.0
SURFACE_MAX_HORS_T4 = 250.0
LOYER_MIN = 200.0
T1_SURFACE_MAX = 60.0
T2_SURFACE_MIN = 20.0

T4_LABEL = 'Grand (T4+)'
T1_LABEL = 'Studio/T1'
T2_LABEL = 'T2'


def _compute_prix_m2(prix, surface):
    if prix is None or surface is None or surface <= 0:
        return None
    return prix / surface


def detect_outlier(prix, surface, type_local=None, prix_m2=None):
    """Renvoie `(suspect: bool, raison: str | None)` pour UNE annonce.

    `prix`/`surface` : `None` si inconnu (jamais NaN — l'appelant pandas
    normalise via `flag_dataframe`). `prix_m2` : si déjà connu (colonne dédiée
    du CSV), utilisé tel quel plutôt que recalculé.

    Règles évaluées dans un ordre fixe, la première qui matche fait foi (une
    annonce n'a besoin que d'UNE raison, pas de toutes celles qui s'appliquent)."""
    if prix_m2 is None:
        prix_m2 = _compute_prix_m2(prix, surface)

    if prix_m2 is not None and (prix_m2 < PRIX_M2_MIN or prix_m2 > PRIX_M2_MAX):
        return True, f"Prix/m² hors norme ({prix_m2:.1f} €/m², attendu {PRIX_M2_MIN:g}-{PRIX_M2_MAX:g} €/m²)"

    if surface is not None:
        if surface < SURFACE_MIN:
            return True, f"Surface trop petite ({surface:g} m² < {SURFACE_MIN:g} m²)"
        if type_local != T4_LABEL and surface > SURFACE_MAX_HORS_T4:
            return True, f"Surface trop grande pour {type_local or 'ce type'} ({surface:g} m² > {SURFACE_MAX_HORS_T4:g} m²)"

    if prix is not None and prix < LOYER_MIN:
        return True, f"Loyer trop bas ({prix:g} € < {LOYER_MIN:g} €)"

    if surface is not None:
        if type_local == T1_LABEL and surface > T1_SURFACE_MAX:
            return True, f"Surface incohérente pour un {T1_LABEL} ({surface:g} m² > {T1_SURFACE_MAX:g} m²)"
        if type_local == T2_LABEL and surface < T2_SURFACE_MIN:
            return True, f"Surface incohérente pour un {T2_LABEL} ({surface:g} m² < {T2_SURFACE_MIN:g} m²)"

    return False, None


def flag_dataframe(df):
    """Version vectorisée de `detect_outlier` pour un DataFrame pandas
    (clean_immo.py, data_loader.py, train_model.py) : renvoie une COPIE de
    `df` avec les colonnes `suspect` (bool) et `suspect_reason` (str|None)
    ajoutées/écrasées — ne mute jamais l'original."""
    import pandas as pd  # import local : ce module doit rester utilisable sans pandas côté annonces_store.py

    has_prix_m2 = 'prix_m2' in df.columns

    def _row(row):
        surface = row.get('surface')
        surface = None if pd.isna(surface) else surface
        prix = row.get('prix')
        prix = None if pd.isna(prix) else prix
        type_local = row.get('type_local')
        type_local = None if pd.isna(type_local) else type_local
        prix_m2 = None
        if has_prix_m2:
            raw_prix_m2 = row.get('prix_m2')
            prix_m2 = None if pd.isna(raw_prix_m2) else raw_prix_m2
        return detect_outlier(prix, surface, type_local, prix_m2=prix_m2)

    # Liste Python plutôt que `df.apply(..., axis=1)` : pandas tente
    # d'étaler un tuple renvoyé par ligne en DataFrame à 2 colonnes (au lieu
    # d'une Series de tuples), et convertit silencieusement les `None` de
    # `suspect_reason` en NaN — une liste évite les deux pièges.
    results = [_row(row) for _, row in df.iterrows()]
    df = df.copy()
    df['suspect'] = [r[0] for r in results]
    df['suspect_reason'] = [r[1] for r in results]
    return df


def exclude_suspects(df):
    """Renvoie `df` (colonnes inchangées) sans ses lignes suspectes — pour les
    appelants qui veulent un jeu de données "propre" sans se soucier du
    marquage (médianes/estimations/écarts/comparables/historique/
    entraînement, ORA-195). `None`/vide renvoyé tel quel."""
    if df is None or df.empty:
        return df
    flagged = flag_dataframe(df)
    return flagged[~flagged['suspect']].drop(columns=['suspect', 'suspect_reason'])
