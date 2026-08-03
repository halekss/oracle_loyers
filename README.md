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

### 1. Configuration de l'IA (Gemini)
Copiez [`.env.example`](./.env.example) en `.env` à la racine et renseignez au minimum `GEMINI_API_KEY` (les autres variables ont des valeurs par défaut raisonnables).

```bash
cp .env.example .env
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

Toute l'intelligence de l'Oracle repose sur la qualité de ses données. Les scripts se trouvent dans `backend/scripts/`, orchestrés par le DAG Airflow `Airflow/dags/oracle_loyers_dag.py` (planifié quotidiennement à 2h) selon deux branches parallèles qui convergent :

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
    * Génère le fichier modèle : `backend/models/price_predictor.pkl` (non versionné dans git — à régénérer localement).

> Les scrapers (`scripts/scraper_*.py`, à la racine du dépôt) ne font **pas** partie du DAG Airflow : ils s'exécutent manuellement pour rafraîchir les CSV d'annonces avant de relancer le pipeline.

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
│   └── api_overpass.py, api_data_gouv.py  # ⚠️ dupliqués avec backend/scripts/, voir Backlog
│
├── backend/                   # API Flask & Logique métier
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                 # Point d'entrée serveur actif (Routes API Flask)
│   │
│   ├── data/                  # LE COFFRE-FORT (CSV bruts, fusionnés, master, conversations.db)
│   ├── models/                # Cerveaux entraînés (price_predictor.pkl, non versionné en git)
│   │
│   ├── scripts/               # L'USINE À DONNÉES (voir section ETL pour l'ordre réel)
│   │   ├── api_overpass.py, enrich_cavaliers_cp.py
│   │   ├── data_fusion.py, clean_immo.py, train_model.py
│   │   └── generate_map.py, analyze_impact.py, test_prediction.py, test_api.py
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
