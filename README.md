# 🔮 L'Oracle des Loyers

> *"Ce T2 est cher, mais c'est le prix à payer pour être à 30m d'un café de spécialité sans entendre les cris de l'école voisine."*

**L'Oracle des Loyers** est une application immobilière intelligente (et un peu cynique) capable d'estimer la "Vraie Valeur" d'un bien à Lyon.
Au-delà des données classiques (surface, prix), l'Oracle croise les données avec **"Les 4 Cavaliers"** de l'environnement urbain pour affiner ses prédictions et ses conseils :

1.   **Gentrification** (Cafés de spécialité, Yoga, Épiceries fines) -> *Fait monter les prix.*
2.   **Vice** (Kebabs, Tabacs, Sex-shops, Casinos) -> *Impact variable (bruit vs commodité).*
3.   **Nuisance** (Bars de nuit, Voies ferrées, Urgences) -> *Fait baisser les prix.*
4.   **Superstition** (Cimetières, Pompes funèbres) -> *Impact psychologique à la baisse.*

---

## 🏗️ Architecture Technique

Le projet repose sur une architecture moderne conteneurisée :

* **Frontend** : React, TailwindCSS, Leaflet (Cartographie).
* **Backend** : Flask (Python).
* **Intelligence Artificielle** :
    * **Prediction** : XGBoost (Machine Learning sur données structurées).
    * **Chatbot** : **Google AI / Gemini Developer API** enrichi par RAG compact (Retrieval Augmented Generation).
* **Infrastructure** : Docker & Docker Compose.

---

## 📄 Contrat API

Les 4 routes exposées par `backend/app.py` (`/api/listings`, `/api/quartier-stats`, `/api/predict`, `/api/chat`) sont documentées de manière formelle (payloads, réponses, codes d'erreur, exemples) dans [`API_CONTRACT.md`](./API_CONTRACT.md), qui fait référence en cas de divergence avec le code.

---

## IA: Google Gemini (cloud)

Le chatbot ("Immotep") utilise **Google AI / Gemini** via `backend/services/chat_service.py` — c'est aujourd'hui le seul backend LLM implémenté dans le code. Il évite le serveur GPU/local, s'intègre simplement côté backend et le free tier suffit généralement pour une démonstration à trafic modéré.

> Un mode **LM Studio en local** (self-hosted, sans dépendre d'un provider externe) a été envisagé mais n'a jamais été implémenté — il n'existe aucune abstraction de provider dans le code actuel. À considérer comme une piste future plutôt qu'un mode disponible.

Le backend actif garde la clé API uniquement côté serveur via `GEMINI_API_KEY`. Le modèle par défaut est `gemini-2.5-flash`, avec des réponses courtes et un contexte RAG borné pour limiter les coûts et les délais.

Toutes les variables liées à Gemini (`GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_MAX_OUTPUT_TOKENS`, `GEMINI_TEMPERATURE`) sont documentées dans [`.env.example`](./.env.example), qui fait référence pour l'ensemble des variables d'environnement du projet.

Limites à garder en tête: les quotas Google AI peuvent évoluer, le débit n'est pas garanti, et une clé API ne doit jamais être exposée dans le frontend. Une interaction courte avec contexte compact vaut souvent environ `1 000 à 3 000 tokens`, ce qui est largement suffisant pour une démo portfolio avec trafic modéré. Le risque principal est surtout un pic de visiteurs simultanés, pas une simple démonstration occasionnelle.

Pour créer la clé:

1. Ouvrez Google AI Studio.
2. Créez une API key Gemini.
3. Renseignez `GEMINI_API_KEY` dans votre environnement local ou dans la configuration de déploiement.
4. Lancez le backend puis testez `/api/chat`.

Test rapide:

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Que vaut un T2 à Gerland ?","context":"Quartier: Gerland, Type: T2"}'
```

---

## 🚀 Installation & Lancement (Recommandé : Docker)

C'est la méthode la plus simple pour lancer tout le projet (Front + Back + Base de données).

### Prérequis
* **Docker Desktop** installé et lancé.
* Une clé **Google AI Studio** pour le chatbot (`GEMINI_API_KEY`).

### 1. Configuration de l'IA (Gemini) et d'Airflow
Copiez [`.env.example`](./.env.example) en `.env` à la racine et renseignez au minimum `GEMINI_API_KEY` (les autres variables Gemini ont des valeurs par défaut raisonnables). Les variables Airflow (`AIRFLOW__WEBSERVER__SECRET_KEY`, `AIRFLOW_ADMIN_USERNAME`, `AIRFLOW_ADMIN_PASSWORD`) sont, elles, obligatoires : `docker-compose up` refuse de démarrer si l'une d'elles est absente (plus de secret/admin par défaut committé).

```bash
cp .env.example .env
# puis éditez .env : GEMINI_API_KEY, AIRFLOW__WEBSERVER__SECRET_KEY (ex. via `openssl rand -hex 30`),
# AIRFLOW_ADMIN_USERNAME et AIRFLOW_ADMIN_PASSWORD
```

### 2. Lancement de l'application
Ouvrez un terminal à la racine du projet :

```bash
# Construire et lancer les conteneurs
docker-compose up --build
```

Une fois lancé, accédez à :
*  **Frontend** : [http://localhost:5173](http://localhost:5173) (ou 3000 selon config)
*  **Backend** : [http://localhost:5000](http://localhost:5000)

---

## 🛠️ Lancement Manuel (Développement)

Si vous ne souhaitez pas utiliser Docker, vous pouvez lancer les deux parties séparément.

### Backend (Python/Flask)

```bash
cd backend

# Créer l'environnement virtuel (optionnel mais recommandé)
python -m venv .venv
# Sur Windows : .venv\Scripts\activate
# Sur Mac/Linux : source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer Gemini
export GEMINI_API_KEY="votre-cle-google-ai"

# Lancer le serveur
python app.py
```

### Frontend (React)

```bash
cd frontend

# Installer les paquets
npm install

# Lancer le serveur de dev
npm run dev
```

---

## 🚀 Déploiement sans Docker Compose

### Backend

Le backend Flask lit le port depuis l'environnement, ce qui permet à Render de fournir `PORT` automatiquement.

Les variables utiles (`GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS`, etc.) sont listées dans [`.env.example`](./.env.example). `CORS_ORIGINS` est optionnel : s'il n'est pas défini, le backend garde un CORS ouvert pour éviter de bloquer une démo.

### Frontend

Le frontend lit l'URL de l'API via Vite (`VITE_API_URL`, voir [`.env.example`](./.env.example)). Sur Render, cette variable est obligatoire. En local seulement, si elle n'est pas définie, le frontend utilise `http://localhost:5000/api`.

---

## ⚙️ Les Scripts de Données (ETL)

Toute l'intelligence de l'Oracle repose sur la qualité de ses données. Les scripts se trouvent dans `backend/scripts/` — **seule source de vérité** pour ce pipeline (le root `scripts/` ne contient que les 6 scrapers, voir plus bas) — orchestrés par le DAG Airflow `Airflow/dags/oracle_loyers_dag.py` (planifié quotidiennement à 2h) selon deux branches parallèles qui convergent :

```text
api_overpass.py ──→ enrich_cavaliers_cp.py ─┐
                                              ├──→ clean_immo.py ──→ train_model.py
data_fusion.py ──────────────────────────────┘
```

1.  **`api_overpass.py`**
    * Récupère ~1 668 lieux répartis sur 21 catégories de POI ("cavaliers") à Lyon via l'API Overpass (OpenStreetMap).
    * *Output :* `cavaliers_lyon.csv` (brut, avec bascule sur 3 miroirs Overpass en cas d'erreur 429/504).

2.  **`enrich_cavaliers_cp.py`**
    * Attribue un code postal précis à chaque cavalier via l'API Data Gouv (Batch processing).
    * *Input/Output :* `cavaliers_lyon.csv` (enrichi avec CP, écriture atomique).

3.  **`data_fusion.py`**
    * Fusionne et nettoie les 6 CSV d'annonces scrapées (Century21, Orpi, SeLoger, PAP, ParuVendu, Vizzit — voir section Scraping ci-dessous).
    * *Output :* `base_de_donnees_immo_lyon_complet.csv`.

4.  **`clean_immo.py`**
    * Le cœur du calcul, en 5 étapes internes séquentielles :
      1. **Géocodage & jitter** — place les annonces sans coordonnées réelles sur la carte, en utilisant l'enveloppe convexe (Convex Hull) des cavaliers pour dessiner la forme réelle des quartiers (fallback sur des zones circulaires par code postal si pas assez de cavaliers).
      2. **Assignation des quartiers** — attribue un nom de quartier lisible (ex: "Croix-Rousse Plateau") à partir du code postal et des coordonnées.
      3. **Classification du type de bien** (Studio/T1, T2, T3, Grand T4+) à partir du texte de l'annonce ou, à défaut, de la surface.
      4. **Calcul des features de distance** — pour chaque annonce, distance au cavalier le plus proche et densité à 500 m, pour chacune des 21 catégories (BallTree/haversine).
      5. **Réindexation des IDs**.
    * *Input :* `base_de_donnees_immo_lyon_complet.csv` + `cavaliers_lyon.csv` -> *Output :* le fichier "Gold Standard" `master_immo_final.csv`.

5.  **`train_model.py`**
    * Entraîne le modèle XGBoost sur `master_immo_final.csv`.
    * Génère le fichier modèle : `backend/models/price_predictor.pkl`, **versionné dans git** (comme `master_immo_final.csv`) pour qu'un environnement fraîchement déployé dispose d'un modèle fonctionnel sans étape manuelle. L'entraînement est déterministe (`random_state=42`) ; relancez `train_model.py` et committez le `.pkl` après toute mise à jour de `master_immo_final.csv`.
    * Via `data_versioning.py`, archive aussi un snapshot content-addressé des données utilisées et écrit `price_predictor.pkl.meta.json` (référence explicite au snapshot + métriques MAE/R² du run courant) — voir "Versioning des snapshots de données" ci-dessous.
    * Chaque run ajoute en plus une ligne (`trained_at`, `mae`, `r2`, `dataset_size`, `n_features`) à `backend/models/training_metrics.jsonl`, un historique continu des métriques permettant de comparer plusieurs runs/versions du modèle dans le temps sans avoir à parcourir l'historique git.
    * Chaque modèle entraîné est identifié par un hash (`model_version`, sha256 du binaire) inclus dans `price_predictor.pkl.meta.json` avec ses hyperparamètres ; une copie est archivée dans `backend/models/versions/`. `GET /api/health` expose la version actuellement chargée. Pour revenir à une version antérieure **sans réentraîner** : `python backend/scripts/rollback_model.py <model_version>`.
    * `backend/tests/test_model_regression.py` (suite pytest, exécuté en CI) vérifie que le MAE/R² restent dans une plage acceptable sur un jeu de validation fixe (même split que l'entraînement), et que `/api/predict` ne régresse pas vers le bug historique de placeholder à 0 — remplace l'ancien script manuel `test_prediction.py`.

> Les scrapers (`scripts/scraper_*.py`, à la racine du dépôt) ne font **pas** partie du DAG Airflow : ils s'exécutent manuellement pour rafraîchir les CSV d'annonces avant de relancer le pipeline. Ils lisent leur ville/URL de recherche depuis `scripts/scraping_config.json` (`scraper_utils.load_site_config()`) plutôt que du code en dur, et chargent les liens déjà connus du run précédent (`load_existing_rows()`) pour ne dédupliquer les annonces contre le CSV existant, pas seulement au sein du run en cours.

### 🧪 Tests frontend (Vitest + E2E Playwright)

* **`npm test`** (`frontend/`) — Vitest (environment jsdom, cohérent avec Vite) : tests unitaires (`services/api.js`, config Vite) et tests de composants React (`ChatOracle`, `SearchForm`, `MapComponent` — rendu, interactions clés, gestion d'erreur). Exécuté en CI à chaque push/PR.
* **`npm run test:e2e`** (`frontend/`) — Playwright pilote le parcours utilisateur critique (saisie des critères → estimation affichée → carte visible → message chatbot → réponse reçue) contre le **vrai build de production** (`vite preview`, pas `npm run dev`) et un **vrai backend Flask** — `playwright.config.js` démarre les deux via `webServer` sur des ports dédiés (5055/4173), sans mock réseau. Fonctionne sans `GEMINI_API_KEY` (le backend répond alors avec un message explicite plutôt que planter). Job CI dédié (`e2e`) car il nécessite à la fois Python et Node.

### 🧪 Tests de scraping et canari Playwright

Deux niveaux de tests protègent les 6 scrapers contre une refonte silencieuse des sites sources :

* **`scripts/tests/test_scraper_extraction_fixtures.py`** (ORA-19) — tests unitaires rapides, sans réseau ni navigateur, basés sur une fixture HTML statique par site (`scripts/tests/fixtures/`) qui réutilise les sélecteurs CSS réels de chaque `scraper_*.py`. Exécutés à chaque push/PR (job `scrapers` de `.github/workflows/ci.yml`).
* **`scripts/tests/e2e/test_playwright_selectors.py`** (ORA-20) — canari Playwright qui navigue vers la page de résultats *live* de chaque site et vérifie que les sélecteurs actuels y retournent encore des annonces avec titre/prix non vides. Un échec logge explicitement `SÉLECTEUR CASSÉ (<site>)` pour le distinguer d'un incident réseau ponctuel. Ne remplace pas les scrapers de production (`undetected_chromedriver` reste nécessaire pour l'anti-bot) — sert uniquement de détecteur de changement HTML.

**Planification et alerte (ORA-21)** — `.github/workflows/scraper-selector-canary.yml` exécute le canari Playwright chaque jour à 1h UTC (une heure avant le DAG Airflow de 2h, pour alerter avant que le pipeline ETL ne tourne sur des données obsolètes/vides) et sur déclenchement manuel (`workflow_dispatch`). En cas d'échec, une issue GitHub `scraper-canari-alert` est créée automatiquement (ou un commentaire est ajouté si une issue ouverte existe déjà, pour éviter le spam d'échecs consécutifs).

**Procédure de triage lors d'une alerte :**
1. Ouvrir le log du run échoué et repérer le(s) message(s) `SÉLECTEUR CASSÉ (<site>)`.
2. Visiter manuellement la page de résultats du site concerné, ou relancer le workflow (`workflow_dispatch`) pour écarter un incident ponctuel (CAPTCHA, blocage IP, timeout réseau).
3. Si le site a réellement changé de structure : mettre à jour les sélecteurs dans `scripts/scraper_<site>.py` **et** la fixture correspondante dans `scripts/tests/fixtures/`.
4. Vérifier que les tests ORA-19 et le canari Playwright passent de nouveau.
5. Fermer l'issue.

### 🕵️ Anti-détection des scrapers — limites légales

Les 6 scrapers tirent à chaque run un User-Agent réaliste au hasard dans un pool (`scraping_config.json` → `user_agents`, via `scraper_utils.pick_user_agent()`), et supportent optionnellement un pool de proxies (`proxies`, vide/désactivé par défaut, via `pick_proxy()`).

**Ces mécanismes ne dispensent pas de respecter le cadre légal du scraping :**
* Consulter et respecter le `robots.txt` et les CGU de chaque site avant toute collecte (voir les issues dédiées ORA-67/ORA-93 pour la vérification formelle par portail).
* Ne pas contourner une mesure de blocage explicite (bannissement d'IP, CAPTCHA résolu manuellement de façon répétée, mur de paiement) — la rotation UA/proxy sert à réduire le risque de faux-positifs de détection anti-bot, pas à forcer un accès refusé.
* Respecter un rythme de requêtes raisonnable (la temporisation aléatoire déjà en place entre les requêtes) pour ne pas dégrader le service du site cible.
* Ne collecter que des données publiquement accessibles, à usage non commercial dans le cadre de ce projet.

### 📦 Versioning des snapshots de données

Chaque exécution de `train_model.py` archive un instantané de `master_immo_final.csv` via `backend/scripts/data_versioning.py` (équivalent léger à DVC, sans dépendance ni stockage distant à configurer) :

* **`backend/data/snapshots/master_immo_final_<sha256>.csv`** — une copie content-addressée du jeu de données (un re-run sur des données identiques ne duplique pas le fichier, seul le hash change si les données changent). Ces fichiers sont versionnés dans git au même titre que le reste de `backend/data/`.
* **`backend/data/snapshots/manifest.csv`** — historique de chaque snapshot (timestamp, sha256, fichier, nombre de lignes).
* **`backend/models/price_predictor.pkl.meta.json`** — référence explicitement, pour le modèle entraîné, le `data_snapshot_sha256`/`data_snapshot_file` utilisé ainsi que les métriques (MAE, R²). Versionné dans git comme le `.pkl` qu'il décrit (ORA-29).

**Reproduire un ancien modèle à partir de son snapshot :**
1. Récupérer le `data_snapshot_sha256` voulu (depuis un `price_predictor.pkl.meta.json` conservé, ou depuis `backend/data/snapshots/manifest.csv`).
2. Copier le snapshot correspondant par-dessus les données actives : `cp backend/data/snapshots/master_immo_final_<sha256>.csv backend/data/master_immo_final.csv`.
3. Relancer `python backend/scripts/train_model.py` — le modèle est ré-entraîné sur exactement les mêmes données, et un nouveau `.meta.json` confirme le même `data_snapshot_sha256`.

### 🔖 Versioning du modèle et rollback sans réentraîner

Le mécanisme ci-dessus reproduit un ancien modèle en **ré-entraînant** sur son snapshot de données. Pour un retour arrière immédiat (ex : le modèle fraîchement entraîné se comporte mal en production), chaque run archive aussi une copie binaire prête à l'emploi :

* **`backend/models/versions/price_predictor_<model_version>.pkl`** — copie du modèle archivée sous son hash (`model_version` = sha256 tronqué du binaire, présent dans `price_predictor.pkl.meta.json`). Versionnée dans git.
* **`GET /api/health`** — expose `model_version`, `trained_at` et `metrics` (MAE/R²) du modèle actuellement chargé par le backend.
* **`python backend/scripts/rollback_model.py <model_version>`** — restaure instantanément cette version comme modèle actif (`price_predictor.pkl`) et met à jour `.meta.json`, **sans ré-entraîner**.

---

## 🗂️ Arborescence du Projet

```text
oracle-des-loyers/
├── docker-compose.yml         # Chef d'orchestre des conteneurs (backend, frontend, Airflow)
├── README.md                  # Ce fichier
│
├── Airflow/                   # Orchestration du pipeline ETL (DAG planifié, cf. section ETL)
│   └── dags/oracle_loyers_dag.py
│
├── scripts/                   # Scrapers (exécution manuelle, hors DAG Airflow)
│   ├── scraper_century_21.py, scraper_orpi.py, scraper_pap.py,
│   │   scraper_paruvendu.py, scraper_seloger.py, scraper_vizzit.py
│   ├── scraper_utils.py, csv_atomic_writer.py, scraping_config.json  # Communs aux 6 scrapers
│   └── tests/                 # Tests unitaires (fixtures) + e2e (canari Playwright)
│
├── backend/                   # API Flask & Logique métier
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                 # Point d'entrée serveur actif (Routes API Flask)
│   │
│   ├── data/                  # LE COFFRE-FORT (CSV bruts, fusionnés, master, conversations.db)
│   ├── models/                # Cerveaux entraînés (price_predictor.pkl, versionné en git)
│   │
│   ├── scripts/               # L'USINE À DONNÉES — source de vérité (voir section ETL) ;
│   │   │                      # ce sont ces copies qu'utilise le DAG Airflow, pas celles de scripts/ (ORA-7)
│   │   ├── api_overpass.py, enrich_cavaliers_cp.py
│   │   ├── data_fusion.py, clean_immo.py, train_model.py
│   │   └── generate_map.py, analyze_impact.py, rollback_model.py, data_versioning.py, http_retry.py, test_api.py
│   │
│   ├── services/              # Modules métier actifs
│   │   ├── chat_service.py    # Chatbot Gemini + RAG (seul chemin LLM actif)
│   │   ├── data_loader.py, map_generator.py, utils.py
│   │
│   ├── core/                  # Constantes partagées
│   ├── tests/                 # Suite pytest (chat, config runtime)
│   └── static/                # Fichiers servis publiquement (cartes HTML)
│
└── frontend/                  # Interface React
    ├── Dockerfile
    ├── package.json
    ├── public/data/           # Carte interactive générée (map_pings_lyon_calques.html)
    └── src/
        ├── components/
        │   ├── ChatOracle.jsx # Composant Chatbot
        │   ├── MapComponent.jsx # Composant Carte Interactive (Leaflet)
        │   └── Sidebar.jsx    # Formulaire de prédiction
        └── services/
            └── api.js         # Pont vers le backend
```

> **Dette technique connue** (trackée dans le backlog Linear) : `backend/main.py` (FastAPI) et les modules `smart_agent.py`/`prompt_system.py`/`conversation_manager.py` sont du code hérité, non branchés sur `app.py` — à ne pas prendre comme référence d'architecture active. `backend/src/api/` et `backend/src/ml_engine/` sont des dossiers vides.
