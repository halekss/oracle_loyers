import sqlite3
import json
from datetime import datetime
import os

class ConversationManager:
    """
    Gère la sauvegarde et le chargement des conversations.
    Utilise SQLite pour la persistance (simple, pas besoin de serveur).
    """
    
    def __init__(self, db_path='data/conversations.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Crée la table si elle n'existe pas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                oracle_response TEXT NOT NULL,
                context TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session 
            ON conversations(session_id, timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_message(self, session_id, user_message, oracle_response, context=None):
        """Sauvegarde un échange"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversations (session_id, user_message, oracle_response, context)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_message, oracle_response, json.dumps(context) if context else None))
        
        conn.commit()
        conn.close()
    
    def get_history(self, session_id, limit=10):
        """
        Récupère l'historique d'une session.
        Retourne les N derniers messages.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_message, oracle_response, context, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (session_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Inverser pour avoir du plus ancien au plus récent
        history = []
        for row in reversed(rows):
            history.append({
                'user': row[0],
                'oracle': row[1],
                'context': json.loads(row[2]) if row[2] else None,
                'timestamp': row[3]
            })
        
        return history
    
    def format_history_for_llm(self, session_id, limit=5):
        """
        Formate l'historique pour l'inclure dans le prompt LLM.
        Garde seulement les N derniers échanges.
        """
        history = self.get_history(session_id, limit)
        
        if not history:
            return ""
        
        formatted = "HISTORIQUE DE LA CONVERSATION:\n"
        for msg in history:
            formatted += f"User: {msg['user']}\n"
            formatted += f"Oracle: {msg['oracle']}\n\n"
        
        return formatted
    
    def clear_session(self, session_id):
        """Efface l'historique d'une session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM conversations WHERE session_id = ?', (session_id,))
        
        conn.commit()
        conn.close()
    
    def get_all_sessions(self):
        """Liste toutes les sessions actives"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT session_id, MAX(timestamp) as last_active
            FROM conversations
            GROUP BY session_id
            ORDER BY last_active DESC
        ''')
        
        sessions = cursor.fetchall()
        conn.close()
        
        return [{'session_id': s[0], 'last_active': s[1]} for s in sessions]