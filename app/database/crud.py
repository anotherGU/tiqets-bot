import sqlite3
import datetime
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('logs.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def create_or_update_log(session_id, masked_pan, booking_id, client_id, step):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO logs (session_id, masked_pan, booking_id, client_id, step, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, masked_pan, booking_id, client_id, step, datetime.datetime.now()))
        
        # Сохраняем карту в историю (только если есть номер карты)
        if masked_pan and len(masked_pan.replace(' ', '')) >= 6:
            clean_card = masked_pan.replace(' ', '')
            cursor.execute('''
                INSERT OR IGNORE INTO card_history (session_id, card_number, booking_id, client_id)
                VALUES (?, ?, ?, ?)
            ''', (session_id, clean_card, booking_id, client_id))
        
        conn.commit()

def get_log_by_session(session_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM logs WHERE session_id = ?', (session_id,))
        return cursor.fetchone()

def update_log_taken_by(session_id, user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE logs 
            SET taken_by = ?, updated_at = ?
            WHERE session_id = ?
        ''', (user_id, datetime.datetime.now(), session_id))
        conn.commit()

def find_card_duplicates(card_number):
    """Находит все случаи использования карты"""
    if not card_number or len(card_number.replace(' ', '')) < 6:
        return []
        
    clean_card = card_number.replace(' ', '')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ch.session_id, ch.card_number, ch.booking_id, ch.client_id, ch.created_at,
                   l.taken_by, l.step
            FROM card_history ch
            LEFT JOIN logs l ON ch.session_id = l.session_id
            WHERE ch.card_number = ?
            ORDER BY ch.created_at DESC
        ''', (clean_card,))
        return cursor.fetchall()