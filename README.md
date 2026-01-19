    # 🔮 L'Oracle des Loyers

    > *"Ce T2 est cher, mais c'est le prix à payer pour être à 30m d'un café de spécialité sans entendre les sirènes de l'hôpital voisin."*

    **L'Oracle des Loyers** est un assistant intelligent et cynique capable d'estimer la "Vraie Valeur" d'un bien immobilier. Au-delà des données classiques (surface, DPE), l'Oracle croise les prix avec **"Les 4 Cavaliers"** de l'environnement urbain :
    1.  🐴 **Gentrification** (Cafés latte, Magasins Bio, Yoga)
    2.  🐴 **Vice** (Kebabs, Tabacs, Sex-shops)
    3.  🐴 **Nuisance** (Bars de nuit, Voies ferrées, Urgences)
    4.  🐴 **Superstition** (Cimetières, Pompes funèbres)

    ---

    ## 🏗️ Architecture Technique

    Le projet fonctionne sur une architecture **Client-Serveur** découplée :

    * **Backend (Le Cerveau) 🧠** : 
        * Language : **Python 3.12+**
        * Framework API : **FastAPI**
        * Data & ML : Pandas, GeoPandas, Scikit-learn, XGBoost.
        * Scraping : Selenium, BeautifulSoup4.
        * Geo : OSMPythonTools (OpenStreetMap).
    * **Frontend (Le Visage) 🎨** : 
        * Framework : **React** (via Vite).
        * Langage : JavaScript (ES6+).
        * Communication : Fetch API vers le port 8000.

    ---

    ## ⚡ Prérequis

    Avant de commencer, assurez-vous d'avoir installé :
    * [Python 3.12+](https://www.python.org/)
    * [Node.js](https://nodejs.org/) (incluant `npm`)
    * [Git](https://git-scm.com/)

    ---

    ## 🛠️ Installation (Première fois)

    Clonez ce dépôt, puis suivez ces deux étapes pour initialiser les deux moteurs.

    ### 1. Installation du Backend (Python)

    Ouvrez un terminal à la racine du projet :

    ```bash
    cd backend

    # 1. Création de l'environnement virtuel (isolé)
    python -m venv .venv

    # 2. Activation de l'environnement
    # Sur Windows (Git Bash) :
    source .venv/Scripts/activate
    # Sur Mac/Linux :
    # source .venv/bin/activate

    # 3. Installation des dépendances
    pip install -r requirements.txt
    ```
    ### 2. Installation du Frontend (React)

    ```bash
    cd frontend

    # Installation des paquets Node.js
    npm install
    ```

    ## 🚀 Démarrage Quotidien (Routine)
    Pour travailler sur le projet, vous devez lancer deux terminaux en parallèle.

    ### Terminal 1 : Lancer l'API (Backend)
    C'est le serveur qui fait les calculs et le Machine Learning.

    ```bash
    cd backend

    # ⚠️ IMPORTANT : Toujours activer l'environnement avant !
    source .venv/Scripts/activate

    # Lancer le serveur (recharge auto à chaque sauvegarde)
    uvicorn main:app --reload
    ```
    L'API sera accessible sur : http://127.0.0.1:8000

    ### Terminal 2 : Lancer l'Interface (Frontend)
    C'est le site web visible par l'utilisateur.

    ```bash
    cd frontend

    # Lancer le serveur de développement
    npm run dev
    ```

    ## 🗂️ Structure du Projet

    oracle-des-loyers/
    ├── .env                       # Variables d'environnement (API Keys)
    ├── .venv/                     # Environnement Virtuel Python (Global)
    ├── requirements.txt           # Liste des dépendances Python
    │
    ├── data/                      # LE COFFRE-FORT 💎 (Données CSV)
    │   ├── base_de_donnees_immo_lyon_complet.csv
    │   └── master_immo_final.csv
    │
    ├── scripts/                   # L'USINE À DONNÉES ⚙️ (ETL)
    │   ├── scraper_orpi.py        # Robots de collecte
    │   ├── geocoding_jitter.py    # Enrichissement géographique
    │   └── merge_csv.py           # Fusion des sources
    │
    ├── backend/                   # LE CERVEAU 🧠 (API)
    │   ├── models/                # Modèles ML entraînés (.joblib)
    │   ├── src/                   # Code source interne de l'API
    │   └── main.py                # Point d'entrée du serveur FastAPI
    │
    ├── notebooks/                 # Brouillons & Explorations Jupyter
    │
    └── frontend/                  # LE VISAGE 🎨 (React)
        ├── src/
        └── package.json

