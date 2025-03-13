import sqlite3
from config import DATABASE_NAME

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Создаем таблицу пользователей
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            current_character TEXT DEFAULT 'default',
            communication_style TEXT DEFAULT 'formal',
            analysis_depth TEXT DEFAULT 'detailed',
            language TEXT DEFAULT 'ru',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Создаем таблицу истории диалогов
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            character TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        self.conn.commit()

    def add_user(self, user_id: int, username: str):
        self.cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                          (user_id, username))
        self.conn.commit()

    def get_user_settings(self, user_id: int):
        self.cursor.execute('''
        SELECT current_character, communication_style, analysis_depth, language 
        FROM users WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()

    def update_user_settings(self, user_id: int, **settings):
        update_fields = ', '.join([f"{key} = ?" for key in settings.keys()])
        query = f'UPDATE users SET {update_fields} WHERE user_id = ?'
        values = tuple(settings.values()) + (user_id,)
        self.cursor.execute(query, values)
        self.conn.commit()

    def add_chat_history(self, user_id: int, message: str, response: str, character: str):
        self.cursor.execute('''
        INSERT INTO chat_history (user_id, message, response, character)
        VALUES (?, ?, ?, ?)
        ''', (user_id, message, response, character))
        self.conn.commit()

    def get_user_history(self, user_id: int, limit: int = 10):
        self.cursor.execute('''
        SELECT message, response, character, timestamp 
        FROM chat_history 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (user_id, limit))
        return self.cursor.fetchall()

    def __del__(self):
        self.conn.close() 