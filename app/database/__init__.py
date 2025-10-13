# database/__init__.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'logs.db')

def get_db_connection():
    """Возвращает соединение с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_cursor():
    """Возвращает курсор базы данных"""
    conn = get_db_connection()
    return conn, conn.cursor()