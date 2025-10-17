# database/crud.py
from . import get_db_connection
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def get_log_by_session(session_id):
    """Получает лог по session_id"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM logs WHERE session_id = ?', (session_id,))
    log = cursor.fetchone()
    
    conn.close()
    return dict(log) if log else None

def create_or_update_log(session_id, masked_pan, booking_id, client_id, step):
    """Создает или обновляет лог, сохраняя taken_by при обновлении"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    existing_log = get_log_by_session(session_id)
    
    if existing_log:
        # Сохраняем taken_by из существующей записи
        taken_by = existing_log.get('taken_by')
        
        # Обновляем запись
        cursor.execute('''
            UPDATE logs 
            SET masked_pan = ?, booking_id = ?, client_id = ?, step = ?, updated_at = datetime('now')
            WHERE session_id = ?
        ''', (masked_pan, booking_id, client_id, step, session_id))
    else:
        # Создаем новую запись
        cursor.execute('''
            INSERT INTO logs (session_id, masked_pan, booking_id, client_id, step, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (session_id, masked_pan, booking_id, client_id, step))
    
    conn.commit()
    conn.close()
    return get_log_by_session(session_id)

def update_log_taken_by(session_id, user_id):
    """Обновляет taken_by для лога"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE logs 
        SET taken_by = ?, updated_at = datetime('now')
        WHERE session_id = ?
    ''', (user_id, session_id))
    
    conn.commit()
    conn.close()

def release_log(session_id):
    """Освобождает лог (сбрасывает taken_by)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE logs 
        SET taken_by = NULL, updated_at = datetime('now')
        WHERE session_id = ?
    ''', (session_id,))
    
    conn.commit()
    conn.close()

def find_card_duplicates(masked_pan):
    """Находит дубликаты карт"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM logs 
        WHERE masked_pan = ? 
        ORDER BY created_at DESC
    ''', (masked_pan,))
    
    duplicates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return duplicates

def get_unique_logs_last_24h():
    """Возвращает уникальные логи за последние 24 часа"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT masked_pan, booking_id, client_id, created_at
        FROM logs
        WHERE datetime(created_at) >= datetime('now', '-1 day')
        ORDER BY created_at DESC
    """)
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs