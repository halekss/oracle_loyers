"""
Store SQLite pour la table `annonces` (ORA-81/82/83).

Persiste les annonces normalisées (titre, prix, surface, ville, quartier, url,
date de scraping, images) indépendamment du CSV `master_immo_final.csv` utilisé
par le pipeline ML : ce store sert de source de vérité pour les futures routes
de consultation d'annonces (GET /api/annonces, GET /api/annonces/:id).

`url` est la clé de dédoublonnage (ORA-82 : champ obligatoire, contrainte
NOT NULL UNIQUE) : `upsert_annonce` met à jour l'annonce existante plutôt que
de la dupliquer ou de l'ignorer quand son url a déjà été vue (ORA-83).
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

__all__ = [
    "DEFAULT_DB_PATH",
    "STATUTS_VALIDES",
    "get_connection",
    "init_db",
    "upsert_annonce",
    "list_annonces",
    "get_annonce_by_id",
    "log_click",
    "count_clicks",
    "delete_annonce",
    "update_statut",
]

STATUTS_VALIDES = {"active", "a_verifier", "inactive"}

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "annonces.db"
)

MAX_PER_PAGE = 100

# ORA-127 : tri optionnel de la liste paginée, whitelist stricte (clé publique
# -> colonne réelle) pour ne jamais interpoler une colonne arbitraire dans le SQL.
SORT_COLUMNS = {
    "prix": "prix",
    "surface": "surface",
    "date": "date_scraping",
}


def get_connection(db_path=DEFAULT_DB_PATH):
    """Ouvre une connexion sqlite3 dédiée (pas de partage entre threads/requêtes),
    avec row_factory=Row pour un accès des colonnes par nom."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DEFAULT_DB_PATH):
    """Crée les tables `annonces` et `clics` si elles n'existent pas encore (ORA-81, ORA-91),
    et migre le schéma `annonces` de façon non-destructive si nécessaire (ORA-134 bis :
    statut + traçabilité, remplace la suppression physique des annonces mortes).

    `url` est NOT NULL UNIQUE (ORA-82) : c'est la clé utilisée par
    `upsert_annonce` pour dédupliquer (ORA-83).

    `statut` (active/a_verifier/inactive) et `derniere_verification` sont ajoutées
    par `ALTER TABLE ... ADD COLUMN` si absentes plutôt que recréées, pour ne
    jamais perdre les lignes déjà en base — safe à ré-exécuter à chaque démarrage.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS annonces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titre TEXT,
                prix REAL,
                surface REAL,
                ville TEXT,
                quartier TEXT,
                url TEXT NOT NULL UNIQUE,
                date_scraping TEXT NOT NULL,
                images TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                annonce_id INTEGER NOT NULL,
                clicked_at TEXT NOT NULL,
                FOREIGN KEY (annonce_id) REFERENCES annonces(id)
            )
            """
        )

        existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(annonces)")}
        if "statut" not in existing_columns:
            # Défaut 'active' pour les lignes déjà en base : conservateur (on ne
            # les marque pas inactive sans vérification), cohérent avec le
            # comportement précédent où leur seule présence en base valait "active".
            conn.execute("ALTER TABLE annonces ADD COLUMN statut TEXT NOT NULL DEFAULT 'active'")
        if "derniere_verification" not in existing_columns:
            conn.execute("ALTER TABLE annonces ADD COLUMN derniere_verification TEXT")

        conn.commit()
    finally:
        conn.close()


def upsert_annonce(
    titre=None,
    prix=None,
    surface=None,
    ville=None,
    quartier=None,
    url=None,
    images=None,
    date_scraping=None,
    statut=None,
    derniere_verification=None,
    db_path=DEFAULT_DB_PATH,
):
    """Insère une nouvelle annonce, ou met à jour l'annonce existante de même
    `url` (ORA-83 : dédoublonnage par update, pas par skip).

    `images` est une liste de chaînes (urls), sérialisée en JSON.
    `statut` par défaut `"active"` à la création (ORA-134 bis) ; sur une ligne
    déjà existante, la valeur transmise par l'appelant remplace l'ancienne —
    la préservation du statut entre deux runs successifs est la responsabilité
    de l'appelant (`clean_immo.py` transmet le statut déjà fusionné, cf. Task 2
    du plan ORA-134 bis), pas de ce store.
    Lève `ValueError` si `url` est absente/vide (ORA-82), ou si `statut` est fourni
    mais invalide.
    """
    if not url or not url.strip():
        raise ValueError("url est obligatoire pour enregistrer une annonce")
    if statut is not None and statut not in STATUTS_VALIDES:
        raise ValueError(f"statut invalide : {statut!r} (attendu parmi {sorted(STATUTS_VALIDES)})")

    date_scraping = date_scraping or datetime.now(timezone.utc).isoformat()
    images_json = json.dumps(images) if images is not None else None
    statut = statut or "active"

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO annonces (titre, prix, surface, ville, quartier, url, date_scraping, images, statut, derniere_verification)
            VALUES (:titre, :prix, :surface, :ville, :quartier, :url, :date_scraping, :images, :statut, :derniere_verification)
            ON CONFLICT(url) DO UPDATE SET
                titre = excluded.titre,
                prix = excluded.prix,
                surface = excluded.surface,
                ville = excluded.ville,
                quartier = excluded.quartier,
                date_scraping = excluded.date_scraping,
                images = excluded.images,
                statut = excluded.statut,
                derniere_verification = excluded.derniere_verification
            """,
            {
                "titre": titre,
                "prix": prix,
                "surface": surface,
                "ville": ville,
                "quartier": quartier,
                "url": url,
                "date_scraping": date_scraping,
                "images": images_json,
                "statut": statut,
                "derniere_verification": derniere_verification,
            },
        )
        conn.commit()
        row = conn.execute("SELECT * FROM annonces WHERE url = ?", (url,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def list_annonces(ville=None, quartier=None, statut=None, page=1, per_page=20, sort=None, order="desc", db_path=DEFAULT_DB_PATH):
    """Liste paginée des annonces, filtrable par ville et/ou quartier (ORA-84).

    `statut` (ORA-134 bis) : `None` (défaut) exclut uniquement les annonces
    `inactive` (comportement par défaut de l'API publique — on ne veut pas
    rediriger un utilisateur vers une annonce confirmée morte, mais les
    `a_verifier` restent potentiellement valides donc affichées). Une valeur
    explicite ("active", "a_verifier" ou "inactive") filtre strictement dessus.

    `sort` (ORA-127, optionnel) : une des clés de `SORT_COLUMNS` ("prix",
    "surface", "date"). Toute autre valeur est ignorée silencieusement (le
    tri par défaut, id DESC = plus récemment inséré d'abord, s'applique).
    `order` : "asc" ou "desc" (défaut), n'a d'effet que si `sort` est fourni.
    `id DESC` est toujours ajouté en tie-breaker pour un ordre stable entre
    annonces de même prix/surface/date.

    Renvoie {"items": [...], "page", "per_page", "total", "total_pages"}.
    """
    page = max(1, page)
    per_page = max(1, min(per_page, MAX_PER_PAGE))

    where_clauses = []
    params = {}
    if ville:
        where_clauses.append("ville = :ville")
        params["ville"] = ville
    if quartier:
        where_clauses.append("quartier = :quartier")
        params["quartier"] = quartier
    if statut:
        where_clauses.append("statut = :statut")
        params["statut"] = statut
    else:
        where_clauses.append("statut != 'inactive'")
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sort_column = SORT_COLUMNS.get(sort)
    order_sql = "ASC" if order == "asc" else "DESC"
    order_by_sql = f"ORDER BY {sort_column} {order_sql}, id DESC" if sort_column else "ORDER BY id DESC"

    conn = get_connection(db_path)
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM annonces {where_sql}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT * FROM annonces {where_sql}
            {order_by_sql}
            LIMIT :limit OFFSET :offset
            """,
            {**params, "limit": per_page, "offset": (page - 1) * per_page},
        ).fetchall()
    finally:
        conn.close()

    total_pages = (total + per_page - 1) // per_page if total else 0

    return {
        "items": [_row_to_dict(row) for row in rows],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }


def get_annonce_by_id(annonce_id, db_path=DEFAULT_DB_PATH):
    """Renvoie l'annonce correspondant à `annonce_id`, ou None si introuvable (ORA-85)."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM annonces WHERE id = ?", (annonce_id,)).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def get_annonce_by_url(url, db_path=DEFAULT_DB_PATH):
    """Renvoie l'annonce correspondant à `url` (contrainte UNIQUE), ou None
    si introuvable. Utilisé par generate_map.py (ORA-107) pour résoudre
    l'id SQLite d'un marker carte à partir de l'URL déjà présente dans le
    CSV, sans dupliquer le tracking de clic entre React et la carte."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM annonces WHERE url = ?", (url,)).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def log_click(annonce_id, clicked_at=None, db_path=DEFAULT_DB_PATH):
    """Journalise un clic sortant vers l'annonce `annonce_id` (ORA-91).

    Utilisé pour tracker les redirections vers le site source, et alimenter
    le compteur de vues (ORA-92, `count_clicks`).
    """
    clicked_at = clicked_at or datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO clics (annonce_id, clicked_at) VALUES (?, ?)",
            (annonce_id, clicked_at),
        )
        conn.commit()
    finally:
        conn.close()


def count_clicks(annonce_id, db_path=DEFAULT_DB_PATH):
    """Nombre de clics enregistrés pour `annonce_id` (ORA-92)."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM clics WHERE annonce_id = ?", (annonce_id,)
        ).fetchone()
    finally:
        conn.close()
    return row[0]


def delete_annonce(url=None, annonce_id=None, db_path=DEFAULT_DB_PATH):
    """Retire une annonce (et ses clics associés) du store, par `url` ou `annonce_id`
    (ORA-134 : nettoyage des annonces confirmées mortes/introuvables sur le site source).

    Exactement un des deux doit être fourni. Renvoie True si une ligne a été supprimée,
    False si aucune annonce ne correspondait (suppression déjà faite / url inconnue).
    """
    if (url is None) == (annonce_id is None):
        raise ValueError("fournir exactement un de url ou annonce_id")

    conn = get_connection(db_path)
    try:
        if annonce_id is None:
            row = conn.execute("SELECT id FROM annonces WHERE url = ?", (url,)).fetchone()
            if row is None:
                return False
            annonce_id = row["id"]

        conn.execute("DELETE FROM clics WHERE annonce_id = ?", (annonce_id,))
        cursor = conn.execute("DELETE FROM annonces WHERE id = ?", (annonce_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_statut(url=None, annonce_id=None, statut=None, derniere_verification=None, db_path=DEFAULT_DB_PATH):
    """Met à jour uniquement le statut (et la date de dernière vérification
    HTTP) d'une annonce, par `url` ou `annonce_id` (ORA-134 bis — remplace la
    suppression physique de `delete_annonce` pour le nettoyage courant).

    Exactement un des deux (`url`/`annonce_id`) doit être fourni. Renvoie True
    si une ligne a été mise à jour, False si aucune annonce ne correspondait.
    Lève `ValueError` si `statut` est absent ou invalide.
    """
    if (url is None) == (annonce_id is None):
        raise ValueError("fournir exactement un de url ou annonce_id")
    if statut not in STATUTS_VALIDES:
        raise ValueError(f"statut invalide : {statut!r} (attendu parmi {sorted(STATUTS_VALIDES)})")

    derniere_verification = derniere_verification or datetime.now(timezone.utc).isoformat()

    conn = get_connection(db_path)
    try:
        if annonce_id is not None:
            cursor = conn.execute(
                "UPDATE annonces SET statut = ?, derniere_verification = ? WHERE id = ?",
                (statut, derniere_verification, annonce_id),
            )
        else:
            cursor = conn.execute(
                "UPDATE annonces SET statut = ?, derniere_verification = ? WHERE url = ?",
                (statut, derniere_verification, url),
            )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def _row_to_dict(row):
    if row is None:
        return None
    data = dict(row)
    data["images"] = json.loads(data["images"]) if data.get("images") else []
    return data
