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

## IA: local vs cloud

Le projet sait documenter deux modes d'exécution LLM:

* **LM Studio en local** : utile pour montrer la maîtrise d'un LLM self-hosted/local, sans dépendre d'un provider externe. Ce mode demande une machine locale allumée et assez puissante, ce qui le rend moins adapté à une démo portfolio publique.
* **Google AI / Gemini** : mode retenu pour le déploiement portfolio. Il évite le serveur GPU/local, s'intègre simplement côté backend et le free tier suffit généralement pour une démonstration à trafic modéré.

Le backend actif garde la clé API uniquement côté serveur via `GEMINI_API_KEY`. Le modèle par défaut est `gemini-2.5-flash`, avec des réponses courtes et un contexte RAG borné pour limiter les coûts et les délais.

Variables disponibles:

```bash
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_OUTPUT_TOKENS=800
GEMINI_TEMPERATURE=0.7
```

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
Pour qu'Immotep, le chatbot de l'Oracle, puisse parler en déploiement portfolio, configurez Gemini côté backend.

```bash
export GEMINI_API_KEY="votre-cle-google-ai"
export GEMINI_MODEL="gemini-2.5-flash"
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

Variables utiles :

```bash
GEMINI_API_KEY="votre-cle-google-ai"
GEMINI_MODEL="gemini-2.5-flash"
CORS_ORIGINS="https://oracle-loyers.onrender.com"
```

`CORS_ORIGINS` est optionnel. S'il n'est pas défini, le backend garde un CORS ouvert pour éviter de bloquer une démo.

### Frontend

Le frontend lit l'URL de l'API via Vite :

```bash
VITE_API_URL="https://votre-backend.onrender.com/api"
```

Sur Render, cette variable est obligatoire. En local seulement, si `VITE_API_URL` n'est pas défini, le frontend utilise `http://localhost:5000/api`.

---

## ⚙️ Les Scripts de Données (ETL)

Toute l'intelligence de l'Oracle repose sur la qualité de ses données. Les scripts se trouvent dans `backend/scripts/`.

Voici l'ordre logique d'exécution pour régénérer la base de données :

1.  **`enrich_cavaliers_cp.py`**
    * Récupère les coordonnées GPS des cavaliers (commerces) et leur attribue un code postal précis via l'API Data Gouv (Batch processing).
    * *Input :* `cavaliers_lyon.csv` (brut) -> *Output :* `cavaliers_lyon.csv` (enrichi avec CP).

2.  **`geocoding_jitter.py`**
    * Place les annonces immobilières sur la carte.
    * *Innovation :* Utilise l'enveloppe convexe (Convex Hull) des cavaliers pour dessiner la forme réelle des quartiers et éviter de placer des points dans le Rhône, tout en respectant les limites administratives.

3.  **`compute_features.py`**
    * Le cœur du calcul. Pour chaque annonce, calcule la distance exacte vers les points d'intérêt (Kebab le plus proche, densité de bars à 500m, etc.).
    * Génère le fichier "Gold Standard" : `master_immo_final.csv`.

4.  **`train_model.py`**
    * Entraîne le modèle XGBoost sur les données calculées.
    * Génère le fichier modèle : `backend/models/price_predictor.pkl`.

---

## 🗂️ Arborescence du Projet

```text
oracle-des-loyers/
├── docker-compose.yml         # Chef d'orchestre des conteneurs
├── README.md                  # Ce fichier
│
├── backend/                   # API Flask & Logique métier
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                 # Point d'entrée serveur (Routes API)
│   │
│   ├── data/                  # LE COFFRE-FORT
│   │   ├── base_de_donnees_immo_lyon_complet.csv
│   │   ├── cavaliers_lyon.csv
│   │   └── master_immo_final.csv
│   │
│   ├── models/                # Cerveaux entraînés
│   │   └── price_predictor.pkl
│   │
│   ├── scripts/               # L'USINE À DONNÉES
│   │   ├── enrich_cavaliers_cp.py
│   │   ├── geocoding_jitter.py
│   │   ├── compute_features.py
│   │   └── train_model.py
│   │
│   ├── services/              # Modules utilitaires
│   │   ├── data_loader.py
│   │   └── map_generator.py
│   │
│   └── static/                # Fichiers servis publiquement (Cartes HTML)
│
└── frontend/                  # Interface React
    ├── Dockerfile
    ├── package.json
    ├── public/
    └── src/
        ├── components/
        │   ├── ChatOracle.jsx # Composant Chatbot
        │   ├── Map.jsx        # Composant Carte Interactive
        │   └── Sidebar.jsx    # Formulaire de prédiction
        └── services/
            └── api.js         # Pont vers le backend
```
