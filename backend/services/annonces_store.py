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
    "get_connection",
    "init_db",
    "upsert_annonce",
    "list_annonces",
    "get_annonce_by_id",
    "log_click",
    "count_clicks",
    "delete_annonce",
]

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "annonces.db"
)

MAX_PER_PAGE = 100


def get_connection(db_path=DEFAULT_DB_PATH):
    """Ouvre une connexion sqlite3 dédiée (pas de partage entre threads/requêtes),
    avec row_factory=Row pour un accès des colonnes par nom."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DEFAULT_DB_PATH):
    """Crée les tables `annonces` et `clics` si elles n'existent pas encore (ORA-81, ORA-91).

    `url` est NOT NULL UNIQUE (ORA-82) : c'est la clé utilisée par
    `upsert_annonce` pour dédupliquer (ORA-83).
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
    db_path=DEFAULT_DB_PATH,
):
    """Insère une nouvelle annonce, ou met à jour l'annonce existante de même
    `url` (ORA-83 : dédoublonnage par update, pas par skip).

    `images` est une liste de chaînes (urls), sérialisée en JSON.
    Lève `ValueError` si `url` est absente/vide (ORA-82).
    """
    if not url or not url.strip():
        raise ValueError("url est obligatoire pour enregistrer une annonce")

    date_scraping = date_scraping or datetime.now(timezone.utc).isoformat()
    images_json = json.dumps(images) if images is not None else None

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO annonces (titre, prix, surface, ville, quartier, url, date_scraping, images)
            VALUES (:titre, :prix, :surface, :ville, :quartier, :url, :date_scraping, :images)
            ON CONFLICT(url) DO UPDATE SET
                titre = excluded.titre,
                prix = excluded.prix,
                surface = excluded.surface,
                ville = excluded.ville,
                quartier = excluded.quartier,
                date_scraping = excluded.date_scraping,
                images = excluded.images
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
            },
        )
        conn.commit()
        row = conn.execute("SELECT * FROM annonces WHERE url = ?", (url,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def list_annonces(ville=None, quartier=None, page=1, per_page=20, db_path=DEFAULT_DB_PATH):
    """Liste paginée des annonces, filtrable par ville et/ou quartier (ORA-84).

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
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    conn = get_connection(db_path)
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM annonces {where_sql}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT * FROM annonces {where_sql}
            ORDER BY id DESC
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


def _row_to_dict(row):
    if row is None:
        return None
    data = dict(row)
    data["images"] = json.loads(data["images"]) if data.get("images") else []
    return data
