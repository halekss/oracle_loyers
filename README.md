# 🔮 L'Oracle des Loyers

> *"Ce T2 est cher, mais c'est le prix à payer pour être à 30m d'un café de spécialité sans entendre les sirènes de l'hôpital voisin."*

**L'Oracle des Loyers** est une application immobilière intelligente (et un peu cynique) capable d'estimer la "Vraie Valeur" d'un bien à Lyon.
Au-delà des données classiques (surface, prix), l'Oracle croise les données avec **"Les 4 Cavaliers"** de l'environnement urbain pour affiner ses prédictions et ses conseils :

1.  🐴 **Gentrification** (Cafés de spécialité, Yoga, Épiceries fines) -> *Fait monter les prix.*
2.  🐴 **Vice** (Kebabs, Tabacs, Sex-shops, Casinos) -> *Impact variable (bruit vs commodité).*
3.  🐴 **Nuisance** (Bars de nuit, Voies ferrées, Urgences) -> *Fait baisser les prix.*
4.  🐴 **Superstition** (Cimetières, Pompes funèbres) -> *Impact psychologique à la baisse.*

---

## 🏗️ Architecture Technique

Le projet repose sur une architecture moderne conteneurisée :

* **Frontend (Le Visage) 🎨** : React, TailwindCSS, Leaflet (Cartographie).
* **Backend (Le Cerveau) 🧠** : Flask (Python).
* **Intelligence Artificielle** :
    * **Prediction** : XGBoost (Machine Learning sur données structurées).
    * **Chatbot** : LLM local via **LM Studio** (Mistral/Llama) enrichi par RAG (Retrieval Augmented Generation).
* **Infrastructure** : Docker & Docker Compose.

---

## 🚀 Installation & Lancement (Recommandé : Docker)

C'est la méthode la plus simple pour lancer tout le projet (Front + Back + Base de données).

### Prérequis
* **Docker Desktop** installé et lancé.
* **LM Studio** (pour le Chatbot).

### 1. Configuration de l'IA (LM Studio)
Pour que l'Oracle puisse parler, il a besoin d'un cerveau local.

1.  Ouvrez **LM Studio**.
2.  Chargez un modèle (ex: `Mistral-7B-Instruct` ou `Hermes`).
3.  Allez dans l'onglet **Local Server** (<->).
4.  Cochez **"Enable CORS"** (Options à droite) pour autoriser les requêtes.
5.  Cliquez sur **Start Server**.

### 2. Lancement de l'application
Ouvrez un terminal à la racine du projet :

```bash
# Construire et lancer les conteneurs
docker-compose up --build
```

Une fois lancé, accédez à :
* 📱 **Frontend (Site Web)** : [http://localhost:5173](http://localhost:5173) (ou 3000 selon config)
* ⚙️ **Backend (API)** : [http://localhost:5000](http://localhost:5000)

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
│   ├── data/                  # LE COFFRE-FORT 💎
│   │   ├── base_de_donnees_immo_lyon_complet.csv
│   │   ├── cavaliers_lyon.csv
│   │   └── master_immo_final.csv
│   │
│   ├── models/                # Cerveaux entraînés
│   │   └── price_predictor.pkl
│   │
│   ├── scripts/               # L'USINE À DONNÉES ⚙️
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

---

## 🧠 Fonctionnalités Clés

### 1. La Carte Interactive 🗺️
Visualisation de toutes les annonces. Les marqueurs changent de couleur selon le prix au m², révélant les zones de tension. Les points sont placés intelligemment pour respecter la géographie des quartiers.

### 2. Prédiction de Prix (Machine Learning) 🤖
L'utilisateur clique sur un point ou entre une surface. L'Oracle prédit le loyer "juste" en se basant sur :
* La surface.
* La localisation précise (Latitude/Longitude).
* La proximité immédiate des 4 Cavaliers (ex: "Ce bien vaut moins cher car il est collé à une boîte de nuit").

### 3. Chatbot Contextuel (LLM) 💬
Une interface de chat permet de discuter avec l'Oracle.
* Il connaît le prix moyen réel par quartier (grâce aux données CSV).
* Il adopte une personnalité cynique et locale.
* Il utilise le contexte géographique (RAG) pour répondre précisément aux questions comme *"C'est cher la Croix-Rousse ?"*.