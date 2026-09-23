# Séparation affichage carte / archive ML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplifier le statut d'annonce ORA-134 bis (3 états `active`/`a_verifier`/`inactive`, pensé pour une vérification HTTP) en un modèle à 2 états (`active`/`archivee`) piloté uniquement par le diff de scrape — la vérification HTTP est écartée (bloquée par captcha) — et construire un vrai historique de prix par annonce pour permettre le suivi d'évolution de prix par type/quartier dans le temps, sans jamais perdre de données.

**Architecture:** `annonces.db` reste la source de vérité du statut et gagne `premiere_vue`/`derniere_vue` (timestamps) + une nouvelle table `historique_prix` (une ligne par annonce à chaque run pipeline, jamais purgée). `master_immo_final.csv` reste la source de vérité pour la carte/le ML, avec le même statut 2-états fusionné de façon préservante par `clean_immo.py`. Le tier HTTP asynchrone (`verify_annonces_async.py`, DAG `oracle_cleanup_pipeline`) construit ce matin est retiré : inutile et bloqué par captcha.

**Tech Stack:** Python (pandas, sqlite3, Flask), pas de nouvelle dépendance (aiohttp est retiré).

## Global Constraints

- Ne jamais supprimer physiquement une ligne existante de `annonces.db` ou `master_immo_final.csv` — remplacer `inactive` par `archivee`, jamais de `DELETE`.
- `url` est la seule clé stable inter-runs.
- Le statut passe de 3 valeurs (`active`/`a_verifier`/`inactive`) à 2 (`active`/`archivee`) — toute trace du 3ème état et de la logique de vérification HTTP associée doit disparaître du code (constante `STATUTS_VALIDES`, docstrings, filtres, DAG).
- Bascule `active → archivee` avec une marge de grâce : `TTL_JOURS_DERNIER_SCAN` (14 jours, déjà en place) reste le seuil — une annonce absente d'un seul run de scraping n'est pas immédiatement archivée. Pas de nouvelle requête réseau vers les sites sources pour des annonces déjà connues (captcha bloquant, contrainte explicite).
- Les annonces `archivee` restent dans `master_immo_final.csv` et dans le dataset d'entraînement XGBoost (décision déjà actée, inchangée) — seuls les endpoints d'affichage utilisateur filtrent sur `active`.
- Historique de prix : nouvelle table SQLite `historique_prix` dans `annonces.db` (pas de fichier séparé), une ligne par annonce par run pipeline (active ET archivee), jamais purgée.
- Style du repo : commentaires en français expliquant le "pourquoi", docstrings avec référence ORA-XXX (cette epic sera ORA-144, référencer ORA-144 dans les nouveaux commentaires ; ORA-134/ORA-134 bis restent en référence historique là où c'est pertinent), écriture CSV atomique déjà en place dans `clean_immo.py` (`df.to_csv` en fin de `main()`, inchangé par ce plan).

---

## File Structure

| Fichier | Rôle |
|---|---|
| `backend/services/annonces_store.py` | Modifie : `STATUTS_VALIDES` → 2 états, `premiere_vue`/`derniere_vue`, nouvelle table+fonctions `historique_prix`. |
| `backend/tests/test_annonces_store.py` | Modifie : tests adaptés au 2-états + nouvelles colonnes/table. |
| `backend/scripts/clean_immo.py` | Modifie : `step_flag_expired` simplifié (2-états + grâce), `step_sync_annonces_store` étoffé (premiere_vue/derniere_vue, historique_prix). |
| `backend/tests/test_clean_immo.py` | Modifie : tests adaptés au 2-états. |
| `backend/scripts/verify_annonces_async.py` | **Supprime** (tier HTTP obsolète, captcha bloquant). |
| `backend/tests/test_verify_annonces_async.py` | **Supprime**. |
| `Airflow/dags/oracle_cleanup_dag.py` | **Supprime**. |
| `backend/requirements.txt` | Modifie : retire `aiohttp`. |
| `Airflow/Dockerfile` | Modifie : retire `aiohttp`. |
| `backend/app.py` | Modifie : `/api/listings` filtre `statut == 'active'`. |
| `backend/scripts/generate_map.py` | Modifie : même filtre pour la carte statique. |
| `backend/scripts/train_model.py` | Modifie : commentaire mis à jour au vocabulaire 2-états. |
| `backend/services/price_evolution.py` | Crée : agrégation prix moyen par quartier/type/mois à partir de `historique_prix`. |
| `backend/tests/test_price_evolution.py` | Crée. |

---

### Task 1: `annonces_store.py` — statut 2-états, premiere_vue/derniere_vue, table `historique_prix`

**Files:**
- Modify: `backend/services/annonces_store.py`
- Test: `backend/tests/test_annonces_store.py`

**Interfaces:**
- Produces: `STATUTS_VALIDES = {"active", "archivee"}` (remplace le set à 3 valeurs).
- Produces: `init_db()` migre en plus (`ALTER TABLE ... ADD COLUMN` non-destructif, même pattern que `statut`/`derniere_verification`) : `premiere_vue TEXT`, `derniere_vue TEXT`. Crée en plus `CREATE TABLE IF NOT EXISTS historique_prix (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, date_observation TEXT NOT NULL, prix REAL, surface REAL, quartier TEXT, type_local TEXT, statut TEXT NOT NULL)`.
- Produces: `upsert_annonce(..., premiere_vue=None, derniere_vue=None, ...)` — sur INSERT, `premiere_vue` = `derniere_vue` = maintenant si non fournis ; sur UPDATE (conflit url), `premiere_vue` N'EST JAMAIS écrasée par la valeur transmise par l'appelant si une valeur existe déjà en base (préservée via `COALESCE(annonces.premiere_vue, excluded.premiere_vue)` dans le `ON CONFLICT`), `derniere_vue` suit toujours la valeur transmise par l'appelant (normalement "maintenant" à chaque upsert représentant un run pipeline qui voit l'URL, active ou archivee).
- Produces: `record_price_observation(url, prix, surface, quartier, type_local, statut, date_observation=None, db_path=DEFAULT_DB_PATH)` — insère une ligne dans `historique_prix` (jamais d'update/dédoublonnage : une ligne par appel, l'appelant décide de la fréquence). `date_observation` par défaut maintenant (UTC ISO).
- Produces: `list_annonces(..., statut=None, ...)` — défaut (`statut=None`) exclut désormais `archivee` (au lieu de `inactive`) ; un filtre explicite (`"active"` ou `"archivee"`) filtre strictement dessus.
- Produces: `update_statut(...)` — inchangé dans sa forme, mais `statut` doit maintenant être `"active"` ou `"archivee"` (validé contre le nouveau `STATUTS_VALIDES`). Conserve la fonction : elle reste utile pour un futur usage manuel/API, même si `clean_immo.py` (Task 2) l'utilisera moins directement qu'avant (le statut est calculé en amont dans le dataframe puis transmis à `upsert_annonce`, comme aujourd'hui).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_annonces_store.py — remplacer les tests devenus obsolètes
# et en ajouter de nouveaux. Localiser et REMPLACER ces trois tests existants
# (ils testent le 3ème état 'inactive', qui n'existe plus) :
#   - test_list_annonces_excludes_inactive_by_default
#   - test_list_annonces_explicit_statut_filter
#   - test_update_statut_rejects_invalid_value (garder le test, juste changer
#     la valeur invalide utilisée si elle référençait 'inactive' comme exemple
#     valide ailleurs dans le test — vérifier son contenu actuel avant d'éditer)
# par :

    def test_list_annonces_excludes_archivee_by_default(self):
        annonces_store.upsert_annonce(titre="Active", url="https://example.com/a", db_path=self.db_path)
        annonces_store.upsert_annonce(titre="Archivee", url="https://example.com/b", db_path=self.db_path)
        annonces_store.update_statut(url="https://example.com/b", statut="archivee", db_path=self.db_path)

        result = annonces_store.list_annonces(db_path=self.db_path)

        titres = [a["titre"] for a in result["items"]]
        self.assertIn("Active", titres)
        self.assertNotIn("Archivee", titres)

    def test_list_annonces_explicit_statut_filter(self):
        annonces_store.upsert_annonce(titre="Archivee", url="https://example.com/c", db_path=self.db_path)
        annonces_store.update_statut(url="https://example.com/c", statut="archivee", db_path=self.db_path)

        result = annonces_store.list_annonces(statut="archivee", db_path=self.db_path)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["titre"], "Archivee")

# Ajouter à la suite (nouveaux tests pour premiere_vue/derniere_vue) :

    def test_new_annonce_sets_premiere_vue_and_derniere_vue(self):
        annonce = annonces_store.upsert_annonce(
            titre="T2", url="https://example.com/premiere-1", db_path=self.db_path,
        )
        self.assertIsNotNone(annonce["premiere_vue"])
        self.assertIsNotNone(annonce["derniere_vue"])
        self.assertEqual(annonce["premiere_vue"], annonce["derniere_vue"])

    def test_existing_db_without_vue_columns_is_migrated(self):
        conn = annonces_store.get_connection(self.db_path)
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(annonces)")}
        conn.close()
        self.assertIn("premiere_vue", cols)
        self.assertIn("derniere_vue", cols)

    def test_upsert_on_existing_url_preserves_premiere_vue_but_updates_derniere_vue(self):
        first = annonces_store.upsert_annonce(
            titre="T2", url="https://example.com/premiere-2",
            premiere_vue="2026-01-01T00:00:00+00:00", derniere_vue="2026-01-01T00:00:00+00:00",
            db_path=self.db_path,
        )
        second = annonces_store.upsert_annonce(
            titre="T2 mis à jour", url="https://example.com/premiere-2",
            premiere_vue="2026-08-01T00:00:00+00:00", derniere_vue="2026-08-01T00:00:00+00:00",
            db_path=self.db_path,
        )
        self.assertEqual(second["premiere_vue"], "2026-01-01T00:00:00+00:00",
                          "premiere_vue ne doit jamais être écrasée par un upsert ultérieur")
        self.assertEqual(second["derniere_vue"], "2026-08-01T00:00:00+00:00",
                          "derniere_vue doit toujours refléter le dernier upsert")

    def test_historique_prix_table_exists_after_init_db(self):
        conn = annonces_store.get_connection(self.db_path)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        self.assertIn("historique_prix", tables)

    def test_record_price_observation_inserts_a_row(self):
        annonces_store.record_price_observation(
            url="https://example.com/histo-1", prix=850, surface=45,
            quartier="Gerland", type_local="T2", statut="active",
            date_observation="2026-08-07T00:00:00+00:00", db_path=self.db_path,
        )
        conn = annonces_store.get_connection(self.db_path)
        rows = conn.execute("SELECT * FROM historique_prix WHERE url = ?", ("https://example.com/histo-1",)).fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["prix"], 850)
        self.assertEqual(rows[0]["statut"], "active")

    def test_record_price_observation_appends_multiple_rows_for_same_url(self):
        annonces_store.record_price_observation(
            url="https://example.com/histo-2", prix=800, surface=40, quartier="Ainay",
            type_local="T1", statut="active", date_observation="2026-08-01T00:00:00+00:00",
            db_path=self.db_path,
        )
        annonces_store.record_price_observation(
            url="https://example.com/histo-2", prix=820, surface=40, quartier="Ainay",
            type_local="T1", statut="active", date_observation="2026-08-07T00:00:00+00:00",
            db_path=self.db_path,
        )
        conn = annonces_store.get_connection(self.db_path)
        rows = conn.execute(
            "SELECT prix FROM historique_prix WHERE url = ? ORDER BY date_observation", ("https://example.com/histo-2",)
        ).fetchall()
        conn.close()
        self.assertEqual([r["prix"] for r in rows], [800, 820])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_annonces_store.py -v`
Expected: FAIL — `archivee` n'existe pas encore, `premiere_vue`/`derniere_vue`/`historique_prix`/`record_price_observation` n'existent pas.

- [ ] **Step 3: Implement**

```python
# backend/services/annonces_store.py — remplacer la constante

STATUTS_VALIDES = {"active", "archivee"}
```

```python
# backend/services/annonces_store.py — remplacer __all__

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
    "record_price_observation",
]
```

```python
# backend/services/annonces_store.py — remplacer init_db()

def init_db(db_path=DEFAULT_DB_PATH):
    """Crée les tables `annonces`, `clics` et `historique_prix` si elles
    n'existent pas encore (ORA-81, ORA-91, ORA-144), et migre le schéma
    `annonces` de façon non-destructive si nécessaire.

    `url` est NOT NULL UNIQUE (ORA-82) : c'est la clé utilisée par
    `upsert_annonce` pour dédupliquer (ORA-83).

    `statut` (active/archivee), `derniere_verification`, `premiere_vue` et
    `derniere_vue` sont ajoutées par `ALTER TABLE ... ADD COLUMN` si absentes
    plutôt que recréées, pour ne jamais perdre les lignes déjà en base —
    safe à ré-exécuter à chaque démarrage.

    `historique_prix` (ORA-144) : une ligne par annonce à chaque run
    pipeline (`clean_immo.py::step_sync_annonces_store`), jamais purgée —
    c'est l'archive qui permet de calculer une évolution de prix par
    quartier/type dans le temps (cf. `services/price_evolution.py`), même
    pour les annonces devenues `archivee`.
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS historique_prix (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                date_observation TEXT NOT NULL,
                prix REAL,
                surface REAL,
                quartier TEXT,
                type_local TEXT,
                statut TEXT NOT NULL
            )
            """
        )

        existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(annonces)")}
        if "statut" not in existing_columns:
            conn.execute("ALTER TABLE annonces ADD COLUMN statut TEXT NOT NULL DEFAULT 'active'")
        if "derniere_verification" not in existing_columns:
            conn.execute("ALTER TABLE annonces ADD COLUMN derniere_verification TEXT")
        if "premiere_vue" not in existing_columns:
            conn.execute("ALTER TABLE annonces ADD COLUMN premiere_vue TEXT")
        if "derniere_vue" not in existing_columns:
            conn.execute("ALTER TABLE annonces ADD COLUMN derniere_vue TEXT")

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
    premiere_vue=None,
    derniere_vue=None,
    db_path=DEFAULT_DB_PATH,
):
    """Insère une nouvelle annonce, ou met à jour l'annonce existante de même
    `url` (ORA-83 : dédoublonnage par update, pas par skip).

    `images` est une liste de chaînes (urls), sérialisée en JSON.
    `statut` par défaut `"active"` à la création (ORA-134 bis, ORA-144).
    `premiere_vue`/`derniere_vue` (ORA-144) : à la création, `premiere_vue`
    et `derniere_vue` valent la valeur fournie ou "maintenant" si absente.
    Sur une ligne déjà existante, `premiere_vue` n'est JAMAIS écrasée (elle
    représente la toute première apparition connue de l'annonce — un
    `COALESCE` en base la préserve quel que soit ce que l'appelant transmet) ;
    `derniere_vue` suit toujours la valeur transmise par l'appelant.
    Lève `ValueError` si `url` est absente/vide (ORA-82), ou si `statut` est
    fourni mais invalide.
    """
    if not url or not url.strip():
        raise ValueError("url est obligatoire pour enregistrer une annonce")
    if statut is not None and statut not in STATUTS_VALIDES:
        raise ValueError(f"statut invalide : {statut!r} (attendu parmi {sorted(STATUTS_VALIDES)})")

    now_iso = datetime.now(timezone.utc).isoformat()
    date_scraping = date_scraping or now_iso
    images_json = json.dumps(images) if images is not None else None
    statut = statut or "active"
    premiere_vue = premiere_vue or now_iso
    derniere_vue = derniere_vue or now_iso

    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO annonces (titre, prix, surface, ville, quartier, url, date_scraping, images, statut, derniere_verification, premiere_vue, derniere_vue)
            VALUES (:titre, :prix, :surface, :ville, :quartier, :url, :date_scraping, :images, :statut, :derniere_verification, :premiere_vue, :derniere_vue)
            ON CONFLICT(url) DO UPDATE SET
                titre = excluded.titre,
                prix = excluded.prix,
                surface = excluded.surface,
                ville = excluded.ville,
                quartier = excluded.quartier,
                date_scraping = excluded.date_scraping,
                images = excluded.images,
                statut = excluded.statut,
                derniere_verification = excluded.derniere_verification,
                premiere_vue = COALESCE(annonces.premiere_vue, excluded.premiere_vue),
                derniere_vue = excluded.derniere_vue
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
                "premiere_vue": premiere_vue,
                "derniere_vue": derniere_vue,
            },
        )
        conn.commit()
        row = conn.execute("SELECT * FROM annonces WHERE url = ?", (url,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()
```

```python
# backend/services/annonces_store.py — remplacer la ligne par défaut du filtre dans list_annonces()
# (garder le reste de la fonction identique, juste ce commentaire + cette ligne)

    `statut` (ORA-134 bis, ORA-144) : `None` (défaut) exclut uniquement les
    annonces `archivee` (comportement par défaut de l'API publique — on ne
    veut pas rediriger un utilisateur vers une annonce disparue du dernier
    scrape). Une valeur explicite ("active" ou "archivee") filtre strictement
    dessus.
    ...
    else:
        where_clauses.append("statut != 'archivee'")
```

```python
# backend/services/annonces_store.py — ajouter après record_price_observation... (nouvelle fonction, après update_statut())

def record_price_observation(
    url, prix=None, surface=None, quartier=None, type_local=None, statut=None,
    date_observation=None, db_path=DEFAULT_DB_PATH,
):
    """Enregistre une observation de prix pour `url` dans `historique_prix`
    (ORA-144) : une ligne par appel, jamais de déduplication/update — c'est
    une archive append-only. Appelée une fois par annonce à chaque run du
    pipeline (`clean_immo.py::step_sync_annonces_store`), pour `active` et
    `archivee` indifféremment, ce qui permet de calculer une évolution de
    prix par quartier/type dans le temps même pour des annonces disparues du
    dernier scrape (`services/price_evolution.py`).
    """
    date_observation = date_observation or datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO historique_prix (url, date_observation, prix, surface, quartier, type_local, statut)
            VALUES (:url, :date_observation, :prix, :surface, :quartier, :type_local, :statut)
            """,
            {
                "url": url,
                "date_observation": date_observation,
                "prix": prix,
                "surface": surface,
                "quartier": quartier,
                "type_local": type_local,
                "statut": statut,
            },
        )
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_annonces_store.py -v`
Expected: PASS (tous les tests, y compris ceux non modifiés — `_row_to_dict` n'a pas besoin de changer, `dict(row)` renvoie déjà les nouvelles colonnes automatiquement).

- [ ] **Step 5: Commit**

```bash
git add backend/services/annonces_store.py backend/tests/test_annonces_store.py
git commit -m "feat(annonces): statut à 2 états (active/archivee) + premiere_vue/derniere_vue + table historique_prix (ORA-144)"
```

---

### Task 2: `clean_immo.py` — diff de scrape simplifié (2 états) + retrait du tier HTTP

**Files:**
- Modify: `backend/scripts/clean_immo.py`
- Modify: `backend/tests/test_clean_immo.py`
- Delete: `backend/scripts/verify_annonces_async.py`
- Delete: `backend/tests/test_verify_annonces_async.py`
- Delete: `Airflow/dags/oracle_cleanup_dag.py`
- Modify: `backend/requirements.txt` (retire `aiohttp`)
- Modify: `Airflow/Dockerfile` (retire `aiohttp`)

**Interfaces:**
- Consumes: `annonces_store.STATUTS_VALIDES = {"active", "archivee"}`, `annonces_store.upsert_annonce(..., premiere_vue=, derniere_vue=, ...)`, `annonces_store.record_price_observation(...)` (Task 1).
- Produces: `step_flag_expired(df, previous_csv_path=OUTPUT_FINAL_CSV, ttl_days=TTL_JOURS_DERNIER_SCAN, reference_date=None) -> df` simplifié à 2 états, mêmes signature/contrat que la version 3-états qu'elle remplace (même nom de fonction, même appel dans `main()` — pas de renommage).
- Produces: colonnes `statut` (`"active"`/`"archivee"`), `premiere_vue`, `derniere_vue` dans le dataframe retourné (remplace `derniere_verification_http`, qui disparaît — c'était le signal du tier HTTP, maintenant retiré).

- [ ] **Step 1: Supprimer le tier HTTP obsolète**

```bash
git rm backend/scripts/verify_annonces_async.py backend/tests/test_verify_annonces_async.py Airflow/dags/oracle_cleanup_dag.py
```

```
# backend/requirements.txt — retirer la ligne `aiohttp` de la section "Utilitaires"
# (ajoutée ce matin pour verify_annonces_async.py, plus nécessaire)
```

```dockerfile
# Airflow/Dockerfile — retirer aiohttp de la ligne pip install

USER airflow
RUN pip install --no-cache-dir \
    pandas numpy scikit-learn shapely xgboost joblib \
    requests beautifulsoup4 folium
```

- [ ] **Step 2: Write the failing tests — remplacer `test_clean_immo.py`**

Le fichier `backend/tests/test_clean_immo.py` teste actuellement un modèle à 3 états avec vérification HTTP (`a_verifier`, `inactive`, `derniere_verification_http`, recency de vérification HTTP). Remplacer l'intégralité de son contenu par la version 2-états ci-dessous (mêmes imports/setUp/tearDown que l'existant, à conserver tels quels) :

```python
# backend/tests/test_clean_immo.py — remplacer TOUTE la classe StepFlagExpiredTest
# par (garder les imports/sys.path.insert du fichier existant en haut du fichier) :

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

    def test_row_present_in_fresh_scrape_stays_active(self):
        previous = pd.DataFrame({"url": ["https://example.com/vue"], "statut": ["active"]})
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({
            "url": ["https://example.com/vue"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        self.assertEqual(result.iloc[0]["statut"], "active")

    def test_archived_row_reappearing_in_fresh_scrape_resets_to_active(self):
        # ORA-144 : une annonce archivée qui réapparaît dans un scrape frais
        # (ex: relouée puis re-publiée) redevient active — le diff de scrape
        # est la seule source de vérité, pas de vérification HTTP à consulter.
        previous = pd.DataFrame({"url": ["https://example.com/revenue"], "statut": ["archivee"]})
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({
            "url": ["https://example.com/revenue"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        self.assertEqual(result.iloc[0]["statut"], "active")

    def test_stale_active_row_within_grace_period_stays_active(self):
        # Marge de grâce (ttl_days) : une annonce non revue par le scraping
        # depuis moins de ttl_days reste active — absorbe un run de scraping
        # manqué/partiel sans bascule prématurée en archivee.
        previous = pd.DataFrame({"url": ["https://example.com/recent"], "statut": ["active"]})
        previous.to_csv(self.csv_path, index=False)

        recent_date = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=5)).isoformat()
        df = pd.DataFrame({"url": ["https://example.com/recent"], "date_dernier_scan": [recent_date]})

        result = step_flag_expired(df, previous_csv_path=self.csv_path, ttl_days=14)

        self.assertEqual(result.iloc[0]["statut"], "active")

    def test_stale_active_row_beyond_grace_period_becomes_archivee(self):
        previous = pd.DataFrame({"url": ["https://example.com/stale"], "statut": ["active"]})
        previous.to_csv(self.csv_path, index=False)

        old_date = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=20)).isoformat()
        df = pd.DataFrame({"url": ["https://example.com/stale"], "date_dernier_scan": [old_date]})

        result = step_flag_expired(df, previous_csv_path=self.csv_path, ttl_days=14)

        self.assertEqual(len(result), 1, "la ligne ne doit jamais être supprimée du dataframe")
        self.assertEqual(result.iloc[0]["statut"], "archivee")

    def test_row_missing_from_new_scrape_is_kept_and_flagged_archivee(self):
        previous = pd.DataFrame({"url": ["https://example.com/disparue"], "statut": ["active"]})
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({
            "url": ["https://example.com/autre"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        urls = list(result["url"])
        self.assertIn("https://example.com/disparue", urls)
        disparue = result[result["url"] == "https://example.com/disparue"].iloc[0]
        self.assertEqual(disparue["statut"], "archivee")

    def test_already_archivee_row_missing_from_new_scrape_stays_archivee(self):
        previous = pd.DataFrame({"url": ["https://example.com/deja-archivee"], "statut": ["archivee"]})
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({
            "url": ["https://example.com/autre"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        row = result[result["url"] == "https://example.com/deja-archivee"].iloc[0]
        self.assertEqual(row["statut"], "archivee",
                          "une annonce déjà archivee et toujours absente reste archivee, jamais supprimée")

    def test_previous_csv_without_statut_column_preserves_disparues(self):
        previous = pd.DataFrame({"url": ["https://example.com/gone", "https://example.com/kept"]})
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({
            "url": ["https://example.com/kept"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        urls = list(result["url"])
        self.assertIn("https://example.com/gone", urls)
        gone = result[result["url"] == "https://example.com/gone"].iloc[0]
        self.assertEqual(gone["statut"], "archivee")

    def test_premiere_vue_is_preserved_across_runs(self):
        previous = pd.DataFrame({
            "url": ["https://example.com/pv"], "statut": ["active"],
            "premiere_vue": ["2026-01-01T00:00:00+00:00"],
        })
        previous.to_csv(self.csv_path, index=False)

        df = pd.DataFrame({
            "url": ["https://example.com/pv"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        result = step_flag_expired(df, previous_csv_path=self.csv_path)

        self.assertEqual(result.iloc[0]["premiere_vue"], "2026-01-01T00:00:00+00:00")

    def test_premiere_vue_defaults_to_now_for_new_row(self):
        df = pd.DataFrame({
            "url": ["https://example.com/nouvelle"],
            "date_dernier_scan": [pd.Timestamp.now(tz="UTC").isoformat()],
        })

        reference = pd.Timestamp("2026-08-07T12:00:00Z")
        result = step_flag_expired(df, previous_csv_path=self.csv_path, reference_date=reference)

        self.assertTrue(str(result.iloc[0]["premiere_vue"]).startswith("2026-08-07"))

    def test_derniere_vue_updates_when_seen_in_fresh_scrape(self):
        previous = pd.DataFrame({
            "url": ["https://example.com/dv"], "statut": ["active"],
            "premiere_vue": ["2026-01-01T00:00:00+00:00"],
            "derniere_vue": ["2026-01-01T00:00:00+00:00"],
        })
        previous.to_csv(self.csv_path, index=False)

        reference = pd.Timestamp("2026-08-07T12:00:00Z")
        df = pd.DataFrame({"url": ["https://example.com/dv"], "date_dernier_scan": [reference.isoformat()]})

        result = step_flag_expired(df, previous_csv_path=self.csv_path, reference_date=reference)

        self.assertTrue(str(result.iloc[0]["derniere_vue"]).startswith("2026-08-07"))
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_clean_immo.py -v`
Expected: FAIL (statut `'archivee'` inattendu par l'implémentation actuelle à 3 états, `premiere_vue`/`derniere_vue` absentes).

- [ ] **Step 4: Write the implementation — remplacer `step_flag_expired` et sa constante**

```python
# backend/scripts/clean_immo.py — remplacer STATUTS_VALIDES

STATUTS_VALIDES = {"active", "archivee"}
```

```python
# backend/scripts/clean_immo.py — remplacer entièrement step_flag_expired()

def step_flag_expired(df, previous_csv_path=None, ttl_days=None, reference_date=None):
    """Fusionne `df` (résultat frais de data_fusion.py) avec le `master_immo_final.csv`
    du run précédent pour calculer/préserver `statut`, `premiere_vue` et
    `derniere_vue` (ORA-144).

    Modèle à 2 états, piloté uniquement par le diff de scrape (présence/
    absence de l'url dans le scrape courant) — la vérification HTTP
    (ORA-134 bis, `verify_annonces_async.py`) est retirée : bloquée par
    captcha sur SeLoger en pratique, elle ne peut pas servir de source de
    vérité fiable. Aucune requête réseau supplémentaire n'est faite ici.

    Règles de fusion (clé = `url`, seul identifiant stable inter-runs) :
    - Ligne présente dans `df` avec un `date_dernier_scan` récent
      (<= ttl_days) : `statut='active'` — y compris une ligne qui était
      `archivee` (réapparaître dans un scrape est une preuve directe de vie,
      ex: bien relogé/re-publié).
    - Ligne dont le `date_dernier_scan` dépasse `ttl_days` (marge de grâce
      pour absorber un run de scraping manqué/partiel sans bascule
      prématurée), ou absente du scrape courant : `statut='archivee'` —
      jamais supprimée, juste sortie de la vue "active".
    - Ligne absente du scrape courant : conservée quel que soit son statut
      précédent (y compris déjà `archivee`), réinjectée via `disparues`
      ci-dessous — sinon une ligne `archivee` (par construction absente de
      tous les scrapes futurs) disparaîtrait silencieusement de
      `master_immo_final.csv` au run suivant.

    `premiere_vue` : préservée telle quelle depuis le CSV précédent si elle
    existe pour cette url, sinon "maintenant" (première apparition connue).
    `derniere_vue` : mise à jour à "maintenant" si l'url est vue dans le
    scrape courant (`deja_vu`), sinon préservée depuis le CSV précédent
    (une ligne archivee garde la date de sa dernière apparition réelle, pas
    la date du run qui l'a marquée archivee).

    Conservateur par construction : une ligne sans `date_dernier_scan`
    exploitable est traitée comme "non confirmée récemment" (archivee si
    connue précédemment, sinon active par défaut faute d'information pour
    trancher plus fort).
    """
    print("\n🗑️  ETAPE 0 : Calcul du statut (fusion préservante, ORA-144)...")

    if previous_csv_path is None:
        previous_csv_path = OUTPUT_FINAL_CSV
    if ttl_days is None:
        ttl_days = TTL_JOURS_DERNIER_SCAN

    reference_date = reference_date or pd.Timestamp.now(tz='UTC').normalize()
    now_iso = reference_date.isoformat()

    if 'date_dernier_scan' in df.columns:
        dernier_scan = pd.to_datetime(df['date_dernier_scan'], errors='coerce', utc=True)
        age_jours = (reference_date - dernier_scan).dt.days
        vue_recemment = age_jours <= ttl_days  # NaN -> False (pas de preuve de fraîcheur)
    else:
        vue_recemment = pd.Series(False, index=df.index)

    previous_statut = {}
    previous_premiere_vue = {}
    previous_derniere_vue = {}
    previous_df = None
    if os.path.exists(previous_csv_path):
        previous_df = pd.read_csv(previous_csv_path)
        if 'statut' in previous_df.columns and 'url' in previous_df.columns:
            previous_statut = dict(zip(previous_df['url'], previous_df['statut']))
        if 'premiere_vue' in previous_df.columns and 'url' in previous_df.columns:
            previous_premiere_vue = dict(zip(previous_df['url'], previous_df['premiere_vue']))
        if 'derniere_vue' in previous_df.columns and 'url' in previous_df.columns:
            previous_derniere_vue = dict(zip(previous_df['url'], previous_df['derniere_vue']))

    nouveau_statut, nouveau_premiere_vue, nouveau_derniere_vue = [], [], []
    for url, deja_vu in zip(df['url'], vue_recemment):
        ancien = previous_statut.get(url)
        if deja_vu:
            nouveau_statut.append('active')
        else:
            nouveau_statut.append('archivee' if ancien is not None else 'active')

        pv = previous_premiere_vue.get(url)
        nouveau_premiere_vue.append(pv if pd.notna(pv) and pv else now_iso)

        if deja_vu:
            nouveau_derniere_vue.append(now_iso)
        else:
            dv = previous_derniere_vue.get(url)
            nouveau_derniere_vue.append(dv if pd.notna(dv) and dv else now_iso)

    df = df.copy()
    df['statut'] = nouveau_statut
    df['premiere_vue'] = nouveau_premiere_vue
    df['derniere_vue'] = nouveau_derniere_vue

    # Lignes disparues du scrape courant (url absente de `df`), conservées
    # quel que soit leur statut précédent (y compris déjà `archivee`) — une
    # ligne archivee est par définition absente de tous les scrapes futurs ;
    # l'exclure ici la supprimerait silencieusement à chaque run.
    if os.path.exists(previous_csv_path) and previous_df is not None and 'url' in previous_df.columns:
        urls_courantes = set(df['url'])
        disparues = previous_df[~previous_df['url'].isin(urls_courantes)].copy()
        if len(disparues):
            if 'statut' not in disparues.columns:
                disparues['statut'] = 'archivee'
            else:
                disparues['statut'] = 'archivee'
            if 'premiere_vue' not in disparues.columns:
                disparues['premiere_vue'] = now_iso
            if 'derniere_vue' not in disparues.columns:
                disparues['derniere_vue'] = now_iso
            print(f"   ↩️  {len(disparues)} annonce(s) absente(s) du scrape courant, conservée(s) en archivee.")
            df = pd.concat([df, disparues], ignore_index=True, sort=False)

    counts = df['statut'].value_counts().to_dict()
    print(f"   ✅ Statuts : {counts}")
    return df
```

**Note d'implémentation :** contrairement à la version précédente, `disparues['statut']` est toujours mis à `'archivee'` sans condition — puisqu'il n'existe plus de 3ème état (`inactive`) à préserver distinctement de `archivee`, il n'y a plus besoin de la logique conditionnelle `s if s == 'inactive' else 'a_verifier'`.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_clean_immo.py -v`
Expected: PASS

- [ ] **Step 6: Mettre à jour `step_sync_annonces_store` — statut coercé, premiere_vue/derniere_vue transmis, historique_prix enregistré**

```python
# backend/scripts/clean_immo.py — dans step_sync_annonces_store(), remplacer le bloc
# `statut_brut = ...` / `statut = ...` / l'appel upsert_annonce, et ajouter l'appel
# record_price_observation juste après un upsert réussi

        statut_brut = row.get('statut') or 'active'
        statut = statut_brut if statut_brut in STATUTS_VALIDES else 'active'

        try:
            annonces_store.upsert_annonce(
                titre=build_titre(row),
                prix=float(row['prix']) if pd.notna(row.get('prix')) else None,
                surface=float(row['surface']) if pd.notna(row.get('surface')) else None,
                ville=row.get('ville') or None,
                quartier=row.get('quartier') or None,
                url=url,
                images=images,
                statut=statut,
                premiere_vue=row.get('premiere_vue') or None,
                derniere_vue=row.get('derniere_vue') or None,
                db_path=db_path,
            )
            annonces_store.record_price_observation(
                url=url,
                prix=float(row['prix']) if pd.notna(row.get('prix')) else None,
                surface=float(row['surface']) if pd.notna(row.get('surface')) else None,
                quartier=row.get('quartier') or None,
                type_local=row.get('type_local') or None,
                statut=statut,
                db_path=db_path,
            )
            synced += 1
        except ValueError as exc:
            if "url" in str(exc).lower():
                skipped_url += 1
            else:
                skipped_autre += 1
                print(f"   ⚠️  Ligne ignorée (erreur upsert, pas url) : {exc}")
```

**Note :** le statut invalide se coerce désormais vers `'active'` (et non plus `'a_verifier'`, qui n'existe plus) — c'est le choix conservateur équivalent dans le nouveau modèle à 2 états : en cas de valeur corrompue/inattendue, ne pas archiver à tort une annonce potentiellement vivante. Retirer aussi le commentaire "Finding 5" existant au-dessus de ce bloc s'il référence explicitement `a_verifier` (le réécrire pour rester exact vis-à-vis du nouveau comportement, ou le simplifier — au choix de l'implémenteur, tant que le commentaire final est cohérent avec le code qu'il documente).

- [ ] **Step 7: Adapter les tests existants de `step_sync_annonces_store` si nécessaire**

Chercher dans `backend/tests/test_clean_immo_steps.py` les tests qui exercent `step_sync_annonces_store` avec un statut invalide/`a_verifier` explicite (ex: un test qui vérifie la coercion vers `a_verifier`) et les adapter pour attendre `active` à la place, avec le même style de test (mêmes assertions, juste la valeur attendue qui change). Si un test appelle `record_price_observation` implicitement via `step_sync_annonces_store`, ajouter une assertion vérifiant qu'une ligne apparaît dans `historique_prix` après l'appel (connexion directe à `db_path`, `SELECT COUNT(*) FROM historique_prix`).

- [ ] **Step 8: Run the full test suite**

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: PASS (hormis les 3 échecs préexistants sans rapport, PDF/WeasyPrint — `test_app_report_pdf.py`, `test_pdf_report.py`). Les fichiers supprimés à l'étape 1 ne doivent plus apparaître dans la collecte de tests (vérifier qu'aucune erreur d'import résiduelle ne subsiste, ex. un import de `verify_annonces_async` oublié ailleurs).

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat(annonces): diff de scrape à 2 états (active/archivee), retire le tier HTTP (captcha bloquant) (ORA-144)"
```

---

### Task 3: Filtrage affichage (carte + API) + vocabulaire XGBoost

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/scripts/generate_map.py`
- Modify: `backend/scripts/train_model.py`

**Interfaces:**
- Consumes: colonne `statut` (`"active"`/`"archivee"`) de `master_immo_final.csv` (Task 2).

- [ ] **Step 1: `/api/listings`**

```python
# backend/app.py — dans get_listings(), remplacer le bloc de filtrage existant

    # Seules les annonces actives (présentes au dernier scrape, ORA-144)
    # apparaissent sur la carte — les archivees restent dans le dataset pour
    # l'historique de prix côté entraînement (cf. train_model.py) mais ne
    # doivent pas être proposées au clic à un utilisateur.
    if 'statut' in df.columns:
        df = df[df['statut'] == 'active']
```

- [ ] **Step 2: `generate_map.py`**

```python
# backend/scripts/generate_map.py — remplacer le filtre existant (même emplacement,
# juste après la lecture/normalisation de df_immo, cf. code actuel autour de la
# lecture de IMMO_CSV)

            if 'statut' in df_immo.columns:
                avant = len(df_immo)
                df_immo = df_immo[df_immo['statut'] == 'active']
                print(f"   🧹 {avant - len(df_immo)} annonce(s) archivee(s) exclue(s) de la carte statique.")
```

- [ ] **Step 3: `train_model.py` — mettre à jour le commentaire au vocabulaire 2-états**

```python
# backend/scripts/train_model.py — remplacer le commentaire existant (ORA-134 bis)
# juste avant `df = pd.read_csv(data_path)`

# ORA-144 : les annonces marquées `statut='archivee'` (absentes du dernier
# scrape, plus vérifiées par requête HTTP — bloquée par captcha) restent dans
# master_immo_final.csv et donc dans ce dataset d'entraînement — décision
# produit assumée : leur historique de prix reste statistiquement valable
# pour le modèle et permet de capter des tendances. Seuls les endpoints
# d'affichage utilisateur (/api/listings, generate_map.py, /api/annonces)
# filtrent sur statut='active'.
```

- [ ] **Step 4: Test manuel**

Run (backend relancé avec un `master_immo_final.csv` contenant `statut`) : `curl -s http://localhost:5000/api/listings | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"`
Expected : compte égal au nombre de lignes `statut == 'active'`.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/scripts/generate_map.py backend/scripts/train_model.py
git commit -m "feat(annonces): filtre l'affichage sur statut=active, vocabulaire 2-états (ORA-144)"
```

---

### Task 4: Agrégation d'évolution de prix par quartier/type

**Files:**
- Create: `backend/services/price_evolution.py`
- Test: `backend/tests/test_price_evolution.py`

**Interfaces:**
- Consumes: la table `historique_prix` (Task 1), peuplée par `step_sync_annonces_store` (Task 2).
- Produces: `compute_price_trend(quartier=None, type_local=None, granularite="mois", db_path=annonces_store.DEFAULT_DB_PATH) -> list[dict]` — renvoie une liste chronologique de `{"periode": "2026-08", "quartier": ..., "type_local": ..., "prix_moyen": ..., "prix_m2_moyen": ..., "count": ...}`, groupée par période (mois par défaut) et, si fournis, filtrée sur `quartier`/`type_local`. Sans filtre, agrège toutes les combinaisons quartier × type_local × période.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_price_evolution.py

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import annonces_store
from services.price_evolution import compute_price_trend


class ComputePriceTrendTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        annonces_store.init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _record(self, url, prix, surface, quartier, type_local, statut, date_observation):
        annonces_store.record_price_observation(
            url=url, prix=prix, surface=surface, quartier=quartier, type_local=type_local,
            statut=statut, date_observation=date_observation, db_path=self.db_path,
        )

    def test_empty_history_returns_empty_list(self):
        self.assertEqual(compute_price_trend(db_path=self.db_path), [])

    def test_aggregates_by_month_quartier_and_type(self):
        self._record("https://example.com/1", 800, 40, "Gerland", "T2", "active", "2026-06-15T00:00:00+00:00")
        self._record("https://example.com/2", 820, 40, "Gerland", "T2", "active", "2026-06-20T00:00:00+00:00")
        self._record("https://example.com/1", 850, 40, "Gerland", "T2", "active", "2026-07-15T00:00:00+00:00")

        result = compute_price_trend(quartier="Gerland", type_local="T2", db_path=self.db_path)

        self.assertEqual(len(result), 2)
        juin = next(r for r in result if r["periode"] == "2026-06")
        self.assertEqual(juin["count"], 2)
        self.assertAlmostEqual(juin["prix_moyen"], 810.0)
        juillet = next(r for r in result if r["periode"] == "2026-07")
        self.assertEqual(juillet["count"], 1)
        self.assertAlmostEqual(juillet["prix_moyen"], 850.0)

    def test_includes_archivee_observations(self):
        # ORA-144 : l'archive doit inclure l'historique des annonces devenues
        # archivee, pas seulement les active — c'est tout l'intérêt de
        # conserver leur historique de prix plutôt que de les supprimer.
        self._record("https://example.com/gone", 700, 30, "Ainay", "T1", "archivee", "2026-05-10T00:00:00+00:00")

        result = compute_price_trend(quartier="Ainay", type_local="T1", db_path=self.db_path)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["count"], 1)

    def test_filters_by_quartier_and_type_local(self):
        self._record("https://example.com/a", 800, 40, "Gerland", "T2", "active", "2026-06-01T00:00:00+00:00")
        self._record("https://example.com/b", 1200, 60, "Gerland", "T3", "active", "2026-06-01T00:00:00+00:00")
        self._record("https://example.com/c", 750, 35, "Vaise", "T2", "active", "2026-06-01T00:00:00+00:00")

        result = compute_price_trend(quartier="Gerland", type_local="T2", db_path=self.db_path)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["count"], 1)
        self.assertAlmostEqual(result[0]["prix_moyen"], 800.0)

    def test_computes_prix_m2_moyen(self):
        self._record("https://example.com/x", 800, 40, "Gerland", "T2", "active", "2026-06-01T00:00:00+00:00")

        result = compute_price_trend(quartier="Gerland", type_local="T2", db_path=self.db_path)

        self.assertAlmostEqual(result[0]["prix_m2_moyen"], 20.0)

    def test_results_are_chronologically_ordered(self):
        self._record("https://example.com/1", 800, 40, "Gerland", "T2", "active", "2026-08-01T00:00:00+00:00")
        self._record("https://example.com/2", 780, 40, "Gerland", "T2", "active", "2026-05-01T00:00:00+00:00")
        self._record("https://example.com/3", 810, 40, "Gerland", "T2", "active", "2026-06-01T00:00:00+00:00")

        result = compute_price_trend(quartier="Gerland", type_local="T2", db_path=self.db_path)

        self.assertEqual([r["periode"] for r in result], ["2026-05", "2026-06", "2026-08"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_price_evolution.py -v`
Expected: FAIL — le module `services.price_evolution` n'existe pas.

- [ ] **Step 3: Write the implementation**

```python
# backend/services/price_evolution.py
"""
Agrégation de l'évolution de prix par quartier/type de bien dans le temps
(ORA-144), à partir de la table `historique_prix` (services/annonces_store.py)
— une ligne par annonce à chaque run pipeline, incluant les annonces devenues
`archivee` : c'est précisément ce qui permet de calculer une tendance de prix
même pour des biens disparus du dernier scrape (relogés, retirés, loués),
plutôt que de perdre ce signal en les excluant.

Distinct de `services/price_history.py` (ORA-72), qui calcule une tendance à
partir de snapshots complets périodiques du dataset (granularité : un point
par run d'entraînement). Ce module travaille au niveau de chaque annonce
individuelle, avec un historique continu indépendant de la cadence
d'entraînement du modèle.
"""

import sqlite3

from services import annonces_store


def compute_price_trend(quartier=None, type_local=None, db_path=None):
    """Renvoie l'évolution mensuelle du prix moyen (et prix/m² moyen) pour
    `quartier`/`type_local`, à partir de `historique_prix`.

    Sans `quartier`/`type_local`, agrège toutes les observations tous
    quartiers/types confondus. Renvoie une liste chronologique de
    `{"periode": "YYYY-MM", "quartier", "type_local", "prix_moyen",
    "prix_m2_moyen", "count"}` — un point par mois où au moins une
    observation existe pour le filtre demandé. Liste vide si aucune donnée.
    """
    db_path = db_path or annonces_store.DEFAULT_DB_PATH

    where_clauses = ["prix IS NOT NULL"]
    params = {}
    if quartier:
        where_clauses.append("quartier = :quartier")
        params["quartier"] = quartier
    if type_local:
        where_clauses.append("type_local = :type_local")
        params["type_local"] = type_local
    where_sql = " AND ".join(where_clauses)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""
            SELECT
                substr(date_observation, 1, 7) AS periode,
                quartier,
                type_local,
                AVG(prix) AS prix_moyen,
                AVG(CASE WHEN surface > 0 THEN prix * 1.0 / surface END) AS prix_m2_moyen,
                COUNT(*) AS count
            FROM historique_prix
            WHERE {where_sql}
            GROUP BY periode, quartier, type_local
            ORDER BY periode ASC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_price_evolution.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/price_evolution.py backend/tests/test_price_evolution.py
git commit -m "feat(annonces): agrégation d'évolution de prix par quartier/type depuis historique_prix (ORA-144)"
```

---

## Self-Review

**Couverture du spec utilisateur :**
- Statut active/archivée (2 états, pas de vérification HTTP) → Task 1 (DB) + Task 2 (CSV/diff).
- Migration DB non-destructive → Task 1 (`ALTER TABLE ADD COLUMN`, testé sur schéma pré-migration existant, déjà couvert par le pattern hérité de ORA-134 bis).
- Diff de scrape (présent → active + update prix, absent → archivée, pas de requête réseau) → Task 2, `step_flag_expired` simplifié + `step_sync_annonces_store` qui met à jour `prix` à chaque upsert (déjà le comportement de `upsert_annonce`, inchangé).
- Filtrage carte sur active uniquement → Task 3 (`/api/listings`, `generate_map.py`).
- Fichier/table d'archive avec historique de prix, première/dernière apparition → Task 1 (`historique_prix`, `premiere_vue`/`derniere_vue`) + Task 2 (peuplement à chaque run).
- Agrégation évolution de prix par type/quartier → Task 4 (`compute_price_trend`).
- Impact XGBoost tranché (actif + archivé pour l'entraînement, actif seul pour l'affichage) → déjà la décision ORA-135, redocumentée Task 3 Step 3, aucun changement de comportement nécessaire.
- Retrait du tier HTTP bloqué par captcha → Task 2 Step 1 (suppression fichiers + dépendance `aiohttp`).
- Aucune suppression de donnée existante → respecté (aucun `DELETE` sur `annonces.db`/`master_immo_final.csv` dans tout le plan ; seuls des fichiers de CODE du tier HTTP obsolète sont supprimés, avec confirmation explicite de l'utilisateur).

**Aucun placeholder** : chaque step contient du code exécutable réel.

**Cohérence des types/signatures** : `statut` est une chaîne parmi `{"active", "archivee"}` partout (Task 1 définit `STATUTS_VALIDES` dans `annonces_store.py`, Task 2 le duplique localement dans `clean_immo.py` par découplage volontaire déjà établi par ORA-134 bis). `compute_price_trend` renvoie une structure cohérente avec ce que `price_history.py` (ORA-72) renvoie déjà pour `/api/quartier-stats` (même esprit : liste chronologique de points), sans les fusionner (modules distincts, sources de données distinctes — snapshots vs historique par annonce).

---

## Note pour la suite (hors scope de ce plan)

`services/price_history.py` (ORA-72, snapshots périodiques) et le nouveau `services/price_evolution.py` (ORA-144, historique par annonce) coexistent délibérément — le premier alimente déjà `/api/quartier-stats` en production, le second est une nouvelle capacité pas encore branchée à une route API. Si l'utilisateur veut exposer `compute_price_trend` via une nouvelle route HTTP, c'est un travail de suivi séparé, pas fait ici (pas demandé explicitement dans le spec).
