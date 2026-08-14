# 🔮 L'Oracle des Loyers

> *"Ce T2 est cher, mais c'est le prix à payer pour être à 30m d'un café de spécialité sans entendre les cris de l'école voisine."*

**L'Oracle des Loyers** est une application immobilière intelligente (et un peu cynique) capable d'estimer la "Vraie Valeur" d'un bien à Lyon.
Au-delà des données classiques (surface, prix), l'Oracle croise les données avec **"Les 4 Cavaliers"** de l'environnement urbain pour affiner ses prédictions et ses conseils :

1.   **Gentrification** (Cafés de spécialité, Yoga, Épiceries fines) -> *Fait monter les prix.*
2.   **Vice** (Kebabs, Tabacs, Sex-shops, Casinos) -> *Impact variable (bruit vs commodité).*
3.   **Nuisance** (Bars de nuit, Voies ferrées, Urgences) -> *Fait baisser les prix.*
4.   **Superstition** (Cimetières, Pompes funèbres) -> *Impact psychologique à la baisse.*

Ces facteurs, jusqu'ici uniquement internes au modèle (features `dist_*`/`nb_*_500m`), sont désormais aussi résumés en phrases lisibles pour l'utilisateur (`backend/services/cavaliers_factors.py`, exposées par `/api/quartier-stats`) et exportables en PDF (ORA-73, généré côté serveur via WeasyPrint depuis ORA-121 — `POST /api/report/pdf`, voir section Contrat API).

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

Les 5 routes exposées par `backend/app.py` (`/api/listings`, `/api/quartier-stats`, `/api/quartier-historique`, `/api/predict`, `/api/chat`) sont documentées de manière formelle (payloads, réponses, codes d'erreur, exemples) dans [`API_CONTRACT.md`](./API_CONTRACT.md), qui fait référence en cas de divergence avec le code.

Une documentation interactive Swagger/OpenAPI (générée via [Flasgger](https://github.com/flasgger/flasgger)) est aussi disponible une fois le backend lancé, sur [http://localhost:5000/apidocs/](http://localhost:5000/apidocs/) (spec JSON brute sur `/apispec.json`).

---

## 🔒 Confidentialité des données

Quelles données personnelles sont collectées (messages du chatbot, adresse IP pour le rate limiting), pendant combien de temps, et ce qui n'est **pas** collecté (pas de cookies, pas de compte, pas d'analytics) : voir [`PRIVACY.md`](./PRIVACY.md).

---

## IA: Google Gemini (cloud)

Le chatbot ("Immotep") utilise **Google AI / Gemini** via `backend/services/chat_service.py` — c'est aujourd'hui le seul backend LLM implémenté dans le code. Il évite le serveur GPU/local, s'intègre simplement côté backend et le free tier suffit généralement pour une démonstration à trafic modéré.

### Décision (ORA-119) : Gemini cloud + logique déterministe, pas de RAG local

Le brief initial du projet (V2) mentionnait un chatbot **"RAG Mistral 7B"**. Ce n'est pas ce qui est implémenté : le code utilise Gemini (cloud) et le "RAG" désigné dans ce README est en réalité un filtrage déterministe du DataFrame (règles/regex sur quartier, type, budget dans `chat_service.parse_query`), pas une recherche par similarité d'embeddings sur un vector store.

**Décision : conserver Gemini + le filtrage déterministe actuel plutôt que d'investir dans un vrai RAG local (Mistral via LM Studio, embeddings, vector store).**

Justification :
- Un RAG local nécessite un serveur avec GPU (ou un CPU suffisamment puissant) tournant en permanence pour héberger Mistral — incompatible avec un hébergement de démo portfolio classique (Render, sans GPU dédié) sans coût d'infra disproportionné par rapport à l'usage réel.
- Le filtrage déterministe actuel **grounde déjà** les réponses sur les données réelles (annonces, quartiers, facteurs) avant l'appel à Gemini : le risque d'hallucination qu'un vrai RAG viserait à réduire est déjà largement couvert pour ce cas d'usage (questions sur un quartier/type de bien connu, pas une recherche sémantique libre sur un corpus large).
- Ajouter une pipeline d'embeddings + vector store est un chantier à part entière (choix du modèle d'embedding, indexation, mise à jour à chaque nouveau scraping) sans commune mesure avec le bénéfice attendu sur ce volume de données (quelques centaines à quelques milliers d'annonces).

**Cette décision doit être réévaluée si** : le trafic ou la diversité des questions posées au chatbot dépasse ce que le filtrage par règles peut couvrir correctement (ex. besoin réel de recherche sémantique libre plutôt que par critères structurés), ou si un hébergement avec GPU devient disponible pour ce projet à coût raisonnable.

> Un mode **LM Studio en local** (self-hosted, sans dépendre d'un provider externe) reste une piste future si cette décision est révisée — il n'existe aujourd'hui aucune abstraction de provider dans le code, Gemini est appelé directement.

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
*  **Documentation Swagger/OpenAPI** : [http://localhost:5000/apidocs/](http://localhost:5000/apidocs/)

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

### 🚚 Déploiement continu (CD, ORA-64)

Le job `deploy` de `.github/workflows/ci.yml` déclenche un déploiement Render (via son [Deploy Hook](https://render.com/docs/deploy-hooks)) uniquement quand **tous** les jobs de CI (`backend`, `scrapers`, `frontend`, `e2e`, `dependency-scan`) ont réussi sur un push vers `main` — `needs: [...]` + `if: success() && ...` : un échec de test (ou une vulnérabilité détectée par `dependency-scan`) bloque bien le déploiement (le job `deploy` est alors sauté, pas juste marqué en échec).

**Configuration requise (à faire une seule fois, côté Render puis GitHub) :**
1. Dans le dashboard Render, pour chaque service (backend, frontend) : *Settings → Deploy Hook* → copier l'URL générée.
2. Dans GitHub, *Settings → Secrets and variables → Actions* : créer `RENDER_DEPLOY_HOOK_BACKEND` et `RENDER_DEPLOY_HOOK_FRONTEND` avec ces URLs. Tant qu'un secret n'est pas défini, l'étape correspondante est sautée sans faire échouer le job (message d'avertissement dans les logs).
3. **Désactiver l'auto-deploy natif de Render** sur ces deux services (*Settings → Auto-Deploy → No*) — sinon Render redéploierait à chaque push, y compris si la CI échoue, en plus du déploiement déclenché par ce workflow.

**Rollback :** chaque déploiement Render reste visible dans l'historique du service (*Dashboard → Deploys*). En cas de déploiement problématique, cliquer sur un déploiement antérieur réussi puis *Rollback to this deploy* revient immédiatement dessus (pas besoin de revert Git ni de relancer la CI).

### 🔎 Scan de vulnérabilités des dépendances (ORA-65)

Le job `dependency-scan` de `.github/workflows/ci.yml` s'exécute sur chaque push/PR et vérifie les dépendances connues pour des vulnérabilités publiées (CVE/PYSEC via l'API [OSV](https://osv.dev/)) :

- **`pip-audit -r requirements.txt`** (working-directory `backend`) sur `backend/requirements.txt`. `pip-audit` n'a pas de filtre de sévérité natif : **toute** vulnérabilité connue fait échouer l'étape, quelle que soit sa gravité.
- **`npm audit --audit-level=critical`** (working-directory `frontend`, après `npm ci`) sur `frontend/package.json`. Seule une vulnérabilité de sévérité **critical** fait échouer le job ; les vulnérabilités low/moderate/high restent visibles dans les logs (le rapport `npm audit` est toujours affiché) mais ne bloquent pas la CI.

**Comment traiter une alerte :**
1. Regarder si un correctif existe : `pip-audit` liste la colonne `Fix Versions` ; `npm audit fix` corrige automatiquement ce qui peut l'être sans breaking change.
2. Si un correctif casse d'autres dépendances, ou si la vulnérabilité ne s'applique pas réellement à notre usage (faux positif applicatif), l'ignorer **explicitement** plutôt que de laisser la CI rouge en permanence ou de désactiver le job :
   - Python : ajouter `--ignore-vuln PYSEC-XXXX-XXXX` à la commande `pip-audit` dans `ci.yml`, avec un commentaire juste au-dessus expliquant pourquoi.
   - JS : `npm audit` ne propose pas d'exclusion par ID directement dans la CLI stable ; documenter le cas ici et suivre le correctif upstream, ou geler `--audit-level` si le risque est jugé acceptable temporairement (à documenter également).
3. Ne jamais supprimer ou commenter l'étape de scan pour faire passer la CI — l'objectif du job est justement d'empêcher qu'une dépendance vulnérable connue parte en prod silencieusement.

**État au 2026-08-03 :** `pip-audit` sur `backend/requirements.txt` ne remonte aucune vulnérabilité connue. `npm audit` sur `frontend/package.json` remonte 9 vulnérabilités (1 low, 2 moderate, 6 high, 0 critical) sur des dépendances de outillage transitives (`postcss`, `js-yaml`, `minimatch`, `picomatch`, `brace-expansion`, `flatted`, `ajv`, `@babel/core`, `yaml`) — aucune n'est critique, le seuil `--audit-level=critical` n'échoue donc pas la CI ; elles restent visibles dans les logs pour correction ultérieure (`npm audit fix`).

---

## 🩺 Observabilité backend (logs structurés, Sentry) — ORA-63

Le backend Flask centralise sa configuration de logging dans `backend/logging_config.py`, importé et appelé en tout premier dans `backend/app.py`.

- **Logs structurés** : tous les logs applicatifs (démarrage, erreurs, avertissements) passent par le module `logging` standard (`logger.info/.warning/.error/.critical`), avec un format cohérent `timestamp [NIVEAU] module: message`. Plus aucun `print()` n'est utilisé pour signaler une erreur applicative dans `app.py` ou `services/*.py` (les `print()` restants, dans `backend/scripts/`, sont des CLI qui affichent une progression humaine et ne relèvent pas de l'observabilité applicative).
- **Niveau configurable** via la variable d'environnement `LOG_LEVEL` (`DEBUG`, `INFO` par défaut, `WARNING`, `ERROR`, `CRITICAL`). Voir [`.env.example`](./.env.example).
- **Tracking d'erreurs (Sentry)** : si la variable d'environnement `SENTRY_DSN` est définie, `sentry-sdk` (avec son intégration Flask) est initialisé au démarrage et capture automatiquement les exceptions non gérées ainsi que les réponses 5xx. Si `SENTRY_DSN` est absent (dev local, CI), l'initialisation est un no-op silencieux : rien à configurer pour développer en local.
- **Alerte sur erreurs critiques** : les erreurs jugées critiques (ex. le provider LLM Gemini indisponible dans `services/chat_service.py`) sont loguées via `logger.critical(...)` avec le tag `[LLM_UNAVAILABLE]`. Lorsque Sentry est configuré, ces logs remontent comme événements dans le dashboard Sentry, qui gère l'alerting (email/Slack/etc.) — pas de système d'alerte custom à maintenir côté backend.

**Configuration requise pour activer Sentry en production :** créer un projet sur [sentry.io](https://sentry.io) (ou une instance self-hosted), copier son DSN et renseigner `SENTRY_DSN` (et éventuellement `SENTRY_ENVIRONMENT`) dans les variables d'environnement du service Render. Configurer ensuite les règles d'alerte côté dashboard Sentry (ex. notification sur toute nouvelle erreur taguée `[LLM_UNAVAILABLE]`, ou sur un volume de 5xx au-delà d'un seuil).

---

## ⚙️ Les Scripts de Données (ETL)

Toute l'intelligence de l'Oracle repose sur la qualité de ses données. Les scripts se trouvent dans `backend/scripts/` — **seule source de vérité** pour ce pipeline (le root `scripts/` ne contient que les 6 scrapers, voir plus bas) — orchestrés par **deux familles de DAG Airflow**, découplées par cadence et par fiabilité (les POI ne bougent pas d'un jour à l'autre et l'API Overpass est rate-limitée ; les annonces ont besoin d'un rafraîchissement plus fréquent et ne doivent pas rester bloquées par la lenteur d'Overpass). Depuis ORA-153, le DAG cavaliers est en plus **scindé par ville** — une DAG indépendante et planifiable séparément par ville déclarée dans `scripts/scraping_config.json`, générées dynamiquement à partir de cette config (ajouter une ville n'y nécessite aucun changement de code Airflow) :

```text
Airflow/dags/oracle_cavaliers_dag.py — une DAG oracle_cavaliers_pipeline_<slug> par ville, cadence mensuelle
  api_overpass.py --ville <slug> ──→ enrich_cavaliers_cp.py --ville <slug> ──→ merge_cavaliers_villes.py

Airflow/dags/oracle_annonces_dag.py — une seule DAG oracle_annonces_pipeline, cadence hebdomadaire
  [data_fusion.py --ville <slug> pour chaque ville] ──→ clean_immo.py ──┬──→ master_immo_final.csv ──→ train_model.py ──→ [generate_map.py --ville <slug> pour chaque ville]
                                                                         └──→ annonces.db (SQLite)
```

`merge_cavaliers_villes.py` régénère `cavaliers_all.csv` (toutes villes confondues) à partir des `cavaliers_<slug>.csv` actuellement sur disque — c'est ce fichier combiné, et lui seul, que lit `clean_immo.py` (DAG annonces) ; aucune dépendance inter-DAG directe, juste le fichier le plus récent sur disque au moment du run.

`clean_immo.py` et `train_model.py` restent pour l'instant un step **partagé, unique pour toutes les villes** : le modèle actif est encore un seul `price_predictor.pkl` combiné (`ville` en feature, pas un modèle par ville — voir ORA-154). Les scinder par ville reviendrait à lancer deux réentraînements concurrents sur le même fichier de sortie ; ils tournent donc une seule fois par run, après que toutes les fusions par ville se sont terminées.

Deux sources de vérité distinctes sortent de `clean_immo.py`, pour deux usages différents :

| Source | Alimente | Consommée par |
| --- | --- | --- |
| `master_immo_final.csv` | `/api/listings`, la carte (`generate_map.py`), l'entraînement du modèle | `MapComponent.jsx`, `train_model.py` |
| `annonces.db` (SQLite) | `/api/annonces` (liste "Annonces récentes") + tracking de clics (`/api/annonces/:id/click`) | `AnnoncesList.jsx`/`AnnonceCard.jsx` |

Les deux sont écrites à partir du **même dataframe final** en fin de `clean_immo.py` (étape 6 ci-dessous) : pas de divergence de comptage attendue entre les deux après un run, `url` étant déjà un champ obligatoire en amont dans les CSV scrapés (ORA-82) — la seule ligne exclue de `annonces.db` serait une annonce dont l'`url` serait vide malgré cette contrainte (garde-fou défensif, cf. `step_sync_annonces_store`).

1.  **`api_overpass.py`**
    * Récupère ~1 668 lieux répartis sur 21 catégories de POI ("cavaliers") via l'API Overpass (OpenStreetMap), pour la ville ciblée par `--ville <slug>` (ORA-153 ; sans l'argument, retombe sur `ville_active` de `scripts/scraping_config.json` — même config que les 6 scrapers, pas de nom de ville en dur dans le code, voir ORA-71 ci-dessous).
    * *Output :* `cavaliers_<slug>.csv` (brut, avec bascule sur 3 miroirs Overpass en cas d'erreur 429/504).

2.  **`enrich_cavaliers_cp.py`**
    * Attribue un code postal précis à chaque cavalier via l'API Data Gouv (Batch processing), pour la ville ciblée par `--ville <slug>` (défaut `lyon`, ORA-153 — avant cette correction le script ciblait `cavaliers_lyon.csv` en dur, Lille n'était donc jamais enrichi).
    * *Input/Output :* `cavaliers_<slug>.csv` (enrichi avec CP, écriture atomique).

3.  **`merge_cavaliers_villes.py`** (ORA-153)
    * Concatène les `cavaliers_<slug>.csv` de toutes les villes déclarées en un seul `cavaliers_all.csv` — le fichier réellement consommé par `clean_immo.py`. Point de jonction entre les DAG cavaliers (scindés par ville) et le DAG annonces (encore global).

4.  **`data_fusion.py`**
    * Fusionne et nettoie les 6 CSV d'annonces scrapées (Century21, Orpi, SeLoger, PAP, ParuVendu, Vizzit — voir section Scraping ci-dessous), pour la ville ciblée par `--ville <slug>` (ORA-153) — sans l'argument, reconstruit à partir de **toutes** les villes déclarées. Un run par ville préserve les annonces des autres villes déjà présentes dans le fichier combiné plutôt que de les écraser.
    * *Output :* `base_de_donnees_immo_complet.csv`.

5.  **`clean_immo.py`**
    * Le cœur du calcul, en 7 étapes internes séquentielles :
      0. **Purge des annonces expirées** (TTL, ORA-134) — exclut les annonces dont `date_dernier_scan` dépasse 14 jours (~2 runs hebdomadaires de marge), avant tout le reste du pipeline. Conservateur : une ligne sans `date_dernier_scan` exploitable (CSV antérieur à ORA-134) est gardée plutôt que purgée. Voir la sous-section dédiée ci-dessous.
      1. **Géocodage & jitter** — place les annonces sans coordonnées réelles sur la carte, en utilisant l'enveloppe convexe (Convex Hull) des cavaliers pour dessiner la forme réelle des quartiers (fallback sur des zones circulaires par code postal si pas assez de cavaliers).
      2. **Assignation des quartiers** — attribue un nom de quartier lisible (ex: "Croix-Rousse Plateau") à partir du code postal et des coordonnées.
      3. **Classification du type de bien** (Studio/T1, T2, T3, Grand T4+) à partir du texte de l'annonce ou, à défaut, de la surface.
      4. **Calcul des features de distance** — pour chaque annonce, distance au cavalier le plus proche et densité à 500 m, pour chacune des 21 catégories (BallTree/haversine).
      5. **Réindexation des IDs**.
      6. **Synchronisation du store SQLite `annonces.db`** (ORA-112) — même dataframe final, upserté (dédoublonné par `url`) dans la table `annonces` consommée par `GET /api/annonces` (liste "Annonces récentes", tracking de clics). Avant cette étape, `annonces.db` n'était peuplée que par les tests unitaires : ce n'est plus le cas, les deux sources sont désormais synchronisées à chaque run de `clean_immo.py`.
    * *Input :* `base_de_donnees_immo_complet.csv` + `cavaliers_all.csv` -> *Output :* le fichier "Gold Standard" `master_immo_final.csv` **et** `annonces.db` à jour.

6.  **`train_model.py`**
    * Entraîne le modèle XGBoost sur `master_immo_final.csv`.
    * Génère le fichier modèle : `backend/models/price_predictor.pkl`, **versionné dans git** (comme `master_immo_final.csv`) pour qu'un environnement fraîchement déployé dispose d'un modèle fonctionnel sans étape manuelle. L'entraînement est déterministe (`random_state=42`) ; relancez `train_model.py` et committez le `.pkl` après toute mise à jour de `master_immo_final.csv`.
    * Via `data_versioning.py`, archive aussi un snapshot content-addressé des données utilisées et écrit `price_predictor.pkl.meta.json` (référence explicite au snapshot + métriques MAE/R² du run courant) — voir "Versioning des snapshots de données" ci-dessous.
    * Chaque run ajoute en plus une ligne (`trained_at`, `mae`, `r2`, `dataset_size`, `n_features`) à `backend/models/training_metrics.jsonl`, un historique continu des métriques permettant de comparer plusieurs runs/versions du modèle dans le temps sans avoir à parcourir l'historique git.
    * Chaque modèle entraîné est identifié par un hash (`model_version`, sha256 du binaire) inclus dans `price_predictor.pkl.meta.json` avec ses hyperparamètres ; une copie est archivée dans `backend/models/versions/`. `GET /api/health` expose la version actuellement chargée. Pour revenir à une version antérieure **sans réentraîner** : `python backend/scripts/rollback_model.py <model_version>`.
    * `backend/tests/test_model_regression.py` (suite pytest, exécuté en CI) vérifie que le MAE/R² restent dans une plage acceptable sur un jeu de validation fixe (même split que l'entraînement), et que `/api/predict` ne régresse pas vers le bug historique de placeholder à 0 — remplace l'ancien script manuel `test_prediction.py`.

> Les scrapers (`scripts/scraper_*.py`, à la racine du dépôt) ne font **pas** partie du DAG Airflow : ils s'exécutent manuellement pour rafraîchir les CSV d'annonces avant de relancer le pipeline. Ils lisent leur ville/URL de recherche depuis `scripts/scraping_config.json` (`scraper_utils.load_site_config()`) plutôt que du code en dur, et chargent les liens déjà connus du run précédent (`load_existing_rows()`) pour ne dédupliquer les annonces contre le CSV existant, pas seulement au sein du run en cours. Une annonce déjà connue et revue au cours du run voit sa colonne `DerniereVue` mise à jour (ORA-134, voir ci-dessous) sans être re-scrapée en détail.

### 🗑️ Annonces mortes : TTL par re-scraping + nettoyage ponctuel (ORA-134)

**Constat** : le pipeline n'avait jusqu'ici aucun mécanisme de suppression — une annonce retirée/louée/expirée sur le site source restait indéfiniment dans `annonces.db`, provoquant des 404 au clic.

**Correctif structurel (TTL)** : chaque scraper trace désormais une colonne `DerniereVue` (date ISO), mise à jour à chaque fois qu'une annonce déjà connue est revue au cours d'un run. `data_fusion.py` la propage sous le nom `date_dernier_scan` dans `base_de_donnees_immo_complet.csv`, et `clean_immo.py` (étape 0 ci-dessus) exclut toute annonce dont cette date dépasse 14 jours — avant génération de `master_immo_final.csv` **et** synchronisation de `annonces.db`, donc les deux sources en bénéficient également.

Complication prise en compte : chaque scraper arrêtait sa pagination dès la 1ère page entièrement déjà-connue, donc les annonces plus profondément paginées n'étaient jamais re-confirmées. `should_continue_pagination()` (`scripts/scraper_utils.py`) accorde désormais `GRACE_PAGES_SANS_NOUVEAUTE` (3) pages de marge sans nouvelle annonce avant d'arrêter réellement la pagination, pour laisser une chance de re-confirmer périodiquement les annonces déjà connues.

**Nettoyage ponctuel du stock existant** : le TTL ne corrige le stock déjà accumulé qu'au fil des prochains runs (les annonces déjà en base n'ont pas de `date_dernier_scan` tant qu'elles n'ont pas été re-scrapées). `backend/scripts/prune_dead_annonces.py` vérifie en direct (HTTP) chaque url encore dans `annonces.db` et retire celles confirmées mortes — un vrai 404/410 HTTP, ou un "soft 404" (page 200 dont le texte indique que l'annonce n'est plus disponible, détection approximative par mots-clés génériques, cf. `SOFT_404_PATTERNS`). Volontairement conservateur au-delà de ça : un statut vraiment ambigu (403 anti-bot, timeout, 5xx) est laissé tel quel plutôt que de risquer une suppression à tort :

```bash
python backend/scripts/prune_dead_annonces.py --dry-run   # vérifie et logue sans rien supprimer
python backend/scripts/prune_dead_annonces.py              # supprime les 404/410/soft-404 confirmés
```

**Résidu bloqué par l'anti-bot** : certains sites (SeLoger notamment) renvoient systématiquement 403 aux clients HTTP basiques, y compris pour des annonces réellement mortes — ces urls restent "ambiguës" et ne sont pas supprimées par le script ci-dessus. `scripts/recheck_dead_annonces.py` (tourne sous `scripts/.venv`, qui a Selenium/undetected_chromedriver — volontairement absents des dépendances backend) re-teste chaque url en HTTP puis escalade au navigateur furtif (`headless=True`, cf. `get_chrome_driver`) celles restées ambiguës, avec trois signaux dans l'ordre : redirection vers la page d'accueil, `looks_like_soft_404` (même détection que ci-dessus), et en dernier recours `looks_like_valid_listing` — absence de tout signal de prix sur la page rendue, plus généraliste qu'une liste de formulations d'erreur mais aussi plus susceptible de faux positif (mitigé pour le cas "prix sur demande") :

```bash
cd scripts && source .venv/bin/activate
python recheck_dead_annonces.py --dry-run   # vérifie et logue sans rien supprimer
python recheck_dead_annonces.py             # supprime les annonces confirmées mortes via navigateur
```

**`master_immo_final.csv` (carte) n'est pas concerné par ce qui précède** : c'est un fichier différent de `annonces.db`, généré indépendamment par `clean_immo.py`, sans colonne `date_dernier_scan` (généré avant le correctif TTL) — ni le TTL structurel ni les deux scripts ci-dessus ne le nettoient. `scripts/prune_dead_map_listings.py` applique la même stratégie de vérification (réutilise `check_url_status`/`check_url_status_browser`) directement sur ce CSV, puis régénère la carte (`generate_map.py`) après une purge réelle. N'affecte pas le modèle ML — les lignes retirées restent des points de prix historiques valables pour l'entraînement même si le lien source a expiré :

```bash
cd scripts && source .venv/bin/activate
python prune_dead_map_listings.py --dry-run   # vérifie et logue sans rien modifier
python prune_dead_map_listings.py             # purge master_immo_final.csv + régénère la carte
```

### 🌍 Généricité multi-ville (ORA-71, ORA-153) — état actuel

Lyon et Lille sont toutes deux déclarées et scrapées en conditions réelles (`scripts/scraping_config.json`).

* **`api_overpass.py`**, **`enrich_cavaliers_cp.py`** et **`data_fusion.py`** acceptent désormais un `--ville <slug>` explicite (ORA-153) — plus besoin d'éditer `ville_active` à la main entre deux scrapes. `generate_map.py` l'avait déjà (ORA-71 POC).
* Les DAG Airflow cavaliers sont générés dynamiquement, un par ville déclarée (`oracle_cavaliers_pipeline_<slug>`) — voir "Les Scripts de Données (ETL)" ci-dessus.
* **`train_model.py`** n'exclut pas `ville` de l'entraînement : encodée en one-hot comme `quartier`/`type_local`, elle permet au modèle d'apprendre un effet prix par ville. Avec Lyon **et** Lille désormais dans `master_immo_final.csv`, ce n'est plus un no-op (`drop_first=True` ne supprime plus la seule catégorie) — voir ORA-154, qui remplace cette approche par un modèle distinct par ville (le garde-fou de régression comparant deux villes aux gammes de prix différentes dans un même R²/MAE n'est pas fiable).
* Vérifié avec une ville fictive de test (`backend/tests/test_api_overpass.py::ResolveActiveCityNameTest`, `backend/tests/test_model_regression.py::MultiCityFeatureGenericizationTest`) en plus des tests avec Lyon/Lille réels.

**Ce qui n'est pas fait** (à traiter séparément) :
* `clean_immo.py` et `train_model.py` restent un step **partagé, unique pour toutes les villes** (`cavaliers_all.csv`, `master_immo_final.csv`, `price_predictor.pkl` combinés) — les scinder par ville suppose d'abord un modèle par ville (ORA-154), sans quoi deux DAGs par ville lanceraient des réentraînements concurrents sur le même fichier de sortie.
* `generate_map.py` : `metro_<slug>.json`/`<slug>_quartiers.geojson` (calques carte) restent alimentés manuellement par ville (pas de script d'extraction automatisé comme pour les cavaliers).

### 🗺️ Génération de la carte

Un seul pipeline fait foi : **`backend/scripts/generate_map.py`**. Pour la ville ciblée par `--ville <slug>` (défaut `lyon` ; `VILLE_CONFIG` dans le script déclare Lyon et Lille), à partir de `master_immo_final.csv`, `cavaliers_<slug>.csv`, `metro_<slug>.json` et son GeoJSON de quartiers, il génère la carte Folium interactive `frontend/public/data/map_pings_<slug>_calques.html`, réellement servie par `MapComponent.jsx` (iframe). Comme pour le reste des données du projet, le fichier généré est **versionné dans git** ; régénérez-le après toute mise à jour des données sources :

```bash
python backend/scripts/generate_map.py --ville lyon
python backend/scripts/generate_map.py --ville lille
```

(L'ancien second pipeline concurrent — `backend/services/map_generator.py` → `backend/static/map_lyon.html`, orphelin, sans route ni DAG l'appelant — a été supprimé ; voir ORA-50.)

**Calque "Quartiers"** (ORA-104) : les limites des 9 arrondissements de Lyon (`backend/data/lyon_arrondissements.geojson`, © contributeurs OpenStreetMap, ODbL 1.0) sont dessinées en polygones (`folium.GeoJson`, off par défaut comme Nuisance/Gentrification/Superstition), avec libellé au survol. Données récupérées une fois via `backend/scripts/fetch_lyon_arrondissements.py` (Nominatim) et versionnées dans le repo — aucune dépendance réseau à runtime. Le fichier des messages postMessage échangés pour piloter les calques (`TOGGLE_LAYER`) est documenté dans [`MAP_CONTRACT.md`](./MAP_CONTRACT.md).

#### Décision (ORA-106) : garder le pré-rendu statique, pas de bascule vers un rendu dynamique piloté par API

**Décision : conserver `generate_map.py` (pré-rendu HTML figé) plutôt que de réécrire la carte en Leaflet dynamique consommant `/api/listings` en direct.**

Fréquence de régénération : `generate_map.py` est déjà la **dernière étape** du DAG Airflow `oracle_annonces_pipeline` (`data_fusion → clean_immo → train_model → generate_map`, voir `Airflow/dags/oracle_annonces_dag.py`), planifié `schedule="0 22 * * 1"` (chaque lundi 22h). La carte est donc **régénérée automatiquement à chaque run du scraping**, jamais désynchronisée de plus d'un cycle de collecte — il n'existe pas de job de régénération séparé à recaler, c'est déjà aligné par construction.

Justification de garder le pré-rendu :
- Les annonces immobilières ne varient pas à l'échelle de l'heure : un rafraîchissement hebdomadaire, calé sur la fréquence réelle du scraping, est déjà aussi "frais" qu'une carte dynamique le serait — passer en rendu API-live n'avancerait pas la fraîcheur réelle des données, seulement la latence entre une donnée déjà en base et son affichage (qui n'existe pas ici : les deux sont mis à jour au même instant, dans le même run de pipeline).
- `generate_map.py` produit une mise en page riche (couches Cavaliers, lignes de métro reliées, popups avec photo hotlinkée et tracking de clic, contrat postMessage) : la réécrire en rendu client dynamique dupliquerait cette logique en JS (sélection de couches, sanitisation d'URL, calcul des tracés) sans bénéfice utilisateur mesurable.
- Le fichier généré reste **versionné dans git** (cohérent avec le reste du projet, cf. section ci-dessus) : un rendu dynamique perdrait cette propriété (reproductibilité, diff visible en revue de code).

**Cette décision doit être réévaluée si** : le scraping passe à une fréquence significativement plus élevée (quotidienne ou plus), ou si une fonctionnalité nécessite une mise à jour de la carte sans attendre le prochain run du DAG (ex. annonce retirée manuellement en urgence).

### 🧪 Tests frontend (Vitest + E2E Playwright)

* **`npm test`** (`frontend/`) — Vitest (environment jsdom, cohérent avec Vite) : tests unitaires (`services/api.js`, config Vite) et tests de composants React (`ChatOracle`, `SearchForm`, `MapComponent`, `ResultCard` — rendu, interactions clés, gestion d'erreur, export PDF). Exécuté en CI à chaque push/PR.
* **`npm run test:e2e`** (`frontend/`) — Playwright pilote le parcours utilisateur critique (saisie des critères → estimation affichée → carte visible → message chatbot → réponse reçue) contre le **vrai build de production** (`vite preview`, pas `npm run dev`) et un **vrai backend Flask** — `playwright.config.js` démarre les deux via `webServer` sur des ports dédiés (5055/4173), sans mock réseau. Fonctionne sans `GEMINI_API_KEY` (le backend répond alors avec un message explicite plutôt que planter). Job CI dédié (`e2e`) car il nécessite à la fois Python et Node.

### 🧪 Tests de scraping et canari Playwright

Deux niveaux de tests protègent les 6 scrapers contre une refonte silencieuse des sites sources :

* **`scripts/tests/test_scraper_extraction_fixtures.py`** (ORA-19) — tests unitaires rapides, sans réseau ni navigateur, basés sur une fixture HTML statique par site (`scripts/tests/fixtures/`) qui réutilise les sélecteurs CSS réels de chaque `scraper_*.py`. Exécutés à chaque push/PR (job `scrapers` de `.github/workflows/ci.yml`).
* **`scripts/tests/e2e/test_playwright_selectors.py`** (ORA-20) — canari Playwright qui navigue vers la page de résultats *live* de chaque site et vérifie que les sélecteurs actuels y retournent encore des annonces avec titre/prix non vides. Un échec logge explicitement `SÉLECTEUR CASSÉ (<site>)` pour le distinguer d'un incident réseau ponctuel. Ne remplace pas les scrapers de production (`undetected_chromedriver` reste nécessaire pour l'anti-bot) — sert uniquement de détecteur de changement HTML.

**Planification et alerte (ORA-21)** — `.github/workflows/scraper-selector-canary.yml` exécute le canari Playwright chaque jour à 1h UTC (une heure avant le DAG Airflow de 2h, pour alerter avant que le pipeline ETL ne tourne sur des données obsolètes/vides) et sur déclenchement manuel (`workflow_dispatch`). En cas d'échec, une issue GitHub `scraper-canari-alert` est créée automatiquement (ou un commentaire est ajouté si une issue ouverte existe déjà, pour éviter le spam d'échecs consécutifs).

**Procédure de triage lors d'une alerte :**
1. Ouvrir le log du run échoué et repérer le(s) message(s) `SÉLECTEUR CASSÉ (<site>)`.
2. Télécharger l'artefact `canary-diagnostics` du run (screenshot + HTML de la page au moment de l'échec, capturés automatiquement par `save_diagnostics()` dans le test) : il permet de voir immédiatement si la page a chargé normalement (site réellement changé) ou si Playwright a été bloqué (CAPTCHA, cookie-wall).
3. Si le site a réellement changé de structure : mettre à jour les sélecteurs dans `scripts/scraper_<site>.py` **et** la fixture correspondante dans `scripts/tests/fixtures/`.
4. Vérifier que les tests ORA-19 et le canari Playwright passent de nouveau.
5. Fermer l'issue.

**Faux-positifs anti-bot connus (confirmés via `canary-diagnostics` le 2026-08-03) :** PAP est bloqué par une page de challenge Cloudflare (`<title>Just a moment...</title>`) et SeLoger par un CAPTCHA DataDome (iframe `geo.captcha-delivery.com`) dès que Playwright headless nu y accède — contrairement à `undetected_chromedriver` (scrapers de production), Playwright n'a pas de patch anti-détection. Ce même jour, Orpi, ParuVendu et Vizzit avaient en revanche réellement changé de structure (titre Orpi, tag de carte ParuVendu, classe de carte Vizzit) — sélecteurs corrigés.

`PapSelectorCanaryTest` et `SeLogerSelectorCanaryTest` sont marqués `@unittest.expectedFailure` (le job CI reste vert malgré leur échec permanent, plutôt que de spammer l'issue GitHub chaque nuit). Si l'un des deux se met à passer un jour, pytest le remonte comme un "unexpected success" (échec du job) — signal qu'il vaut la peine d'enquêter plutôt que du bruit à ignorer.

### 🕵️ Anti-détection des scrapers — limites légales

Les 6 scrapers tirent à chaque run un User-Agent réaliste au hasard dans un pool (`scraping_config.json` → `user_agents`, via `scraper_utils.pick_user_agent()`), et supportent optionnellement un pool de proxies (`proxies`, vide/désactivé par défaut, via `pick_proxy()`).

**Ces mécanismes ne dispensent pas de respecter le cadre légal du scraping :**
* Ne pas contourner une mesure de blocage explicite (bannissement d'IP, CAPTCHA résolu manuellement de façon répétée, mur de paiement) — la rotation UA/proxy sert à réduire le risque de faux-positifs de détection anti-bot, pas à forcer un accès refusé.
* Respecter un rythme de requêtes raisonnable (la temporisation aléatoire déjà en place entre les requêtes) pour ne pas dégrader le service du site cible.
* Ne collecter que des données publiquement accessibles, à usage non commercial dans le cadre de ce projet.

**Revue robots.txt (ORA-67, 2026-08-03)** — chaque URL réellement ciblée par un scraper a été comparée mot pour mot aux règles `Disallow` du `robots.txt` du site correspondant :

| Site | URL ciblée par le scraper | Règle `robots.txt` (User-agent: `*`) | Conforme ? |
|---|---|---|---|
| Century21 | `/annonces/f/location-maison-appartement/v-lyon/page-{}/` | `Disallow: /annonces/f/` | ❌ Non |
| Orpi | `/recherche/rent?transaction=rent...` | `Disallow: /recherche/*` | ❌ Non |
| PAP | `/annonce/...-a-partir-du-2-pieces?page={}` | `Disallow: /*?*` (toute URL avec query string) | ❌ Non |
| SeLoger | `/classified-search?distributionTypes=...` | `Disallow: /classified-search?` | ❌ Non |
| ParuVendu | `/immobilier/recherche/location/lyon/?rechpv=1...` | Aucune règle correspondante trouvée | ✅ Oui |
| Vizzit | `/fr/properties/{}?searchQuery=...` | Aucune règle correspondante trouvée (note : `ClaudeBot` est bloqué nommément ailleurs dans ce fichier, sans rapport avec ce scraper) ; `Crawl-delay: 1` déjà respecté par la temporisation existante | ✅ Oui |

**Décision explicite (posture du projet) :** 4 des 6 scrapers ciblent des chemins explicitement disallow par le site source. Le `robots.txt` n'a pas de valeur contractuelle contraignante (contrairement aux CGU), mais signale une volonté explicite du site. Décision assumée : **ne pas modifier les scrapers en production**, compte tenu du contexte du projet — usage non commercial/portfolio, volumes de requêtes faibles et temporisés, aucune donnée personnelle sensible collectée (annonces publiques uniquement), aucune republication de contenu protégé (voir point suivant). Le risque résiduel (accès jugé non souhaité par le site, même sans base légale contraignante) est assumé explicitement plutôt qu'ignoré. Cette décision est à réévaluer si l'usage du projet change (volumes, contexte commercial).

**Affichage des annonces — photo hébergée vs lien (ORA-93, epic ORA-80) :** vérifié dans les en-têtes CSV de sortie des 6 scrapers (`atomic_csv_writer(OUTPUT_PATH, [...])` dans chaque `scraper_*.py`) : aucune colonne photo/image n'est collectée ni stockée, sur aucun des 6 sites. Chaque annonce n'expose que des champs texte (titre, prix, lieu, détails) et un lien `Lien` vers l'annonce originale. L'application n'héberge donc aucune photo scrapée — elle renvoie vers la source, à la manière d'un agrégateur/moteur de recherche. Ceci limite significativement le risque de reproduction non autorisée de contenu protégé (photos) par rapport à un hébergement direct.

**Décision explicite (ORA-94, epic ORA-80) :** ce constat est formalisé en décision produit dans [`LEGAL_DECISIONS.md`](./LEGAL_DECISIONS.md) — l'application ne doit jamais héberger de photo d'annonce scrapée (ni capture d'écran du site source en guise de thumbnail), uniquement un lien de redirection vers l'annonce d'origine. Implication directe pour les tickets frontend ORA-87/ORA-88/ORA-89 : pas de balise `<img>` pointant vers une photo scrapée dans les composants d'affichage des annonces.

### 📦 Versioning des snapshots de données

Chaque exécution de `train_model.py` archive un instantané de `master_immo_final.csv` via `backend/scripts/data_versioning.py` (équivalent léger à DVC, sans dépendance ni stockage distant à configurer) :

* **`backend/data/snapshots/master_immo_final_<sha256>.csv`** — une copie content-addressée du jeu de données (un re-run sur des données identiques ne duplique pas le fichier, seul le hash change si les données changent). Ces fichiers sont versionnés dans git au même titre que le reste de `backend/data/`.
* **`backend/data/snapshots/manifest.csv`** — historique de chaque snapshot (timestamp, sha256, fichier, nombre de lignes).
* **`backend/models/price_predictor.pkl.meta.json`** — référence explicitement, pour le modèle entraîné, le `data_snapshot_sha256`/`data_snapshot_file` utilisé ainsi que les métriques (MAE, R²). Versionné dans git comme le `.pkl` qu'il décrit (ORA-29).

`manifest.csv` alimente aussi `/api/quartier-historique` (ORA-72, `backend/services/price_history.py`) : évolution du prix moyen/m² par quartier à travers les snapshots disponibles, affichée dans l'UI (`PriceHistory.jsx`) sous le résultat d'une recherche. Avec un seul snapshot enregistré (état actuel du projet), l'API renvoie `status: "insufficient_history"` plutôt qu'une tendance fictive à un seul point — le tableau se peuplera naturellement au fil des prochains entraînements.

**Fréquence des snapshots (ORA-129) :** `train_model.py` — donc `snapshot_dataset()` — s'exécute une fois par run du DAG Airflow `oracle_annonces_pipeline` (`schedule="0 22 * * 1"`, chaque lundi 22h Europe/Paris ; voir "Pipeline ETL" ci-dessus). En régime nominal, c'est donc **une nouvelle ligne par semaine** dans `manifest.csv`. Ceci n'est **pas un SLA vérifié activement** : contrairement au canari scrapers et au monitoring de dérive (tous deux ci-dessous), qui tournent en GitHub Actions indépendamment d'Airflow et alertent sur un GitHub issue en cas d'échec, rien n'alerte spécifiquement si un run hebdomadaire du DAG annonces est sauté ou échoue avant `train_model.py` — la machine hébergeant Airflow n'est pas garantie allumée à 22h (voir commentaire dans `oracle_annonces_dag.py`). `manifest.csv` (colonne `timestamp`) reste donc la seule source de vérité sur la cadence réellement observée, pas le planning déclaré du DAG.

**Reproduire un ancien modèle à partir de son snapshot :**
1. Récupérer le `data_snapshot_sha256` voulu (depuis un `price_predictor.pkl.meta.json` conservé, ou depuis `backend/data/snapshots/manifest.csv`).
2. Copier le snapshot correspondant par-dessus les données actives : `cp backend/data/snapshots/master_immo_final_<sha256>.csv backend/data/master_immo_final.csv`.
3. Relancer `python backend/scripts/train_model.py` — le modèle est ré-entraîné sur exactement les mêmes données, et un nouveau `.meta.json` confirme le même `data_snapshot_sha256`.

### 🔖 Versioning du modèle et rollback sans réentraîner

Le mécanisme ci-dessus reproduit un ancien modèle en **ré-entraînant** sur son snapshot de données. Pour un retour arrière immédiat (ex : le modèle fraîchement entraîné se comporte mal en production), chaque run archive aussi une copie binaire prête à l'emploi :

* **`backend/models/versions/price_predictor_<model_version>.pkl`** — copie du modèle archivée sous son hash (`model_version` = sha256 tronqué du binaire, présent dans `price_predictor.pkl.meta.json`). Versionnée dans git.
* **`GET /api/health`** — expose `model_version`, `trained_at` et `metrics` (MAE/R²) du modèle actuellement chargé par le backend.
* **`python backend/scripts/rollback_model.py <model_version>`** — restaure instantanément cette version comme modèle actif (`price_predictor.pkl`) et met à jour `.meta.json`, **sans ré-entraîner**.

### 📈 Monitoring de dérive (drift) des prédictions (ORA-33)

`backend/scripts/monitor_drift.py` compare la distribution des features numériques du modèle (mêmes colonnes que `train_model.py`) et de la cible `prix` — utilisée en proxy de dérive des prédictions, faute de journal de prédictions live — entre les données actuelles (`master_immo_final.csv`) et un snapshot de référence **glissant** tiré de `backend/data/snapshots/manifest.csv` (celui d'il y a 7 runs de retraining, pas le tout premier snapshot du projet : sinon, le marché évoluant naturellement sur plusieurs mois, la comparaison finirait par toujours signaler une dérive de façon permanente et non actionnable).

La comparaison utilise un test de Kolmogorov-Smirnov à deux échantillons par feature ; une dérive est signalée sur la taille d'effet (statistique D > 0.15), pas uniquement la p-value (qui devient quasi toujours significative sur de gros volumes même pour un écart négligeable).

* **`backend/data/drift_reports/drift_report_latest.json`** — dernier état (dérive détectée ou non, détail par feature). Versionné dans git.
* **`backend/data/drift_reports/drift_history.jsonl`** — historique append-only de chaque exécution, pour visualiser la tendance dans le temps.
* **`.github/workflows/model-drift-monitor.yml`** — exécute le contrôle chaque lundi à 3h UTC (et sur `workflow_dispatch`), commite le rapport mis à jour, et ouvre/commente une issue GitHub `model-drift-alert` en cas de dérive détectée (même mécanisme de dédoublonnage que le canari scrapers).
* Avec un seul snapshot enregistré (état initial du projet), le rapport indique explicitement `"status": "insufficient_history"` plutôt que de prétendre à tort qu'il n'y a pas de dérive.

---

## 🗂️ Arborescence du Projet

```text
oracle-des-loyers/
├── docker-compose.yml         # Chef d'orchestre des conteneurs (backend, frontend, Airflow)
├── README.md                  # Ce fichier
│
├── Airflow/                   # Orchestration du pipeline ETL (2 DAG planifiés, cf. section ETL)
│   └── dags/oracle_cavaliers_dag.py, oracle_annonces_dag.py
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
│   ├── data/                  # LE COFFRE-FORT (CSV bruts, fusionnés, master, snapshots)
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
│   │   ├── data_loader.py, predictor.py, utils.py
│   │
│   ├── core/                  # Constantes partagées
│   └── tests/                 # Suite pytest (chat, config runtime, ETL, modèle...)
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

> **ORA-36** : les modules `smart_agent.py`/`prompt_system.py`/`conversation_manager.py` (ancienne architecture de chatbot "Oracle de Lyon", jamais branchée sur `app.py`) ont été supprimés, ainsi que `backend/data/conversations.db` qu'ils écrivaient — voir [`PRIVACY.md`](./PRIVACY.md) pour la politique de rétention des données de conversation.
