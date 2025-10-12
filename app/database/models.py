import sqlite3

def init_db():
    with sqlite3.connect('logs.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                session_id TEXT PRIMARY KEY,
                masked_pan TEXT,
                booking_id TEXT,
                client_id TEXT, 
                taken_by INTEGER,
                step TEXT DEFAULT 'full',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Новая таблица для истории карт
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                card_number TEXT NOT NULL,
                booking_id TEXT,
                client_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES logs (session_id) ON DELETE CASCADE
            )
        ''')
        
        # Уникальный индекс для предотвращения дублирования записей
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_session_card 
            ON card_history(session_id, card_number)
        ''')
        
        # Индекс для быстрого поиска по номеру карты
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_number ON card_history(card_number)')
        conn.commit()