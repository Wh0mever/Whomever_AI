import aiosqlite
import asyncio
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from config import DATABASE_NAME

class Database:
    def __init__(self):
        self.db_path = DATABASE_NAME
        
    # Метод get_connection больше не нужен - используем прямые соединения

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as conn:
            await self.create_tables(conn)

    async def create_tables(self, conn: aiosqlite.Connection):
        """Создание всех необходимых таблиц"""
        
        # Таблица пользователей
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            current_character TEXT DEFAULT 'default',
            communication_style TEXT DEFAULT 'formal',
            analysis_depth TEXT DEFAULT 'detailed',
            language TEXT DEFAULT 'ru',
            personality_profile TEXT DEFAULT '{}',
            is_founder BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица чатов (групповые и приватные)
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_type TEXT NOT NULL, -- 'private', 'group', 'supergroup'
            title TEXT,
            description TEXT,
            chat_settings TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица участников чатов
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_members (
            chat_id INTEGER,
            user_id INTEGER,
            role TEXT DEFAULT 'member', -- 'member', 'admin', 'creator'
            nickname TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message_count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')

        # Расширенная таблица истории сообщений
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            message_id INTEGER,
            message_text TEXT,
            bot_response TEXT,
            character_used TEXT,
            is_whomever_call BOOLEAN DEFAULT FALSE,
            context_summary TEXT,
            mentions TEXT DEFAULT '[]', -- JSON список упомянутых пользователей
            reply_to_message_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processing_time REAL,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')

        # Таблица контекстной памяти для каждого чата
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            context_type TEXT, -- 'topic', 'user_info', 'ongoing_discussion'
            context_key TEXT,
            context_value TEXT,
            relevance_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
        )
        ''')

        # Таблица для хранения профилей пользователей в контексте чата
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS user_chat_profiles (
            chat_id INTEGER,
            user_id INTEGER,
            interests TEXT DEFAULT '[]',
            communication_patterns TEXT DEFAULT '{}',
            personality_traits TEXT DEFAULT '{}',
            topic_preferences TEXT DEFAULT '{}',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(chat_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        
        await conn.commit()

    async def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавление или обновление пользователя"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Проверяем, является ли пользователь основателем (добавлен новый ID)
            founder_ids = [1914567632]  # Shokha и основатель WHOMEVER
            is_founder = user_id in founder_ids or (username and username.lower() in ['shokha', 'whomever_ceo'])
            
            await conn.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, is_founder, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, is_founder, datetime.now().isoformat()))
            await conn.commit()

    async def add_chat(self, chat_id: int, chat_type: str, title: str = None, description: str = None):
        """Добавление нового чата"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
            INSERT OR REPLACE INTO chats (chat_id, chat_type, title, description, last_message_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (chat_id, chat_type, title, description))
            await conn.commit()

    async def add_chat_member(self, chat_id: int, user_id: int, role: str = 'member', nickname: str = None):
        """Добавление участника в чат"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
            INSERT OR REPLACE INTO chat_members 
            (chat_id, user_id, role, nickname, last_seen)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (chat_id, user_id, role, nickname))
            await conn.commit()

    async def get_user_settings(self, user_id: int) -> Optional[Tuple]:
        """Получение настроек пользователя"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute('''
            SELECT current_character, communication_style, analysis_depth, language, is_founder
        FROM users WHERE user_id = ?
        ''', (user_id,))
            return await cursor.fetchone()

    async def update_user_settings(self, user_id: int, **settings):
        """Обновление настроек пользователя"""
        if not settings:
            return
            
        fields = []
        values = []
        for key, value in settings.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        fields.append("last_active = CURRENT_TIMESTAMP")
        
        async with aiosqlite.connect(self.db_path) as conn:
            query = f'UPDATE users SET {", ".join(fields)} WHERE user_id = ?'
            values.append(user_id)
            await conn.execute(query, values)
            await conn.commit()

    async def add_chat_history(self, chat_id: int, user_id: int, message_id: int, message_text: str, 
                             bot_response: str, character: str, is_whomever_call: bool = False,
                             context_summary: str = None, mentions: List[int] = None, 
                             reply_to_message_id: int = None, processing_time: float = None):
        """Добавление записи в историю чата"""
        async with aiosqlite.connect(self.db_path) as conn:
            mentions_json = json.dumps(mentions or [])
            await conn.execute('''
            INSERT INTO chat_history 
            (chat_id, user_id, message_id, message_text, bot_response, character_used, 
             is_whomever_call, context_summary, mentions, reply_to_message_id, processing_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (chat_id, user_id, message_id, message_text, bot_response, character, 
                  is_whomever_call, context_summary, mentions_json, reply_to_message_id, processing_time))
            
            # Обновляем счетчик сообщений участника
            await conn.execute('''
            UPDATE chat_members 
            SET message_count = message_count + 1, last_seen = CURRENT_TIMESTAMP
            WHERE chat_id = ? AND user_id = ?
            ''', (chat_id, user_id))
            
            # Обновляем время последнего сообщения в чате
            await conn.execute('''
            UPDATE chats SET last_message_at = CURRENT_TIMESTAMP WHERE chat_id = ?
            ''', (chat_id,))
            
            await conn.commit()

    async def get_chat_history(self, chat_id: int, limit: int = 20, user_id: int = None) -> List[Dict]:
        """Получение истории чата"""
        async with aiosqlite.connect(self.db_path) as conn:
            query = '''
            SELECT ch.*, u.username, u.first_name, u.is_founder
            FROM chat_history ch
            LEFT JOIN users u ON ch.user_id = u.user_id
            WHERE ch.chat_id = ?
            '''
            params = [chat_id]
            
            if user_id:
                query += ' AND ch.user_id = ?'
                params.append(user_id)
                
            query += ' ORDER BY ch.timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            
            # Преобразуем в список словарей
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def get_recent_chat_history(self, chat_id: int, limit: int = 10) -> List[Dict]:
        """Получение последних сообщений для контекста ИИ в правильном порядке"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Сначала получаем последние сообщения (DESC), потом сортируем в правильном порядке (ASC)
            query = '''
            SELECT * FROM (
                SELECT ch.message_text, ch.bot_response, ch.timestamp, u.first_name
                FROM chat_history ch
                LEFT JOIN users u ON ch.user_id = u.user_id
                WHERE ch.chat_id = ? AND ch.bot_response != ''
                ORDER BY ch.timestamp DESC
                LIMIT ?
            ) ORDER BY timestamp ASC
            '''
            
            cursor = await conn.execute(query, (chat_id, limit))
            rows = await cursor.fetchall()
            
            # Преобразуем в список словарей
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def get_chat_context(self, chat_id: int, context_type: str = None, limit: int = 50) -> List[Dict]:
        """Получение контекста чата"""
        async with aiosqlite.connect(self.db_path) as conn:
            query = '''
            SELECT * FROM chat_context 
            WHERE chat_id = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            '''
            params = [chat_id]
            
            if context_type:
                query += ' AND context_type = ?'
                params.append(context_type)
                
            query += ' ORDER BY relevance_score DESC, updated_at DESC LIMIT ?'
            params.append(limit)
            
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def update_chat_context(self, chat_id: int, context_type: str, context_key: str, 
                                context_value: str, relevance_score: float = 1.0, 
                                expires_in_hours: int = None):
        """Обновление контекста чата"""
        async with aiosqlite.connect(self.db_path) as conn:
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            
            await conn.execute('''
            INSERT OR REPLACE INTO chat_context 
            (chat_id, context_type, context_key, context_value, relevance_score, 
             updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            ''', (chat_id, context_type, context_key, context_value, relevance_score, expires_at))
            await conn.commit()

    async def get_chat_members(self, chat_id: int) -> List[Dict]:
        """Получение списка участников чата"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute('''
            SELECT cm.*, u.username, u.first_name, u.last_name, u.is_founder
            FROM chat_members cm
            LEFT JOIN users u ON cm.user_id = u.user_id
            WHERE cm.chat_id = ?
            ORDER BY cm.message_count DESC, cm.join_date ASC
            ''', (chat_id,))
            rows = await cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def is_user_founder(self, user_id: int) -> bool:
        """Проверка, является ли пользователь основателем"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute('''
            SELECT is_founder FROM users WHERE user_id = ?
            ''', (user_id,))
            row = await cursor.fetchone()
            return bool(row and row[0]) if row else False

    async def get_user_chat_profile(self, chat_id: int, user_id: int) -> Optional[Dict]:
        """Получение профиля пользователя в контексте чата"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute('''
            SELECT * FROM user_chat_profiles WHERE chat_id = ? AND user_id = ?
            ''', (chat_id, user_id))
            row = await cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                profile = dict(zip(columns, row))
                # Парсим JSON поля
                for field in ['interests', 'communication_patterns', 'personality_traits', 'topic_preferences']:
                    if profile[field]:
                        profile[field] = json.loads(profile[field])
                return profile
            return None

    async def update_user_chat_profile(self, chat_id: int, user_id: int, **profile_data):
        """Обновление профиля пользователя в чате"""
        if not profile_data:
            return
            
        # Конвертируем списки/словари в JSON
        for field in ['interests', 'communication_patterns', 'personality_traits', 'topic_preferences']:
            if field in profile_data and isinstance(profile_data[field], (list, dict)):
                profile_data[field] = json.dumps(profile_data[field], ensure_ascii=False)
        
        fields = []
        values = []
        for key, value in profile_data.items():
            fields.append(f"{key} = ?")
            values.append(value)
            
        fields.append("last_updated = CURRENT_TIMESTAMP")
        
        async with aiosqlite.connect(self.db_path) as conn:
            # Сначала попробуем обновить
            values_with_ids = values + [chat_id, user_id]
            result = await conn.execute(f'''
            UPDATE user_chat_profiles SET {", ".join(fields)} 
            WHERE chat_id = ? AND user_id = ?
            ''', values_with_ids)
            
            # Если записи не было, создаем новую
            if result.rowcount == 0:
                profile_data['chat_id'] = chat_id
                profile_data['user_id'] = user_id
                
                columns = list(profile_data.keys())
                placeholders = ["?" for _ in columns]
                
                await conn.execute(f'''
                INSERT INTO user_chat_profiles ({", ".join(columns)})
                VALUES ({", ".join(placeholders)})
                ''', list(profile_data.values()))
            
            await conn.commit()

    async def cleanup_old_context(self, days_old: int = 30):
        """Очистка старого контекста"""
        async with aiosqlite.connect(self.db_path) as conn:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            await conn.execute('''
            DELETE FROM chat_context 
            WHERE expires_at < CURRENT_TIMESTAMP OR updated_at < ?
            ''', (cutoff_date,))
            await conn.commit()

    async def get_statistics(self, chat_id: int = None) -> Dict:
        """Получение статистики использования"""
        async with aiosqlite.connect(self.db_path) as conn:
            stats = {}
            
            if chat_id:
                # Статистика по конкретному чату
                cursor = await conn.execute('''
                SELECT COUNT(*) as total_messages, 
                       COUNT(DISTINCT user_id) as unique_users,
                       AVG(processing_time) as avg_processing_time
                FROM chat_history WHERE chat_id = ?
                ''', (chat_id,))
                row = await cursor.fetchone()
                stats['chat'] = dict(zip([d[0] for d in cursor.description], row))
            else:
                # Общая статистика
                cursor = await conn.execute('''
                SELECT COUNT(*) as total_messages,
                       COUNT(DISTINCT user_id) as total_users,
                       COUNT(DISTINCT chat_id) as total_chats
        FROM chat_history 
                ''')
                row = await cursor.fetchone()
                stats['global'] = dict(zip([d[0] for d in cursor.description], row))
            
            return stats

    async def close(self):
        """Закрытие всех соединений (заглушка для совместимости)"""
        # aiosqlite автоматически закрывает соединения при выходе из контекста
        pass 