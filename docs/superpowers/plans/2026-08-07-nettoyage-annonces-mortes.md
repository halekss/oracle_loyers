# Nettoyage non-destructif des annonces mortes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer la suppression physique des annonces mortes (`prune_dead_annonces.py` / `prune_dead_map_listings.py`, `DELETE` direct) par un statut `active` / `a_verifier` / `inactive` non-destructif, propagé par deux couches — diff de scrape (déjà en place, ORA-134) et vérification HTTP asynchrone (aiohttp, nouvelle) — orchestrées par un DAG Airflow quotidien séparé du pipeline hebdomadaire.

**Architecture:** `master_immo_final.csv` devient la source de vérité du statut (colonne `statut` + `derniere_verification_http`), avec fusion préservante à chaque run de `clean_immo.py` (au lieu d'une régénération complète qui écraserait le statut). `annonces.db` reçoit le statut par synchronisation (déjà existante côté écriture, étendue). Le tier navigateur (Selenium, bloqué à ~100% par CAPTCHA SeLoger constaté en pratique) reste hors Airflow, inchangé.

**Tech Stack:** Python 3.11 (Airflow) / 3.14 (backend local), aiohttp (nouveau), pandas, sqlite3, Flask, Airflow 2.9.3 (BashOperator).

## Global Constraints

- Ne jamais supprimer physiquement une ligne existante de `annonces.db` ou `master_immo_final.csv` dans ce travail — seul un changement de `statut` est permis (le user a explicitement demandé confirmation avant toute suppression de données).
- `url` est la seule clé stable inter-runs (`id_annonce` dans le CSV est ré-indexé à chaque run, `id` SQLite est local à la base) — toute logique de fusion/diff doit clé sur `url`.
- Les annonces `inactive` restent dans le dataset d'entraînement XGBoost (décision confirmée avec l'utilisateur) — seuls les endpoints d'affichage utilisateur (`/api/listings`, `/api/annonces`, carte statique) filtrent.
- Le tier de vérification par navigateur headless (Selenium) reste un script manuel hors Airflow (décision confirmée) — le DAG cleanup ne fait que le tier HTTP rapide (aiohttp).
- Cadence du DAG cleanup : quotidienne, à une heure distincte du DAG hebdomadaire existant (`oracle_annonces_pipeline`, lundi 22h Europe/Paris) pour éviter tout chevauchement d'écriture sur `master_immo_final.csv`.
- Style du repo : commentaires en français expliquant le "pourquoi" (pas le "quoi"), docstrings avec référence ORA-XXX, écriture CSV atomique (`os.replace`, jamais d'écrasement direct).

---

## File Structure

| Fichier | Rôle |
|---|---|
| `backend/services/annonces_store.py` | Modifie : migration non-destructive (`statut`, `derniere_verification`), nouvelle fonction `update_statut`, filtre par défaut dans `list_annonces`. |
| `backend/tests/test_annonces_store.py` | Modifie : tests des nouvelles fonctions/colonnes. |
| `backend/scripts/clean_immo.py` | Modifie : fusion préservante avec le CSV précédent, remplace le drop TTL par un flag `a_verifier`. |
| `backend/tests/test_clean_immo.py` | Modifie (ou crée si absent) : tests de la fusion préservante. |
| `backend/scripts/verify_annonces_async.py` | Crée : vérificateur HTTP asynchrone (aiohttp), tier 2 du nettoyage. |
| `backend/tests/test_verify_annonces_async.py` | Crée : tests du vérificateur (aiohttp mocké). |
| `backend/requirements.txt` | Modifie : ajoute `aiohttp`. |
| `Airflow/Dockerfile` | Modifie : ajoute `aiohttp` à l'image Airflow. |
| `Airflow/dags/oracle_cleanup_dag.py` | Crée : DAG quotidien dédié au nettoyage. |
| `backend/app.py` | Modifie : `/api/listings` exclut `statut == 'inactive'`. |
| `backend/scripts/generate_map.py` | Modifie : exclut `statut == 'inactive'` avant de générer la carte statique. |
| `backend/scripts/train_model.py` | Modifie (commentaire seul) : documente explicitement la décision de garder les `inactive`. |

---

### Task 1: Migration DB non-destructive + statut dans `annonces_store.py`

**Files:**
- Modify: `backend/services/annonces_store.py`
- Test: `backend/tests/test_annonces_store.py`

**Interfaces:**
- Produces: `update_statut(url=None, annonce_id=None, statut=None, derniere_verification=None, db_path=DEFAULT_DB_PATH) -> bool` (True si une ligne a été mise à jour).
- Produces: `STATUTS_VALIDES = {"active", "a_verifier", "inactive"}` (module-level constant, réutilisé par `verify_annonces_async.py` et `clean_immo.py`).
- Produces: `list_annonces(..., statut=None, ...)` — nouveau paramètre optionnel ; `None` (défaut) exclut uniquement `inactive` (comportement par défaut de l'API publique), une valeur explicite filtre strictement dessus.
- Produces: `upsert_annonce(..., statut=None, derniere_verification=None, ...)` — `statut` par défaut `"active"` à l'INSERT ; sur conflit (`ON CONFLICT`), la colonne `statut`/`derniere_verification` suit la valeur transmise par l'appelant (pas de préservation automatique côté DB : la préservation across-run est gérée en amont dans `clean_immo.py`, Task 2, qui est la source de vérité).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_annonces_store.py — ajouter à la fin de la classe AnnoncesStoreTest

    def test_new_annonce_defaults_to_active_status(self):
        annonce = annonces_store.upsert_annonce(
            titre="T2 Gerland", url="https://example.com/annonce-statut-1",
            db_path=self.db_path,
        )
        self.assertEqual(annonce["statut"], "active")
        self.assertIsNone(annonce["derniere_verification"])

    def test_existing_db_without_statut_column_is_migrated(self):
        # Simule une base créée avant l'ajout de la colonne (schéma pré-migration).
        conn = annonces_store.get_connection(self.db_path)
        conn.execute("DROP TABLE annonces")
        conn.execute(
            """
            CREATE TABLE annonces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titre TEXT, prix REAL, surface REAL, ville TEXT, quartier TEXT,
                url TEXT NOT NULL UNIQUE, date_scraping TEXT NOT NULL, images TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO annonces (titre, url, date_scraping) VALUES (?, ?, ?)",
            ("Annonce pré-migration", "https://example.com/pre-migration", "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()
        conn.close()

        annonces_store.init_db(self.db_path)  # doit ALTER TABLE sans lever d'exception

        annonce = annonces_store.get_annonce_by_url("https://example.com/pre-migration", db_path=self.db_path)
        self.assertIsNotNone(annonce, "la ligne pré-migration doit être conservée")
        self.assertEqual(annonce["statut"], "active", "défaut rétroactif sûr pour les lignes existantes")

    def test_update_statut_by_url(self):
        annonces_store.upsert_annonce(titre="T3", url="https://example.com/annonce-statut-2", db_path=self.db_path)
        updated = annonces_store.update_statut(
            url="https://example.com/annonce-statut-2", statut="inactive",
            derniere_verification="2026-08-07T10:00:00+00:00", db_path=self.db_path,
        )
        self.assertTrue(updated)
        annonce = annonces_store.get_annonce_by_url("https://example.com/annonce-statut-2", db_path=self.db_path)
        self.assertEqual(annonce["statut"], "inactive")
        self.assertEqual(annonce["derniere_verification"], "2026-08-07T10:00:00+00:00")

    def test_update_statut_rejects_invalid_value(self):
        annonces_store.upsert_annonce(titre="T3", url="https://example.com/annonce-statut-3", db_path=self.db_path)
        with self.assertRaises(ValueError):
            annonces_store.update_statut(
                url="https://example.com/annonce-statut-3", statut="supprime", db_path=self.db_path,
            )

    def test_update_statut_unknown_url_returns_false(self):
        updated = annonces_store.update_statut(
            url="https://example.com/inconnue", statut="inactive", db_path=self.db_path,
        )
        self.assertFalse(updated)

    def test_list_annonces_excludes_inactive_by_default(self):
        annonces_store.upsert_annonce(titre="Active", url="https://example.com/a", db_path=self.db_path)
        annonces_store.upsert_annonce(titre="Morte", url="https://example.com/b", db_path=self.db_path)
        annonces_store.update_statut(url="https://example.com/b", statut="inactive", db_path=self.db_path)

        result = annonces_store.list_annonces(db_path=self.db_path)

        titres = [a["titre"] for a in result["items"]]
        self.assertIn("Active", titres)
        self.assertNotIn("Morte", titres)

    def test_list_annonces_explicit_statut_filter(self):
        annonces_store.upsert_annonce(titre="Morte", url="https://example.com/c", db_path=self.db_path)
        annonces_store.update_statut(url="https://example.com/c", statut="inactive", db_path=self.db_path)

        result = annonces_store.list_annonces(statut="inactive", db_path=self.db_path)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["titre"], "Morte")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_annonces_store.py -v`
Expected: FAIL — `update_statut` n'existe pas, `statut` absent des lignes renvoyées, colonnes manquantes.

- [ ] **Step 3: Implement the migration + statut support**

```python
# backend/services/annonces_store.py — remplacer __all__ et ajouter la constante

__all__ = [
    "DEFAULT_DB_PATH",
    "STATUTS_VALIDES",
    "get_connection",
    "init_db",
    "upsert_annonce",
    "list_annonces",
    "get_annonce_by_id",
    "get_annonce_by_url",
    "log_click",
    "count_clicks",
    "delete_annonce",
    "update_statut",
]

STATUTS_VALIDES = {"active", "a_verifier", "inactive"}
```

```python
# backend/services/annonces_store.py — remplacer init_db()

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
```

```python
# backend/services/annonces_store.py — remplacer upsert_annonce()

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
```

```python
# backend/services/annonces_store.py — remplacer list_annonces()

def list_annonces(ville=None, quartier=None, statut=None, page=1, per_page=20, db_path=DEFAULT_DB_PATH):
    """Liste paginée des annonces, filtrable par ville et/ou quartier (ORA-84).

    `statut` (ORA-134 bis) : `None` (défaut) exclut uniquement les annonces
    `inactive` (comportement par défaut de l'API publique — on ne veut pas
    rediriger un utilisateur vers une annonce confirmée morte, mais les
    `a_verifier` restent potentiellement valides donc affichées). Une valeur
    explicite ("active", "a_verifier" ou "inactive") filtre strictement dessus.

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
```

```python
# backend/services/annonces_store.py — ajouter après delete_annonce()

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_annonces_store.py -v`
Expected: PASS (tous les tests, y compris les préexistants — `_row_to_dict` renvoie déjà toutes les colonnes via `dict(row)`, donc `statut`/`derniere_verification` apparaissent automatiquement, aucune modification nécessaire côté `_row_to_dict`).

- [ ] **Step 5: Vérifier l'impact sur `app.py` (les appelants existants de `list_annonces`/`upsert_annonce` restent compatibles — nouveaux paramètres tous optionnels)**

Run: `cd backend && .venv/bin/python -m pytest tests/ -k "annonces or app" -v`
Expected: PASS — `app.py` appelle `annonces_store.list_annonces(ville=..., quartier=..., page=..., per_page=..., db_path=...)` sans `statut` explicite, donc bénéficie automatiquement du filtre par défaut (exclusion des `inactive`) sans changement de code dans `app.py` pour cet endpoint.

- [ ] **Step 6: Commit**

```bash
git add backend/services/annonces_store.py backend/tests/test_annonces_store.py
git commit -m "feat(annonces): statut non-destructif (active/a_verifier/inactive) dans annonces.db"
```

---

### Task 2: Fusion préservante dans `clean_immo.py` (remplace le drop TTL)

**Files:**
- Modify: `backend/scripts/clean_immo.py`
- Test: `backend/tests/test_clean_immo.py` (créer si absent — vérifier d'abord)

**Interfaces:**
- Consumes: rien de Task 1 directement (CSV et DB restent découplés à ce stade — Task 2 ne touche que le CSV).
- Produces: `step_flag_expired(df, previous_csv_path=OUTPUT_FINAL_CSV, ttl_days=TTL_JOURS_DERNIER_SCAN, reference_date=None) -> df` — remplace `step_prune_expired` dans `main()`. Ajoute/fusionne les colonnes `statut` et `derniere_verification_http` dans `df`. Ne retire plus aucune ligne.
- Produces: colonnes `statut` (str, une des `STATUTS_VALIDES` — dupliquée en constante locale pour ne pas faire dépendre `clean_immo.py`, qui tourne aussi sous Airflow sans `backend/services` forcément sur le PYTHONPATH de la même façon, de `annonces_store` au-delà de ce qui existe déjà) et `derniere_verification_http` (str ISO ou vide) que `step_sync_annonces_store` (Task 1's `upsert_annonce`) consomme ensuite.

- [ ] **Step 1: Vérifier l'absence de tests existants pour `clean_immo.py`**

Run: `ls backend/tests/test_clean_immo.py 2>/dev/null || echo "absent"`

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_clean_immo.py — nouveau fichier

import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from scripts.clean_immo import step_flag_expired


class StepFlagExpiredTest(unittest.TestCase):
    def setUp(self):
        fd, self.csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        os.remove(self.csv_path)  # le fichier n'existe pas encore = premier run

    def tearDown(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)

    def test_first_run_all_rows_default_active(self):
        df = pd.DataFrame({
            "url": ["https://example.com/1", "https://example.com/2"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()] * 2,
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        self.assertListEqual(list(result["statut"]), ["active", "active"])

    def test_previously_inactive_row_is_preserved_across_runs(self):
        # Simule un CSV précédent où l'url 'dead' a déjà été marquée inactive
        # par verify_annonces_async.py (Task 3).
        previous = pd.DataFrame({
            "url": ["https://example.com/dead"],
            "statut": ["inactive"],
            "derniere_verification_http": ["2026-08-01T00:00:00+00:00"],
        })
        previous.to_csv(self.csv_path, index=False)

        # Le run courant re-fusionne des données brutes fraîches ne contenant
        # PAS cette colonne statut (comme le fait réellement data_fusion.py).
        df = pd.DataFrame({
            "url": ["https://example.com/dead"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        self.assertEqual(result.iloc[0]["statut"], "inactive",
                          "le statut inactive confirmé ne doit pas être écrasé par une re-fusion")

    def test_reappearing_row_resets_to_active(self):
        # Une url 'a_verifier' (TTL dépassé sans confirmation morte) qui
        # réapparaît dans un scrape frais (date_dernier_scan récente) est
        # une preuve forte qu'elle est de nouveau active.
        previous = pd.DataFrame({
            "url": ["https://example.com/revenue"],
            "statut": ["a_verifier"],
            "derniere_verification_http": [""],
        })
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({
            "url": ["https://example.com/revenue"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        self.assertEqual(result.iloc[0]["statut"], "active")

    def test_stale_active_row_flagged_a_verifier_not_dropped(self):
        previous = pd.DataFrame({"url": ["https://example.com/stale"], "statut": ["active"]})
        previous.to_csv(self.csv_path, index=False)

        old_date = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=20)).isoformat()
        df = pd.DataFrame({"url": ["https://example.com/stale"], "date_dernier_scan": [old_date]})

        result = step_flag_expired(df, previous_csv_path=self.csv_path, ttl_days=14)

        self.assertEqual(len(result), 1, "la ligne ne doit plus être supprimée du dataframe")
        self.assertEqual(result.iloc[0]["statut"], "a_verifier")

    def test_row_missing_from_new_scrape_is_kept_and_flagged(self):
        # ORA-134 bis, étape 3.1 du spec utilisateur : une url absente du
        # scrape courant (introuvable dans `df`) mais présente dans le run
        # précédent doit être conservée avec statut a_verifier, pas perdue.
        previous = pd.DataFrame({"url": ["https://example.com/disparue"], "statut": ["active"]})
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({"url": ["https://example.com/autre"], "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()]})

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        urls = list(result["url"])
        self.assertIn("https://example.com/disparue", urls)
        disparue = result[result["url"] == "https://example.com/disparue"].iloc[0]
        self.assertEqual(disparue["statut"], "a_verifier")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_clean_immo.py -v`
Expected: FAIL — `step_flag_expired` n'existe pas encore.

- [ ] **Step 4: Write the implementation**

```python
# backend/scripts/clean_immo.py — remplacer step_prune_expired() par step_flag_expired()

STATUTS_VALIDES = {"active", "a_verifier", "inactive"}


def step_flag_expired(df, previous_csv_path=OUTPUT_FINAL_CSV, ttl_days=TTL_JOURS_DERNIER_SCAN, reference_date=None):
    """Fusionne `df` (résultat frais de data_fusion.py) avec le `master_immo_final.csv`
    du run précédent pour calculer/préserver la colonne `statut` (ORA-134 bis).

    Remplace l'ancien `step_prune_expired`, qui excluait purement et simplement
    du dataframe les lignes dont `date_dernier_scan` dépassait `ttl_days` — un
    ré-entraînement hebdomadaire du pipeline complet aurait alors effacé le
    travail du DAG de nettoyage quotidien (`verify_annonces_async.py`, qui
    marque `inactive` sans jamais supprimer de ligne). Ici, aucune ligne n'est
    supprimée : on ne fait que calculer/reporter le `statut`.

    Règles de fusion (clé = `url`, seul identifiant stable inter-runs — voir
    Global Constraints du plan ORA-134 bis) :
    - Ligne absente du CSV précédent (première apparition) : `statut='active'`.
    - Ligne déjà `inactive` dans le CSV précédent : reste `inactive` (une
      confirmation de mort par vérification HTTP n'est jamais écrasée par une
      re-fusion — seul `verify_annonces_async.py` peut la faire repasser
      `active` s'il la re-confirme vivante).
    - Ligne présente dans `df` (le scrape frais) avec un `date_dernier_scan`
      récent (<= ttl_days) : `statut='active'` — réapparaître dans un scrape
      est une preuve directe de vie, y compris pour une ligne qui était
      `a_verifier`.
    - Ligne dont le `date_dernier_scan` dépasse `ttl_days` (non revue par le
      scraping depuis trop longtemps), ou absente du scrape courant mais
      présente précédemment et pas déjà `inactive` : `statut='a_verifier'` —
      candidate pour `verify_annonces_async.py`, jamais supprimée ici.

    Conservateur par construction, comme l'ancien `step_prune_expired` : une
    ligne sans `date_dernier_scan` exploitable est traitée comme "non
    confirmée récemment" (a_verifier si elle a un statut précédent, sinon
    active par défaut faute d'information pour trancher plus fort).
    """
    print("\n🗑️  ETAPE 0 : Calcul du statut (fusion préservante, ORA-134 bis)...")

    reference_date = reference_date or pd.Timestamp.now(tz='UTC').normalize()

    if 'date_dernier_scan' in df.columns:
        dernier_scan = pd.to_datetime(df['date_dernier_scan'], errors='coerce', utc=True)
        age_jours = (reference_date - dernier_scan).dt.days
        vue_recemment = age_jours <= ttl_days  # NaN -> False (pas de preuve de fraîcheur)
    else:
        vue_recemment = pd.Series(False, index=df.index)

    previous_statut = {}
    if os.path.exists(previous_csv_path):
        previous_df = pd.read_csv(previous_csv_path)
        if 'statut' in previous_df.columns and 'url' in previous_df.columns:
            previous_statut = dict(zip(previous_df['url'], previous_df['statut']))

    nouveau_statut = []
    for url, deja_vu in zip(df['url'], vue_recemment):
        ancien = previous_statut.get(url)
        if ancien == 'inactive':
            nouveau_statut.append('inactive')
        elif deja_vu:
            nouveau_statut.append('active')
        elif ancien is not None:
            nouveau_statut.append('a_verifier')
        else:
            nouveau_statut.append('active')
    df = df.copy()
    df['statut'] = nouveau_statut

    # Lignes disparues du scrape courant (url absente de `df`) mais connues
    # précédemment et pas déjà inactive : conservées avec statut a_verifier
    # plutôt que perdues (ORA-134 bis, étape 3.1 — "toute annonce absente du
    # nouveau scrape passe en à vérifier, pas supprimée directement").
    if os.path.exists(previous_csv_path) and 'url' in previous_df.columns:
        urls_courantes = set(df['url'])
        disparues = previous_df[
            ~previous_df['url'].isin(urls_courantes)
            & (previous_df.get('statut', pd.Series(dtype=object)) != 'inactive')
        ].copy()
        if len(disparues):
            disparues['statut'] = disparues['statut'].apply(lambda s: s if s == 'inactive' else 'a_verifier')
            print(f"   ↩️  {len(disparues)} annonce(s) absente(s) du scrape courant, conservée(s) en a_verifier.")
            df = pd.concat([df, disparues], ignore_index=True, sort=False)

    counts = df['statut'].value_counts().to_dict()
    print(f"   ✅ Statuts : {counts}")
    return df
```

```python
# backend/scripts/clean_immo.py — dans main(), remplacer l'appel

    df = step_flag_expired(df)  # remplace : df = step_prune_expired(df)
```

**Note d'implémentation :** `disparues` peut apporter des colonnes que `df` n'a pas encore reçues (géocodage, quartier, etc., calculées par les étapes suivantes) — comme ces étapes (`step_geocoding`, `step_quartiers`, `step_types`, `step_features`) tournent sur `df` complet après `step_flag_expired`, elles recalculeront ces colonnes pour les lignes réintroduites aussi (`step_geocoding` gère déjà le cas de coordonnées manquantes via génération par jitter). Vérifier lors de l'implémentation que `step_ids` (ré-indexation) n'est pas perturbée par les colonnes supplémentaires — elle ne dépend que de `len(df)`, donc aucun impact attendu.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_clean_immo.py -v`
Expected: PASS

- [ ] **Step 6: Mettre à jour `step_sync_annonces_store` pour transmettre le statut**

```python
# backend/scripts/clean_immo.py — dans step_sync_annonces_store(), au niveau de l'appel upsert_annonce

            annonces_store.upsert_annonce(
                titre=build_titre(row),
                prix=float(row['prix']) if pd.notna(row.get('prix')) else None,
                surface=float(row['surface']) if pd.notna(row.get('surface')) else None,
                ville=row.get('ville') or None,
                quartier=row.get('quartier') or None,
                url=url,
                images=images,
                statut=row.get('statut') or 'active',
                derniere_verification=row.get('derniere_verification_http') or None,
                db_path=db_path,
            )
```

- [ ] **Step 7: Run the full test suite for clean_immo + annonces_store**

Run: `cd backend && .venv/bin/python -m pytest tests/test_clean_immo.py tests/test_annonces_store.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/scripts/clean_immo.py backend/tests/test_clean_immo.py
git commit -m "feat(annonces): fusion préservante du statut dans clean_immo.py (remplace le drop TTL destructif)"
```

---

### Task 3: Vérificateur HTTP asynchrone (`verify_annonces_async.py`)

**Files:**
- Create: `backend/scripts/verify_annonces_async.py`
- Test: `backend/tests/test_verify_annonces_async.py`
- Modify: `backend/requirements.txt` (ajoute `aiohttp`)

**Interfaces:**
- Consumes: `backend.scripts.prune_dead_annonces.looks_like_soft_404(html_text) -> bool` (réutilisé tel quel — une seule source de vérité pour les patterns de soft-404, y compris les patterns SeLoger déjà en place).
- Consumes: `backend.services.annonces_store.update_statut(...)`, `STATUTS_VALIDES` (Task 1).
- Produces: `async def check_url_status_async(url, session, timeout=10) -> bool | None` (True=mort confirmé, False=vivant, None=ambigu — même contrat que `check_url_status` synchrone existant, pour rester cohérent).
- Produces: `async def verify_annonces(csv_path=MASTER_CSV_PATH, db_path=ANNONCES_DB_PATH, concurrency=5, ttl_days=15, dry_run=False) -> dict` avec clés `{"checked", "confirmed_dead", "reconfirmed_alive", "still_ambiguous", "network_errors"}`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_verify_annonces_async.py

import asyncio
import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import verify_annonces_async
from services import annonces_store


class CheckUrlStatusAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_returns_true_on_404(self):
        session = MagicMock()
        response = AsyncMock()
        response.status = 404
        response.__aenter__.return_value = response
        response.__aexit__.return_value = False
        session.get.return_value = response

        result = await verify_annonces_async.check_url_status_async("https://example.com/x", session)

        self.assertTrue(result)

    async def test_returns_true_on_soft_404_text(self):
        session = MagicMock()
        response = AsyncMock()
        response.status = 200
        response.text = AsyncMock(return_value="<div>Cette annonce a été supprimée</div>")
        response.__aenter__.return_value = response
        response.__aexit__.return_value = False
        session.get.return_value = response

        result = await verify_annonces_async.check_url_status_async("https://example.com/x", session)

        self.assertTrue(result)

    async def test_returns_false_on_live_page(self):
        session = MagicMock()
        response = AsyncMock()
        response.status = 200
        response.text = AsyncMock(return_value="<div>T2 - 850€/mois</div>")
        response.__aenter__.return_value = response
        response.__aexit__.return_value = False
        session.get.return_value = response

        result = await verify_annonces_async.check_url_status_async("https://example.com/x", session)

        self.assertFalse(result)

    async def test_returns_none_on_network_error(self):
        import aiohttp
        session = MagicMock()
        session.get.side_effect = aiohttp.ClientError("boom")

        result = await verify_annonces_async.check_url_status_async("https://example.com/x", session)

        self.assertIsNone(result)


class VerifyAnnoncesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fd, self.csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        annonces_store.init_db(self.db_path)

        pd.DataFrame({
            "url": ["https://example.com/dead", "https://example.com/alive", "https://example.com/ambiguous"],
            "statut": ["a_verifier", "a_verifier", "a_verifier"],
        }).to_csv(self.csv_path, index=False)

    def tearDown(self):
        for path in (self.csv_path, self.db_path):
            if os.path.exists(path):
                os.remove(path)

    async def test_confirmed_dead_updates_csv_and_db_without_deleting_rows(self):
        async def fake_checker(url, session, timeout=10):
            return {"https://example.com/dead": True, "https://example.com/alive": False,
                    "https://example.com/ambiguous": None}[url]

        annonces_store.upsert_annonce(url="https://example.com/dead", statut="a_verifier", db_path=self.db_path)

        stats = await verify_annonces_async.verify_annonces(
            csv_path=self.csv_path, db_path=self.db_path, checker=fake_checker,
        )

        result_df = pd.read_csv(self.csv_path)
        self.assertEqual(len(result_df), 3, "aucune ligne ne doit être supprimée")
        statuts = dict(zip(result_df["url"], result_df["statut"]))
        self.assertEqual(statuts["https://example.com/dead"], "inactive")
        self.assertEqual(statuts["https://example.com/alive"], "active")
        self.assertEqual(statuts["https://example.com/ambiguous"], "a_verifier")

        self.assertEqual(stats["confirmed_dead"], 1)
        self.assertEqual(stats["reconfirmed_alive"], 1)
        self.assertEqual(stats["still_ambiguous"], 1)

        annonce = annonces_store.get_annonce_by_url("https://example.com/dead", db_path=self.db_path)
        self.assertEqual(annonce["statut"], "inactive")

    async def test_dry_run_does_not_write(self):
        async def fake_checker(url, session, timeout=10):
            return True

        original_mtime = os.path.getmtime(self.csv_path)
        await verify_annonces_async.verify_annonces(
            csv_path=self.csv_path, db_path=self.db_path, checker=fake_checker, dry_run=True,
        )

        self.assertEqual(os.path.getmtime(self.csv_path), original_mtime)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verify_annonces_async.py -v`
Expected: FAIL — `scripts.verify_annonces_async` n'existe pas.

- [ ] **Step 3: Add aiohttp to requirements**

```
# backend/requirements.txt — ajouter dans la section "Utilitaires"
aiohttp
```

Run: `cd backend && .venv/bin/pip install aiohttp`

- [ ] **Step 4: Write the implementation**

```python
# backend/scripts/verify_annonces_async.py
"""
Vérification HTTP asynchrone des annonces à statut incertain (ORA-134 bis,
tier 2 du nettoyage non-destructif — complète la fusion préservante de
clean_immo.py, Task 2). Contrairement à prune_dead_annonces.py/
prune_dead_map_listings.py (ORA-134, suppression physique), ce script ne
supprime jamais de ligne : il met uniquement à jour la colonne `statut`.

Cible : les annonces de master_immo_final.csv dont le statut est
`a_verifier`, ou `active` mais dont `derniere_verification_http` dépasse
`ttl_days` (re-vérification périodique même d'une annonce jugée active, pour
détecter une disparition qui ne serait pas encore passée par la fusion
diff-scrape de clean_immo.py).

aiohttp + asyncio.Semaphore pour un rate limiting raisonnable (concurrence
plafonnée, pas de rafale sur les sites sources) — remplace le
`time.sleep(random.uniform(...))` séquentiel des scripts ORA-134 par un
throttling concurrent équivalent en esprit mais bien plus rapide sur le
volume total.

Met à jour master_immo_final.csv (source de vérité du statut, atomique) puis
synchronise annonces.db (consommé par /api/annonces) pour le même run — pas
besoin d'attendre le pipeline hebdomadaire pour que l'API reflète le
nettoyage quotidien.

Usage :
    python backend/scripts/verify_annonces_async.py [--dry-run] [--concurrency N] [--ttl-days N]
"""
import argparse
import asyncio
import logging
import os
import random
import sys

import aiohttp
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.prune_dead_annonces import looks_like_soft_404, REQUEST_HEADERS  # noqa: E402
from services import annonces_store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MASTER_CSV_PATH = os.path.join(backend_dir, "data", "master_immo_final.csv")
ANNONCES_DB_PATH = annonces_store.DEFAULT_DB_PATH

DEFAULT_CONCURRENCY = 5
DEFAULT_TTL_DAYS = 15
DEFAULT_TIMEOUT_SECONDS = 10
DEAD_STATUS_CODES = {404, 410}


async def check_url_status_async(url, session, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Version asynchrone de check_url_status (prune_dead_annonces.py) : même
    contrat (True=mort, False=vivant, None=ambigu), même détection soft-404
    (looks_like_soft_404, réutilisée telle quelle — une seule source de vérité
    pour les patterns de contenu 'annonce supprimée' entre les tiers sync et async)."""
    try:
        async with session.get(
            url, headers=REQUEST_HEADERS, timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
        ) as response:
            if response.status in DEAD_STATUS_CODES:
                return True
            if response.status == 200:
                text = await response.text()
                if looks_like_soft_404(text):
                    return True
                return False
            logger.warning("Statut ambigu pour %s (HTTP %s) : conservée par prudence.", url, response.status)
            return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.warning("Erreur réseau pour %s (%s) : conservée par prudence.", url, exc)
        return None


def _rows_to_verify(df, ttl_days, reference_date=None):
    """Sélectionne les lignes à vérifier : statut a_verifier, ou active avec
    derniere_verification_http absente/dépassant ttl_days."""
    reference_date = reference_date or pd.Timestamp.now(tz='UTC')
    if 'derniere_verification_http' in df.columns:
        derniere_verif = pd.to_datetime(df['derniere_verification_http'], errors='coerce', utc=True)
        age_jours = (reference_date - derniere_verif).dt.days
        active_stale = (df['statut'] == 'active') & (age_jours.isna() | (age_jours > ttl_days))
    else:
        active_stale = df['statut'] == 'active'
    return df[(df['statut'] == 'a_verifier') | active_stale].index


async def verify_annonces(
    csv_path=MASTER_CSV_PATH,
    db_path=ANNONCES_DB_PATH,
    concurrency=DEFAULT_CONCURRENCY,
    ttl_days=DEFAULT_TTL_DAYS,
    dry_run=False,
    checker=check_url_status_async,
):
    """Vérifie les annonces éligibles (cf. `_rows_to_verify`) et met à jour leur
    `statut` dans master_immo_final.csv (jamais de suppression de ligne) puis
    dans annonces.db. Renvoie les compteurs de la passe."""
    df = pd.read_csv(csv_path)
    if 'statut' not in df.columns:
        df['statut'] = 'active'
    if 'derniere_verification_http' not in df.columns:
        df['derniere_verification_http'] = ''

    to_check = _rows_to_verify(df, ttl_days)
    logger.info("%s annonce(s) éligible(s) à la vérification HTTP.", len(to_check))

    stats = {"checked": 0, "confirmed_dead": 0, "reconfirmed_alive": 0, "still_ambiguous": 0, "network_errors": 0}
    semaphore = asyncio.Semaphore(concurrency)
    now_iso = pd.Timestamp.now(tz='UTC').isoformat()

    async def _check_one(idx, url):
        async with semaphore:
            await asyncio.sleep(random.uniform(0.1, 0.3))  # jitter, évite une rafale synchronisée
            status = await checker(url, session)
            return idx, status

    async with aiohttp.ClientSession() as session:
        tasks = [_check_one(idx, df.at[idx, 'url']) for idx in to_check]
        results = await asyncio.gather(*tasks)

    for idx, status in results:
        stats["checked"] += 1
        if status is True:
            df.at[idx, 'statut'] = 'inactive'
            df.at[idx, 'derniere_verification_http'] = now_iso
            stats["confirmed_dead"] += 1
            logger.info("Confirmée morte : %s", df.at[idx, 'url'])
        elif status is False:
            df.at[idx, 'statut'] = 'active'
            df.at[idx, 'derniere_verification_http'] = now_iso
            stats["reconfirmed_alive"] += 1
        else:
            df.at[idx, 'derniere_verification_http'] = now_iso  # évite un re-check immédiat en boucle
            stats["still_ambiguous"] += 1
            stats["network_errors"] += 1

    logger.info(
        "Terminé : %s vérifiées, %s confirmées mortes, %s re-confirmées vivantes, %s toujours ambiguës (dont %s erreurs réseau).",
        stats["checked"], stats["confirmed_dead"], stats["reconfirmed_alive"],
        stats["still_ambiguous"], stats["network_errors"],
    )

    if not dry_run and len(to_check) > 0:
        tmp_path = f"{csv_path}.tmp"
        df.to_csv(tmp_path, index=False)
        os.replace(tmp_path, csv_path)

        for idx, status in results:
            if status is None:
                continue
            annonces_store.update_statut(
                url=df.at[idx, 'url'],
                statut=df.at[idx, 'statut'],
                derniere_verification=df.at[idx, 'derniere_verification_http'],
                db_path=db_path,
            )

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Vérifie et logue sans rien modifier.")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Requêtes HTTP simultanées max.")
    parser.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS, help="Âge max avant re-vérification d'une annonce active.")
    args = parser.parse_args()
    asyncio.run(verify_annonces(dry_run=args.dry_run, concurrency=args.concurrency, ttl_days=args.ttl_days))
```

**Note :** `REQUEST_HEADERS` doit être exporté par `prune_dead_annonces.py` (déjà défini au niveau module — vérifier qu'il ne commence pas par `_` et est donc importable tel quel ; c'est le cas dans le code actuel).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_verify_annonces_async.py -v`
Expected: PASS

- [ ] **Step 6: Test manuel en dry-run contre les données réelles**

Run: `cd backend && .venv/bin/python scripts/verify_annonces_async.py --dry-run --concurrency 5`
Expected: tourne sans exception, logue des compteurs cohérents avec le nombre de lignes `a_verifier`/`active` périmées dans `master_immo_final.csv` actuel (690 lignes, dont ~380 SeLoger déjà `a_verifier` d'après le nettoyage de ce matin — une fois Task 2 exécutée pour peupler la colonne `statut`, cf. dépendance ci-dessous).

**Dépendance avec l'existant :** `master_immo_final.csv` n'a pas encore de colonne `statut` tant que Task 2 n'a pas tourné une fois en conditions réelles (le prochain run de `clean_immo.py`, ou un run manuel de validation). Documenter dans le ticket Linear correspondant qu'un run manuel de `clean_immo.py` (ou a minima de `step_flag_expired` isolément) est nécessaire avant la première exécution utile de `verify_annonces_async.py` en production.

- [ ] **Step 7: Commit**

```bash
git add backend/scripts/verify_annonces_async.py backend/tests/test_verify_annonces_async.py backend/requirements.txt
git commit -m "feat(annonces): vérificateur HTTP asynchrone non-destructif (aiohttp, tier 2 ORA-134 bis)"
```

---

### Task 4: DAG Airflow "cleanup" quotidien

**Files:**
- Create: `Airflow/dags/oracle_cleanup_dag.py`
- Modify: `Airflow/Dockerfile`

**Interfaces:**
- Consumes: `backend/scripts/verify_annonces_async.py` (Task 3) en CLI via `BashOperator`.

- [ ] **Step 1: Add aiohttp to the Airflow image**

```dockerfile
# Airflow/Dockerfile — remplacer la ligne pip install

USER airflow
RUN pip install --no-cache-dir \
    pandas numpy scikit-learn shapely xgboost joblib \
    requests beautifulsoup4 folium aiohttp
```

- [ ] **Step 2: Write the DAG**

```python
# Airflow/dags/oracle_cleanup_dag.py
"""
L'Oracle des Loyers — DAG Cleanup (ORA-134 bis)

Vérification HTTP asynchrone quotidienne des annonces à statut incertain
(`a_verifier`, ou `active` périmées) — tier 2 du nettoyage non-destructif.
Ne supprime jamais de ligne, met uniquement à jour la colonne `statut`
(active/a_verifier/inactive) de master_immo_final.csv puis annonces.db.

Volontairement séparé de oracle_annonces_pipeline (hebdomadaire, lundi 22h) :
cadence différente (quotidienne vs hebdomadaire) et ce DAG ne doit pas être
bloqué par la durée du pipeline ML complet (fusion + features + entraînement).
Exécuté à 3h du matin (Europe/Paris), en dehors du créneau du pipeline
principal, pour éviter tout chevauchement d'écriture sur master_immo_final.csv.

Ne couvre que le tier HTTP rapide (aiohttp) : le tier navigateur headless
(Selenium, pour les 403/CAPTCHA constatés sur SeLoger) reste un script manuel
hors Airflow (scripts/recheck_dead_annonces.py, scripts/.venv) — décision
délibérée pour ne pas alourdir l'image Airflow avec Chrome/Selenium,
cohérente avec le choix déjà fait pour le pipeline principal.
"""

from datetime import timedelta
import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator

BACKEND_SCRIPTS = "/opt/airflow/backend/scripts"

default_args = {
    "owner": "aymeric",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="oracle_cleanup_pipeline",
    default_args=default_args,
    description="Vérification HTTP asynchrone des annonces à statut incertain — cadence quotidienne",
    schedule="0 3 * * *",
    start_date=pendulum.datetime(2026, 8, 8, tz="Europe/Paris"),
    catchup=False,
    tags=["oracle", "etl", "immo", "cleanup"],
) as dag:

    step_verify = BashOperator(
        task_id="verify_annonces_async",
        bash_command=f"cd {BACKEND_SCRIPTS} && python verify_annonces_async.py --concurrency 5 --ttl-days 15",
    )
```

- [ ] **Step 3: Vérifier que le DAG s'importe sans erreur**

Run: `cd Airflow && docker compose -f ../docker-compose.yml exec airflow-webserver airflow dags list 2>/dev/null | grep oracle_cleanup_pipeline`
Expected: la ligne `oracle_cleanup_pipeline` apparaît (si l'environnement Airflow Docker tourne — sinon, valider a minima par import Python direct : `cd Airflow/dags && python -c "import oracle_cleanup_dag"` échouera localement faute du package `airflow` hors conteneur, c'est attendu — la vraie validation se fait dans le conteneur).

- [ ] **Step 4: Commit**

```bash
git add Airflow/dags/oracle_cleanup_dag.py Airflow/Dockerfile
git commit -m "feat(airflow): DAG cleanup quotidien pour la vérification HTTP asynchrone (ORA-134 bis)"
```

---

### Task 5: Filtrage des annonces `inactive` côté affichage (API + carte)

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/scripts/generate_map.py`
- Modify: `backend/scripts/train_model.py` (commentaire seul — pas de changement de comportement)

**Interfaces:**
- Consumes: colonne `statut` de `master_immo_final.csv` (Task 2).

- [ ] **Step 1: Filtrer `/api/listings` (carte dynamique)**

```python
# backend/app.py — dans get_listings(), remplacer

    df = data_loader.get_data()
    if df is None:
        return jsonify([])

    # Une annonce confirmée morte par le nettoyage (ORA-134 bis) ne doit plus
    # apparaître sur la carte, même si elle reste dans le dataset (gardée pour
    # l'historique de prix côté entraînement — cf. train_model.py).
    if 'statut' in df.columns:
        df = df[df['statut'] != 'inactive']

    # On renvoie les colonnes nécessaires uniquement et on gère les NaN
    data = df[['latitude', 'longitude', 'prix', 'type_local', 'quartier']].fillna('').to_dict(orient='records')
    return jsonify(data)
```

- [ ] **Step 2: Filtrer `generate_map.py` (carte statique pré-rendue)**

```python
# backend/scripts/generate_map.py — juste après la lecture de df_immo (ligne ~215)

            df_immo = pd.read_csv(IMMO_CSV, sep=None, engine='python')
            if 'statut' in df_immo.columns:
                avant = len(df_immo)
                df_immo = df_immo[df_immo['statut'] != 'inactive']
                print(f"   🧹 {avant - len(df_immo)} annonce(s) inactive(s) exclue(s) de la carte statique.")
```

(Vérifier lors de l'implémentation l'indentation exacte et la variable de sortie utilisée juste après cette ligne dans le fichier réel — insérer immédiatement après le `pd.read_csv`, avant toute utilisation ultérieure de `df_immo`.)

- [ ] **Step 3: Documenter la décision XGBoost dans `train_model.py`**

```python
# backend/scripts/train_model.py — juste avant `df = pd.read_csv(data_path)`

# ORA-134 bis : les annonces marquées `statut='inactive'` (confirmées mortes
# côté site source) restent dans master_immo_final.csv et donc dans ce
# dataset d'entraînement — décision produit assumée : leur prix historique
# reste statistiquement valable pour le modèle même si le lien source a
# expiré. Seuls les endpoints d'affichage utilisateur (/api/listings,
# generate_map.py, /api/annonces) filtrent les inactive.
```

- [ ] **Step 4: Test manuel — vérifier que le endpoint filtre bien**

Run (après avoir relancé le backend avec un `master_immo_final.csv` contenant une colonne `statut`) : `curl -s http://localhost:5000/api/listings | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"`
Expected : compte inférieur ou égal au nombre total de lignes de `master_immo_final.csv`, cohérent avec le nombre de lignes `!= 'inactive'`.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/scripts/generate_map.py backend/scripts/train_model.py
git commit -m "feat(annonces): exclut les annonces inactive de l'affichage (carte + API), conservées pour l'entraînement"
```

---

## Self-Review

**Couverture du spec utilisateur :**
- Statut active/inactive/à vérifier + timestamp dernière vérification → Task 1 (DB) + Task 2 (CSV).
- Migration DB non-destructive → Task 1, Step 3 (`ALTER TABLE ADD COLUMN`, testé sur un schéma pré-migration).
- Diff de scrape (absent du nouveau scrape → à vérifier) → déjà en place côté scrapers (`DerniereVue`, commit `a52d063`) + Task 2 gère explicitement le cas "ligne disparue du scrape courant".
- Vérification HTTP async + rate limiting → Task 3 (`aiohttp` + `asyncio.Semaphore`).
- Détection contenu "annonce expirée" sur 200 → Task 3, réutilise `looks_like_soft_404`.
- DAG Airflow séparé, cadence quotidienne, logging clair (checked/inactive/erreurs) → Task 4 + les logs de `verify_annonces` (Task 3, Step 4).
- Filtrage frontend des inactive → Task 5 (`/api/listings`, carte statique) ; `/api/annonces` déjà couvert par le filtre par défaut de `list_annonces` (Task 1).
- Décision XGBoost → tranchée avec l'utilisateur (garder), documentée Task 5 Step 3.
- Aucune suppression de donnée existante → respecté sur toute la plan (`update_statut` remplace `delete_annonce` dans le flow courant ; `delete_annonce` n'est pas supprimé du code mais n'est plus appelé par les nouveaux scripts).

**Aucun placeholder** : chaque step contient du code exécutable réel, pas de TODO.

**Cohérence des types/signatures** : `statut` est une chaîne parmi `STATUTS_VALIDES` partout (Task 1 définit la constante, Task 2 la duplique localement par découplage volontaire des imports Airflow/backend documenté en commentaire, Task 3 l'importe de `annonces_store`). `check_url_status_async` suit le même contrat `True/False/None` que `check_url_status` (sync, déjà existant) pour rester prévisible.

---

## Prochaines étapes après ce plan (hors scope, à netifier séparément si besoin)

- Une fois Task 2 tournée une première fois en conditions réelles, `master_immo_final.csv` aura sa colonne `statut` peuplée (défaut `active` pour les 690 lignes actuelles, `a_verifier` pour les URLs déjà identifiées ambiguës par le nettoyage manuel de ce matin si on choisit de les faire correspondre manuellement — sinon elles repartiront à `active` faute d'historique, et seront re-signalées `a_verifier` au prochain passage du TTL. À trancher au moment de l'exécution si vous voulez réinjecter l'état déjà observé aujourd'hui.).
- `prune_dead_annonces.py` / `recheck_dead_annonces.py` / `prune_dead_map_listings.py` (suppression physique) restent dans le repo, inchangés — non supprimés par ce plan (hors scope explicite : "ne supprime aucune donnée existante sans confirmation"), mais devraient être dépréciés/documentés comme "legacy, non utilisés par le flow courant" dans un futur ticket, une fois le nouveau système validé en production.
