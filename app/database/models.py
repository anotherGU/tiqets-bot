# database/models.py
from . import get_db_connection

def init_db():
    """Инициализирует базу данных"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            masked_pan TEXT NOT NULL,
            booking_id TEXT,
            client_id TEXT,
            step TEXT,
            taken_by INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")