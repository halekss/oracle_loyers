import sqlite3
import os

# On stocke la DB dans le dossier backend/src
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "immo.db")

def get_db_connection():
    """Crée une connexion à la base de données."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Permet d'accéder aux colonnes par nom (row['prix'])
    return conn

def init_db():
    """Initialise la table 'annonces' si elle n'existe pas."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Création de la table
    # On met une contrainte UNIQUE sur (titre, prix, surface) pour éviter les doublons simples
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS annonces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT,
            prix INTEGER,
            surface REAL,
            prix_m2 REAL,
            cp TEXT,
            ville TEXT,
            source TEXT DEFAULT 'csv_import',
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_annonce UNIQUE (titre, prix, cp)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Base de données initialisée : {DB_PATH}")

if __name__ == "__main__":
    # Si on lance ce fichier directement, ça crée la table
    init_db()