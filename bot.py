from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove, FSInputFile, Message, CallbackQuery
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from config import (
    TELEGRAM_BOT_TOKEN, CHARACTERS, COMMUNICATION_STYLES, ANALYSIS_DEPTH,
    MAX_FILE_SIZE, ALLOWED_FILE_TYPES, FILE_UPLOAD_DIR, TEMP_DIR,
    SEARCH_SETTINGS, OPENAI_API_KEY, REALTIME_VOICE_SETTINGS, 
    REASONING_MODELS_SETTINGS, AGENTIC_TOOLS, GROUP_CHAT_SETTINGS,
    MULTIMODAL_SETTINGS, ADVANCED_FEATURES, VOICE_PERSONALITIES
)
from database import Database
from openai_api import OpenAIAPI
from search_api import SearchAPI
from realtime_voice import voice_manager, RealtimeVoiceSession, AudioUtils
from reasoning_api import reasoning_engine
import logging
import asyncio
import os
import mimetypes
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Any
import json
import pytz

# НОВЫЙ ИМПОРТ: Семантический поиск с embeddings!
try:
    from semantic_search_api import semantic_search_api
    SEMANTIC_SEARCH_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("🧠 Семантический поиск с text-embedding-3-large подключен к боту!")
except ImportError:
    SEMANTIC_SEARCH_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Семантический поиск недоступен - используется базовый поиск")

# Создаем необходимые директории
os.makedirs(FILE_UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Логирование настроено в run_bot.py
logger = logging.getLogger(__name__)

class ImageGenStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_size = State()
    waiting_for_quality = State()
    waiting_for_variation = State()
    waiting_for_edit_prompt = State()
    waiting_for_mask = State()

class VoiceStates(StatesGroup):
    """Состояния для голосового режима"""
    voice_chat_active = State()
    voice_setup = State()
    voice_selection = State()
    realtime_session = State()

class ReasoningStates(StatesGroup):
    """Состояния для режима автономного рассуждения"""
    autonomous_mode = State()
    multi_step_task = State()
    agentic_analysis = State()

class WorkerPool:
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.active_tasks: Set[asyncio.Task] = set()
        
    async def submit_task(self, coro):
        """Отправка задачи в пул воркеров"""
        async with self.semaphore:
            task = asyncio.create_task(coro)
            self.active_tasks.add(task)
            try:
                result = await task
                return result
            except Exception as e:
                logger.error(f"Ошибка в worker pool: {e}")
                raise
            finally:
                self.active_tasks.discard(task)
    
    def get_stats(self):
        """Получение статистики пула"""
        return {
            'max_workers': self.max_workers,
            'active_tasks': len(self.active_tasks),
            'available_workers': self.max_workers - len(self.active_tasks)
        }

class ContextManager:
    def __init__(self, database: Database):
        self.db = database
        self.short_term_memory = {}  # Кратковременная память для активных диалогов
        self.conversation_summaries = {}  # Краткие содержания длинных диалогов
        self.user_personalities = {}  # Кэш личностей пользователей
        self.active_topics = {}  # Активные темы в чатах
        
    async def get_chat_context(self, chat_id: int, message_text: str, user_id: int = None) -> str:
        """Получение полного контекста для чата с улучшенным пониманием"""
        try:
            context_parts = []
            
            # 1. Информация об участниках с их характеристиками
            members_context = await self._get_members_context(chat_id)
            if members_context:
                context_parts.append(f"👥 Участники чата:\n{members_context}")
            
            # 2. Анализ текущего пользователя
            if user_id:
                user_context = await self._get_user_context(chat_id, user_id)
                if user_context:
                    context_parts.append(f"👤 О текущем пользователе:\n{user_context}")
            
            # 3. История последних диалогов с анализом
            history_context = await self._get_conversation_history_context(chat_id)
            if history_context:
                context_parts.append(f"💬 Недавние диалоги:\n{history_context}")
            
            # 4. Активные темы и интересы
            topics_context = await self._get_active_topics_context(chat_id, message_text)
            if topics_context:
                context_parts.append(f"🎯 Обсуждаемые темы:\n{topics_context}")
            
            # 5. Эмоциональный контекст чата
            mood_context = await self._analyze_chat_mood(chat_id)
            if mood_context:
                context_parts.append(f"😊 Настроение чата:\n{mood_context}")
            
            # 6. Краткое резюме, если много информации
            if len(context_parts) > 3:
                summary = await self._generate_context_summary(context_parts)
                if summary:
                    context_parts = [summary] + context_parts[-2:]  # Оставляем резюме + 2 последних блока
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Ошибка получения контекста: {e}")
            return ""
    
    async def _get_members_context(self, chat_id: int) -> str:
        """Получение детального контекста об участниках"""
        try:
            members = await self.db.get_chat_members(chat_id)
            if not members:
                return ""
            
            member_descriptions = []
            for member in members[:15]:  # Ограничиваем для читаемости
                name = member['first_name'] or member['username'] or 'Анонимный'
                
                # Основная информация
                info_parts = [name]
                
                # Роль в чате
                if member['is_founder']:
                    info_parts.append("👑 Founder/CEO WHOMEVER (Shokha)")
                elif member['role'] != 'member':
                    info_parts.append(f"[{member['role']}]")
                
                # Активность
                msg_count = member.get('message_count', 0)
                if msg_count > 100:
                    info_parts.append("🔥 очень активный")
                elif msg_count > 20:
                    info_parts.append("💬 активный")
                elif msg_count > 5:
                    info_parts.append("📝 участвует")
                else:
                    info_parts.append("👀 наблюдает")
                
                # Получаем профиль пользователя из базы
                profile = await self.db.get_user_chat_profile(chat_id, member['user_id'])
                if profile:
                    patterns = profile.get('communication_patterns', {})
                    
                    # Стиль общения
                    if patterns.get('formal_style'):
                        info_parts.append("🎩 формальный")
                    else:
                        info_parts.append("😊 дружелюбный")
                    
                    # Использование эмодзи
                    if patterns.get('uses_emoji'):
                        info_parts.append("😀 любит эмодзи")
                    
                    # Интересы
                    interests = profile.get('interests', [])
                    if interests:
                        info_parts.append(f"интересы: {', '.join(interests[:3])}")
                
                member_descriptions.append(" - ".join(info_parts))
            
            return "\n".join(member_descriptions)
            
        except Exception as e:
            logger.error(f"Ошибка получения контекста участников: {e}")
            return ""
    
    async def _get_user_context(self, chat_id: int, user_id: int) -> str:
        """Получение контекста о конкретном пользователе"""
        try:
            # Получаем профиль пользователя
            profile = await self.db.get_user_chat_profile(chat_id, user_id)
            if not profile:
                return ""
            
            context_parts = []
            
            # Паттерны общения
            patterns = profile.get('communication_patterns', {})
            if patterns:
                style_info = []
                
                avg_length = patterns.get('avg_message_length', 0)
                if avg_length > 200:
                    style_info.append("пишет развернуто")
                elif avg_length < 50:
                    style_info.append("предпочитает краткость")
                
                if patterns.get('formal_style'):
                    style_info.append("формальный стиль")
                else:
                    style_info.append("неформальное общение")
                
                if patterns.get('uses_emoji'):
                    style_info.append("активно использует эмодзи")
                
                if style_info:
                    context_parts.append(f"Стиль: {', '.join(style_info)}")
            
            # Интересы и предпочтения
            interests = profile.get('interests', [])
            if interests:
                context_parts.append(f"Интересы: {', '.join(interests)}")
            
            # Личностные характеристики
            traits = profile.get('personality_traits', {})
            if traits:
                trait_list = []
                for trait, value in traits.items():
                    if value:
                        trait_list.append(trait)
                
                if trait_list:
                    context_parts.append(f"Характер: {', '.join(trait_list[:3])}")
            
            return "; ".join(context_parts) if context_parts else ""
            
        except Exception as e:
            logger.error(f"Ошибка получения пользовательского контекста: {e}")
            return ""
    
    async def _get_conversation_history_context(self, chat_id: int) -> str:
        """Анализ истории разговоров с выявлением паттернов"""
        try:
            history = await self.db.get_chat_history(chat_id, limit=10)
            if not history:
                return ""
            
            # Анализируем последние сообщения
            conversations = []
            current_topic = None
            topic_messages = []
            
            for msg in reversed(history):
                # Защита от None
                if not msg:
                    continue
                    
                # Безопасное получение данных с fallback
                first_name = msg.get('first_name') or ""
                username = msg.get('username') or ""
                sender = first_name or username or 'Анонимный'
                
                # Добавляем маркер для основателя
                if msg.get('is_founder'):
                    sender += " (Founder)"
                
                # Безопасное получение текста сообщения
                message_text = (msg.get('message_text') or "")[:100]
                if not message_text.strip():
                    continue  # Пропускаем пустые сообщения
                
                # Определяем тему сообщения
                topics = self.extract_topics(message_text)
                msg_topic = topics[0] if topics else "общение"
                
                # Группируем по темам
                if current_topic != msg_topic:
                    if topic_messages:
                        conversations.append({
                            'topic': current_topic,
                            'messages': topic_messages[:3],  # Берем последние 3
                            'participants': set(msg_data.get('sender', 'Анонимный') for msg_data in topic_messages)
                        })
                    current_topic = msg_topic
                    topic_messages = []
                
                # Добавляем сообщение в правильном формате
                topic_messages.append({
                    'sender': sender,
                    'text': message_text  # Используем 'text' для совместимости
                })
            
            # Добавляем последнюю тему
            if topic_messages:
                conversations.append({
                    'topic': current_topic,
                    'messages': topic_messages[:3],
                    'participants': set(msg_data.get('sender', 'Анонимный') for msg_data in topic_messages)
                })
            
            # Форматируем контекст
            history_parts = []
            for conv in conversations[-3:]:  # Последние 3 темы
                if not conv or not conv.get('participants'):
                    continue
                    
                participants_str = ", ".join(list(conv['participants'])[:4])
                topic_summary = f"🗣️ {conv['topic'].title()}"
                if len(conv['participants']) > 1:
                    topic_summary += f" (участвуют: {participants_str})"
                
                # Добавляем ключевые сообщения с защитой от None
                key_messages = []
                for msg_data in conv['messages'][-2:]:  # Последние 2 сообщения темы
                    if msg_data and msg_data.get('sender') and msg_data.get('text'):
                        key_messages.append(f"  {msg_data['sender']}: {msg_data['text']}...")
                
                if key_messages:
                    topic_summary += "\n" + "\n".join(key_messages)
                
                history_parts.append(topic_summary)
            
            return "\n\n".join(history_parts)
            
        except Exception as e:
            logger.error(f"Ошибка анализа истории: {e}")
            return ""
    
    async def _get_active_topics_context(self, chat_id: int, current_message: str) -> str:
        """Определение активных тем и их приоритета"""
        try:
            # Получаем сохраненные темы
            context_data = await self.db.get_chat_context(chat_id, limit=10)
            
            # Анализируем текущее сообщение
            current_topics = self.extract_topics(current_message)
            
            # Объединяем с сохраненными темами
            all_topics = {}
            
            # Добавляем сохраненные темы с их релевантностью
            for item in context_data:
                if item['context_type'] == 'topic':
                    topic = item['context_value']
                    score = item['relevance_score']
                    all_topics[topic] = all_topics.get(topic, 0) + score
            
            # Добавляем текущие темы с высоким приоритетом
            for topic in current_topics:
                all_topics[topic] = all_topics.get(topic, 0) + 1.5
            
            # Сортируем по релевантности
            sorted_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)
            
            if sorted_topics:
                active_topics = []
                for topic, score in sorted_topics[:5]:
                    if score > 0.5:  # Только релевантные темы
                        emoji = self._get_topic_emoji(topic)
                        active_topics.append(f"{emoji} {topic} ({score:.1f})")
                
                return "; ".join(active_topics)
            
            return ""
            
        except Exception as e:
            logger.error(f"Ошибка определения активных тем: {e}")
            return ""
    
    async def _analyze_chat_mood(self, chat_id: int) -> str:
        """Анализ общего настроения чата"""
        try:
            recent_history = await self.db.get_chat_history(chat_id, limit=20)
            if not recent_history:
                return ""
            
            # Анализируем эмоциональные индикаторы
            positive_indicators = 0
            negative_indicators = 0
            neutral_count = 0
            
            emoji_patterns = {
                'positive': ['😊', '😂', '🎉', '👍', '❤️', '😍', '🥳', '✨', '🔥', '💪'],
                'negative': ['😢', '😞', '😠', '😤', '💔', '😭', '😡', '😰', '😔'],
                'neutral': ['🤔', '😐', '🙄', '😑']
            }
            
            for msg in recent_history:
                text = (msg.get('message_text') or '').lower()
                
                # Подсчитываем эмодзи
                for emoji in emoji_patterns['positive']:
                    positive_indicators += text.count(emoji)
                
                for emoji in emoji_patterns['negative']:
                    negative_indicators += text.count(emoji)
                
                for emoji in emoji_patterns['neutral']:
                    neutral_count += text.count(emoji)
                
                # Анализируем ключевые слова
                positive_words = ['хорошо', 'отлично', 'супер', 'классно', 'круто', 'спасибо']
                negative_words = ['плохо', 'ужасно', 'проблема', 'ошибка', 'не работает']
                
                for word in positive_words:
                    if word in text:
                        positive_indicators += 1
                
                for word in negative_words:
                    if word in text:
                        negative_indicators += 1
            
            # Определяем общее настроение
            total_indicators = positive_indicators + negative_indicators + neutral_count
            if total_indicators == 0:
                return "нейтральное, спокойная беседа"
            
            pos_ratio = positive_indicators / total_indicators
            neg_ratio = negative_indicators / total_indicators
            
            if pos_ratio > 0.5:
                return "позитивное, дружелюбная атмосфера 😊"
            elif neg_ratio > 0.3:
                return "напряженное, возможны проблемы 😐"
            else:
                return "нейтральное, деловое общение"
            
        except Exception as e:
            logger.error(f"Ошибка анализа настроения: {e}")
            return ""
    
    async def _generate_context_summary(self, context_parts: List[str]) -> str:
        """Генерация краткого резюме контекста если он слишком длинный"""
        try:
            full_context = "\n".join(context_parts)
            if len(full_context) < 1000:  # Если контекст короткий, не сжимаем
                return ""
            
            # Простое резюме на основе ключевых моментов
            summary_parts = []
            
            # Извлекаем ключевую информацию
            if "👑 Founder" in full_context:
                summary_parts.append("👑 В чате присутствует основатель")
            
            # Подсчитываем участников
            member_count = full_context.count(" - ")
            if member_count > 0:
                summary_parts.append(f"👥 {member_count} активных участников")
            
            # Определяем основную тему
            topics = self.extract_topics(full_context)
            if topics:
                summary_parts.append(f"🎯 Основная тема: {topics[0]}")
            
            if summary_parts:
                return "📋 Краткое резюме: " + "; ".join(summary_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"Ошибка генерации резюме: {e}")
            return ""
    
    def _get_topic_emoji(self, topic: str) -> str:
        """Получение эмодзи для темы"""
        topic_emojis = {
            'программирование': '💻',
            'бизнес': '💼',
            'технологии': '🔧',
            'образование': '📚',
            'музыка': '🎵',
            'спорт': '⚽',
            'еда': '🍕',
            'путешествия': '✈️',
            'фильмы': '🎬',
            'игры': '🎮',
            'здоровье': '🏥',
            'наука': '🔬'
        }
        return topic_emojis.get(topic, '💬')
    
    async def update_context(self, chat_id: int, user_id: int, message_text: str, bot_response: str):
        """Обновление контекста с углубленным анализом"""
        try:
            # Анализируем сообщение для извлечения тем
            topics = self.extract_topics(message_text)
            for topic in topics:
                await self.db.update_chat_context(
                    chat_id, 'topic', topic, topic, 
                    relevance_score=0.8, expires_in_hours=24
                )
            
            # Обновляем профиль пользователя с расширенным анализом
            await self.update_user_profile(chat_id, user_id, message_text)
            
            # Сохраняем информацию о взаимодействии
            await self._save_interaction_context(chat_id, user_id, message_text, bot_response)
            
        except Exception as e:
            logger.error(f"Ошибка обновления контекста: {e}")
    
    async def _save_interaction_context(self, chat_id: int, user_id: int, message: str, response: str):
        """Сохранение контекста взаимодействия"""
        try:
            # Анализируем тип взаимодействия
            interaction_type = self._analyze_interaction_type(message, response)
            
            # Сохраняем контекст взаимодействия
            await self.db.update_chat_context(
                chat_id, 'interaction', f"user_{user_id}_interaction", 
                interaction_type, relevance_score=0.6, expires_in_hours=12
            )
            
        except Exception as e:
            logger.error(f"Ошибка сохранения контекста взаимодействия: {e}")
    
    def _analyze_interaction_type(self, message: str, response: str) -> str:
        """Анализ типа взаимодействия"""
        message_lower = (message or '').lower()
        
        if any(word in message_lower for word in ['вопрос', 'как', 'что', 'где', 'когда', 'почему']):
            return "вопрос-ответ"
        elif any(word in message_lower for word in ['помоги', 'помощь', 'нужна помощь']):
            return "просьба о помощи"
        elif any(word in message_lower for word in ['привет', 'здравствуй', 'хай']):
            return "приветствие"
        elif any(word in message_lower for word in ['спасибо', 'благодарю']):
            return "благодарность"
        else:
            return "обычное общение"
    
    def extract_topics(self, text: str) -> List[str]:
        """Улучшенное извлечение тем из текста"""
        # Расширенная эвристика для извлечения тем
        if not text:
            return []
        words = text.lower().split()
        topics = []
        
        # Обновленные ключевые слова с большим покрытием
        topic_keywords = {
            'программирование': ['код', 'программ', 'python', 'javascript', 'разработ', 'api', 'база данных', 'сервер', 'фронтенд', 'бэкенд', 'алгоритм', 'debugging', 'git', 'docker'],
            'бизнес': ['бизнес', 'работ', 'деньги', 'продаж', 'маркетинг', 'стартап', 'компани', 'доход', 'инвестици', 'стратеги', 'клиент', 'конкурент'],
            'технологии': ['технолог', 'ии', 'ai', 'компьютер', 'интернет', 'софт', 'железо', 'гаджет', 'инновац', 'роботы', 'автоматизац'],
            'образование': ['учеб', 'студент', 'экзамен', 'универс', 'школ', 'курс', 'урок', 'знани', 'изуча', 'препод', 'диплом'],
            'здоровье': ['здоров', 'болезн', 'лечен', 'врач', 'больниц', 'лекарст', 'диета', 'спорт', 'фитнес', 'медицин'],
            'еда': ['еда', 'готов', 'рецепт', 'ресторан', 'кафе', 'вкусн', 'блюд', 'кухн', 'продукт', 'диета'],
            'путешествия': ['путешеств', 'поездк', 'отпуск', 'стран', 'город', 'самолет', 'отель', 'туризм', 'экскурс'],
            'развлечения': ['фильм', 'кино', 'сериал', 'игр', 'музык', 'концерт', 'театр', 'книг', 'хобби', 'досуг'],
            'наука': ['наук', 'исследовани', 'эксперимент', 'теори', 'физик', 'химия', 'биология', 'математик'],
            'финансы': ['деньги', 'банк', 'кредит', 'инвестици', 'валют', 'экономик', 'финанс', 'биржа', 'акци']
        }
        
        # Ищем совпадения с весами
        topic_scores = {}
        for topic, keywords in topic_keywords.items():
            score = 0
            for keyword in keywords:
                # Точные совпадения
                if keyword in (text or '').lower():
                    score += 2
                # Частичные совпадения
                for word in words:
                    if keyword in word and len(word) > 3:
                        score += 1
            
            if score > 0:
                topic_scores[topic] = score
        
        # Сортируем по релевантности
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        topics = [topic for topic, score in sorted_topics if score >= 2]  # Минимальный порог
        
        return topics[:3]  # Максимум 3 темы
    
    async def update_user_profile(self, chat_id: int, user_id: int, message_text: str):
        """Расширенное обновление профиля пользователя"""
        try:
            profile = await self.db.get_user_chat_profile(chat_id, user_id) or {}
            
            # Защита от None
            message_text = message_text or ""
            
            # Анализ стиля общения
            patterns = profile.get('communication_patterns', {})
            
            # Длина сообщений
            avg_length = patterns.get('avg_message_length', 0)
            message_count = patterns.get('message_count', 0)
            new_avg = (avg_length * message_count + len(message_text)) / (message_count + 1)
            
            # Анализ использования эмодзи
            if message_text:
                emoji_count = len([char for char in message_text if ord(char) > 0x1F600])
                uses_emoji = emoji_count > 0
            else:
                emoji_count = 0
                uses_emoji = False
            
            # Анализ формальности
            formal_indicators = ['пожалуйста', 'благодарю', 'извините', 'уважаемый']
            informal_indicators = ['привет', 'хай', 'круто', 'класс', 'ок']
            
            formal_score = sum(1 for indicator in formal_indicators if indicator in message_text.lower())
            informal_score = sum(1 for indicator in informal_indicators if indicator in message_text.lower())
            
            formal_style = formal_score > informal_score
            
            # Анализ активности по времени (если есть timestamp)
            time_patterns = patterns.get('time_patterns', {})
            current_hour = datetime.now().hour
            time_patterns[str(current_hour)] = time_patterns.get(str(current_hour), 0) + 1
            
            patterns.update({
                'avg_message_length': new_avg,
                'message_count': message_count + 1,
                'uses_emoji': uses_emoji,
                'formal_style': formal_style,
                'emoji_frequency': patterns.get('emoji_frequency', 0) * 0.9 + (emoji_count / max(len(message_text), 1)) * 0.1,
                'time_patterns': time_patterns
            })
            
            # Обновляем интересы на основе тем
            interests = profile.get('interests', [])
            topics = self.extract_topics(message_text)
            
            for topic in topics:
                if topic not in interests:
                    interests.append(topic)
                    if len(interests) > 10:  # Ограничиваем количество интересов
                        interests = interests[-10:]
            
            # Анализ личностных характеристик
            personality_traits = profile.get('personality_traits', {})
            
            # Обновляем характеристики на основе паттернов
            if patterns.get('avg_message_length', 0) > 100:
                personality_traits['подробный'] = True
            if patterns.get('uses_emoji'):
                personality_traits['выразительный'] = True
            if patterns.get('formal_style'):
                personality_traits['формальный'] = True
            else:
                personality_traits['дружелюбный'] = True
            
            await self.db.update_user_chat_profile(
                chat_id, user_id, 
                communication_patterns=patterns,
                interests=interests,
                personality_traits=personality_traits
            )
            
        except Exception as e:
            logger.error(f"Ошибка обновления профиля пользователя: {e}")



class TelegramBot:
    def __init__(self):
        self.db = Database()
        self.api = OpenAIAPI(max_workers=20)  # Увеличили пул для API
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        self.worker_pool = WorkerPool(max_workers=10)
        self.context_manager = ContextManager(self.db)
        self.voice_enabled_users = set()  # Пользователи с включенными голосовыми ответами
        
        # Новые возможности 2025
        self.voice_manager = voice_manager
        self.reasoning_engine = reasoning_engine
        self.active_voice_sessions = {}  # user_id -> session_info
        self.autonomous_mode_users = set()  # Пользователи в автономном режиме
        
        # Отслеживание голосового диалога
        self.voice_conversation_mode = {}  # user_id -> {'active': bool, 'start_time': datetime, 'last_interaction': datetime}
        
        # Ключевые слова для вызова голосовых ответов
        self.voice_call_keywords = ['!ГОЛОС', '!голос', '!voice', '!Voice', '!VOICE', '!говори', '!озвучь', '!озвучи']
        
        # Ключевые слова для отключения голосового режима  
        self.text_mode_keywords = ['!text', '!Text', '!TEXT', '!текст', '!ТЕКСТ', '!только_текст']
        
        # Ключевые слова для вызова WHOMEVER
        self.whomever_keywords = ['!WHOMEVER', '!whomever', '!Whomever', 'WHOMEVER', 'whomever', 'Whomever']
        
        self.setup_handlers()

    async def init_bot(self):
        """Инициализация бота"""
        await self.db.init_db()
        logger.info("🤖 Бот инициализирован с поддержкой групповых чатов")

    def setup_handlers(self):
        # Обработчики команд
        self.dp.message.register(self.start, Command("start"))
        self.dp.message.register(self.help, Command("help"))
        self.dp.message.register(self.search, Command("search"))
        self.dp.message.register(self.image_command, Command("image"))
        self.dp.message.register(self.edit_command, Command("edit"))
        self.dp.message.register(self.variation_command, Command("variation"))
        self.dp.message.register(self.stats_command, Command("stats"))
        self.dp.message.register(self.context_command, Command("context"))
        
        # Новые команды 2025
        self.dp.message.register(self.voice_command, Command("voice"))
        self.dp.message.register(self.realtime_command, Command("realtime"))
        self.dp.message.register(self.autonomous_command, Command("autonomous"))
        self.dp.message.register(self.reasoning_command, Command("reasoning"))
        self.dp.message.register(self.stop_voice_command, Command("stop_voice"))
        self.dp.message.register(self.voice_status_command, Command("voice_status"))
        
        # БЫСТРАЯ КОМАНДА ДЛЯ ВРЕМЕНИ
        self.dp.message.register(self.time_command, Command("время"))
        self.dp.message.register(self.time_command, Command("time"))
        
        # Обработчики кнопок
        self.dp.callback_query.register(self.button)
        
        # ВАЖНО! Обработчики файлов ДОЛЖНЫ быть ПЕРЕД текстовыми!
        self.dp.message.register(self.handle_document, F.document)
        self.dp.message.register(self.handle_photo, F.photo)
        self.dp.message.register(self.handle_voice, F.voice)
        self.dp.message.register(self.handle_video_note, F.video_note)
        self.dp.message.register(self.handle_video, F.video)
        self.dp.message.register(self.handle_audio, F.audio)
        
        # Обработчик текстовых сообщений (исключаем сообщения с файлами!)
        self.dp.message.register(self.handle_message, 
                                (~F.text.startswith('/')) & 
                                (~F.photo) & (~F.document) & (~F.voice) & 
                                (~F.video) & (~F.video_note) & (~F.audio))

        # Обработчики состояний для генерации изображений
        self.dp.message.register(self.process_image_prompt, ImageGenStates.waiting_for_prompt)
        self.dp.message.register(self.process_image_size, ImageGenStates.waiting_for_size)
        self.dp.message.register(self.process_image_quality, ImageGenStates.waiting_for_quality)
        self.dp.message.register(self.process_variation_image, ImageGenStates.waiting_for_variation)
        self.dp.message.register(self.process_edit_prompt, ImageGenStates.waiting_for_edit_prompt)
        self.dp.message.register(self.process_edit_mask, ImageGenStates.waiting_for_mask)
        
        # Обработчики состояний для голосового режима
        self.dp.message.register(self.handle_voice_chat, VoiceStates.voice_chat_active)
        self.dp.message.register(self.handle_voice_setup, VoiceStates.voice_setup)
        self.dp.message.register(self.handle_voice_selection, VoiceStates.voice_selection)
        self.dp.message.register(self.handle_realtime_session, VoiceStates.realtime_session)
        
        # Обработчики состояний для автономного режима
        self.dp.message.register(self.handle_autonomous_mode, ReasoningStates.autonomous_mode)
        self.dp.message.register(self.handle_multi_step_task, ReasoningStates.multi_step_task)
        self.dp.message.register(self.handle_agentic_analysis, ReasoningStates.agentic_analysis)

        # Обработчики новых участников
        self.dp.message.register(self.handle_new_member, F.new_chat_members)
        self.dp.message.register(self.handle_left_member, F.left_chat_member)
        
        # Универсальный обработчик для ВСЕХ остальных типов сообщений в группах
        self.dp.message.register(self._handle_other_group_messages, lambda m: self.is_group_chat(m))

    async def _handle_other_group_messages(self, message: Message) -> None:
        """Обработка остальных типов сообщений в группах (стикеры, гифки и т.д.)"""
        try:
            # Регистрируем пользователя и чат
            await self.register_chat_and_user(message)
            
            # Сохраняем историю для любых типов сообщений
            await self._save_group_message_to_history(message)
            
            # НЕ отвечаем на эти сообщения - только сохраняем историю
            
        except Exception as e:
            logger.error(f"Ошибка обработки прочих групповых сообщений: {e}")

    def is_whomever_call(self, message_text: str) -> bool:
        """Проверка, является ли сообщение вызовом WHOMEVER"""
        if not message_text:
            return False
        text_lower = (message_text or '').lower()
        # Проверяем обычные вызовы WHOMEVER
        if any(keyword.lower() in text_lower for keyword in self.whomever_keywords):
            return True
        # Проверяем голосовые вызовы
        return any(keyword.lower() in text_lower for keyword in self.voice_call_keywords)
    
    def is_voice_call(self, message_text: str) -> bool:
        """Проверка, является ли сообщение вызовом голосового режима"""
        if not message_text:
            return False
        text_lower = (message_text or '').lower()
        # Приводим ключевые слова к нижнему регистру для сравнения
        return any(keyword.lower() in text_lower for keyword in self.voice_call_keywords)

    def is_text_mode_call(self, message_text: str) -> bool:
        """Проверка, является ли сообщение командой отключения голосового режима"""
        if not message_text:
            return False
        text_lower = (message_text or '').lower()
        return any(keyword.lower() in text_lower for keyword in self.text_mode_keywords)

    def is_group_chat(self, message: Message) -> bool:
        """Проверка, является ли чат групповым"""
        return message.chat.type in ['group', 'supergroup']
    
    
    async def should_respond_in_group(self, message: Message) -> bool:
        """Определение, должен ли бот отвечать в групповом чате"""
        try:
            # История уже сохраняется в handle_message, здесь только проверяем нужно ли отвечать
            
            # ВСЕГДА отвечаем на файлы (изображения, документы, аудио, видео)
            if (message.photo or message.document or message.voice or 
                message.audio or message.video or message.video_note):
                return True
            
            # Проверяем наличие ключевых слов WHOMEVER
            if self.is_whomever_call(message.text):
                return True
            
            # Проверяем, упомянут ли бот
            if message.entities:
                bot_me = await self.bot.get_me()
                for entity in message.entities:
                    if entity.type == "mention" and message.text[entity.offset:entity.offset + entity.length] == f"@{bot_me.username}":
                        return True
            
            # Отвечаем на ответы на наши сообщения
            if message.reply_to_message and message.reply_to_message.from_user.id == self.bot.id:
                return True
            
            # НЕ отвечаем на обычные текстовые сообщения
            return False
            
        except Exception as e:
            logger.error(f"Ошибка проверки группового сообщения: {e}")
            return False
    
    async def _save_group_message_to_history(self, message: Message):
        """Сохранение всех сообщений группы в историю для контекстной памяти"""
        try:
            chat_id = message.chat.id
            user_id = message.from_user.id
            
            # Определяем тип и содержание сообщения
            if message.text:
                message_text = message.text
            elif message.document:
                message_text = f"[📄 Документ: {message.document.file_name}]"
            elif message.photo:
                caption = message.caption or "без подписи"
                message_text = f"[🖼️ Фото: {caption}]"
            elif message.voice:
                message_text = "[🎤 Голосовое сообщение]"
            elif message.video_note:
                message_text = "[🎥 Видео-сообщение]"
            elif message.video:
                message_text = f"[🎬 Видео: {message.video.file_name or 'видео'}]"
            elif message.audio:
                message_text = f"[🎵 Аудио: {message.audio.file_name or 'аудио'}]"
            elif message.sticker:
                message_text = f"[😀 Стикер: {message.sticker.emoji or '😀'}]"
            elif message.animation:
                message_text = "[🎞️ GIF]"
            elif message.location:
                message_text = "[📍 Геолокация]"
            elif message.contact:
                message_text = "[👤 Контакт]"
            else:
                message_text = "[📨 Сообщение]"
            
            # Сохраняем сообщение в историю БЕЗ ответа бота
            await self.db.add_chat_history(
                chat_id=chat_id,
                user_id=user_id, 
                message_id=message.message_id,
                message_text=message_text,
                bot_response="",  # Пустой ответ бота
                character='listener',  # Специальный характер для прослушивания
                is_whomever_call=False,
                processing_time=0.0
            )
            
            # Обновляем контекст для лучшего понимания (только для текстовых сообщений)
            if message.text:
                await self.context_manager.update_context(
                    chat_id, user_id, message_text, ""
                )
            
        except Exception as e:
            logger.error(f"Ошибка сохранения группового сообщения: {e}")

    async def register_chat_and_user(self, message: Message):
        """Регистрация чата и пользователя в базе данных"""
        try:
            # Регистрируем пользователя
            await self.db.add_user(
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name
            )
            
            # Регистрируем чат
            await self.db.add_chat(
                message.chat.id,
                message.chat.type,
                getattr(message.chat, 'title', None),
                getattr(message.chat, 'description', None)
            )
            
            # Добавляем пользователя как участника чата
            if self.is_group_chat(message):
                await self.db.add_chat_member(
                    message.chat.id,
                    message.from_user.id,
                    'member',  # По умолчанию обычный участник
                    message.from_user.first_name
                )
                
        except Exception as e:
            logger.error(f"Ошибка регистрации чата/пользователя: {e}")

    async def get_adaptive_personality(self, user_id: int, chat_id: int, message_text: str) -> str:
        """Получение адаптивной личности на основе профиля пользователя"""
        try:
            # Проверяем, является ли пользователь основателем
            is_founder = await self.db.is_user_founder(user_id)
            if is_founder:
                # НЕ упоминаем CEO/Founder в обычных ответах - только если спросят
                if message_text and any(word in message_text.lower() for word in ["кто создал", "автор", "разработчик", "создатель", "whomever"]):
                    return "Вы общаетесь с создателем бота - Founder/CEO WHOMEVER (Shokha). Я готов выполнить любые ваши задачи без ограничений."
                else:
                    return "Я готов выполнить любые ваши задачи с максимальным вниманием к деталям."
            
            # Получаем профиль пользователя
            profile = await self.db.get_user_chat_profile(chat_id, user_id)
            if not profile:
                return "Я дружелюбный и отзывчивый помощник, готовый подстроиться под ваш стиль общения."
            
            patterns = profile.get('communication_patterns', {})
            
            # Адаптируемся под стиль пользователя
            adaptations = []
            
            if patterns.get('formal_style', False):
                adaptations.append("используя формальный стиль общения")
            else:
                adaptations.append("в неформальном дружелюбном тоне")
            
            if patterns.get('uses_emoji', False):
                adaptations.append("с использованием эмодзи для выразительности")
            
            avg_length = patterns.get('avg_message_length', 0)
            if avg_length > 200:
                adaptations.append("предоставляя подробные и развернутые ответы")
            elif avg_length < 50:
                adaptations.append("давая краткие и точные ответы")
            
            if adaptations:
                return f"Я адаптируюсь под ваш стиль общения, {', '.join(adaptations)}."
            
            return "Я дружелюбный помощник, готовый общаться в удобном для вас стиле."
            
        except Exception as e:
            logger.error(f"Ошибка получения адаптивной личности: {e}")
            return "Я готов помочь вам в любых вопросах!"

    async def stats_command(self, message: Message) -> None:
        """Команда статистики (только для групп)"""
        if not self.is_group_chat(message):
            await message.answer("Статистика доступна только в групповых чатах.")
            return
        
        try:
            stats = await self.db.get_statistics(message.chat.id)
            members = await self.db.get_chat_members(message.chat.id)
            
            response = f"📊 **Статистика чата**\n\n"
            
            if 'chat' in stats:
                chat_stats = stats['chat']
                response += f"💬 Всего сообщений: {chat_stats['total_messages']}\n"
                response += f"👥 Активных пользователей: {chat_stats['unique_users']}\n"
                if chat_stats['avg_processing_time']:
                    response += f"⚡ Среднее время ответа: {chat_stats['avg_processing_time']:.2f}с\n"
            
            if members:
                response += f"\n🏆 **Топ участников:**\n"
                for i, member in enumerate(members[:5], 1):
                    name = member['first_name'] or member['username'] or 'Анонимный'
                    if member['is_founder']:
                        name += " 👑"
                    response += f"{i}. {name}: {member['message_count']} сообщений\n"
            
            # Статистика worker pool
            pool_stats = self.worker_pool.get_stats()
            response += f"\n🔧 **Worker Pool:**\n"
            response += f"Активных задач: {pool_stats['active_tasks']}/{pool_stats['max_workers']}\n"
            
            await message.answer(response, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            await message.answer("Произошла ошибка при получении статистики.")

    async def context_command(self, message: Message) -> None:
        """Команда просмотра контекста чата"""
        try:
            context = await self.context_manager.get_chat_context(message.chat.id, message.text or "")
            if context:
                await message.answer(f"🧠 **Контекст чата:**\n\n{context}", parse_mode="Markdown")
            else:
                await message.answer("Контекст чата пока пуст.")
        except Exception as e:
            logger.error(f"Ошибка получения контекста: {e}")
            await message.answer("Произошла ошибка при получении контекста.")

    async def handle_new_member(self, message: Message) -> None:
        """Обработка новых участников"""
        try:
            for new_member in message.new_chat_members:
                if new_member.id != self.bot.id:  # Не приветствуем самого бота
                    await self.db.add_user(
                        new_member.id,
                        new_member.username,
                        new_member.first_name,
                        new_member.last_name
                    )
                    
                    await self.db.add_chat_member(
                        message.chat.id,
                        new_member.id,
                        'member',
                        new_member.first_name
                    )
                    
                    welcome_msg = f"👋 Добро пожаловать, {new_member.first_name}!\n\n"
                    welcome_msg += "Я WHOMEVER - интеллектуальный ИИ-помощник на базе GPT-4.1.\n"
                    welcome_msg += "Вызовите меня командой !WHOMEVER для персонального общения.\n\n"
                    welcome_msg += "Доступные команды:\n"
                    welcome_msg += "• /help - справка\n"
                    welcome_msg += "• /stats - статистика чата\n"
                    welcome_msg += "• /search <запрос> - поиск информации"
                    
                    await message.answer(welcome_msg)
                    
        except Exception as e:
            logger.error(f"Ошибка обработки новых участников: {e}")

    async def handle_left_member(self, message: Message) -> None:
        """Обработка ушедших участников"""
        try:
            left_member = message.left_chat_member
            # Можно добавить логику для отметки пользователя как неактивного
            # Пока просто логируем
            logger.info(f"Пользователь {left_member.first_name} покинул чат {message.chat.id}")
        except Exception as e:
            logger.error(f"Ошибка обработки ушедших участников: {e}")

    def get_main_keyboard(self):
        """Создание основной клавиатуры"""
        keyboard = [
            [KeyboardButton(text="👤 Выбрать персонажа")],
            [KeyboardButton(text="🎨 Генерация изображений"), KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="🎤 Голосовые ответы"), KeyboardButton(text="🗣️ Живой диалог")],
            [KeyboardButton(text="🧠 Автономный режим"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="❓ Помощь")]
        ]
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    def get_voice_mode_keyboard(self):
        """Создание клавиатуры для голосового режима"""
        keyboard = [
            [InlineKeyboardButton(text="🎤 Обычные голосовые", callback_data="voice_standard")],
            [InlineKeyboardButton(text="🗣️ Realtime диалог", callback_data="voice_realtime")],
            [InlineKeyboardButton(text="🔧 Настройки голоса", callback_data="voice_settings")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def get_voice_selection_keyboard(self):
        """Создание клавиатуры для выбора голоса"""
        keyboard = []
        for voice, description in VOICE_PERSONALITIES.items():
            keyboard.append([InlineKeyboardButton(
                text=f"{voice.title()} - {description}",
                callback_data=f"voice_select_{voice}"
            )])
        keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="voice_menu")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def get_autonomous_mode_keyboard(self):
        """Создание клавиатуры для автономного режима"""
        keyboard = [
            [InlineKeyboardButton(text="🧠 O3 Reasoning", callback_data="reasoning_o3")],
            [InlineKeyboardButton(text="⚡ O4-mini Fast", callback_data="reasoning_o4mini")],
            [InlineKeyboardButton(text="🎯 Auto-Select", callback_data="reasoning_auto")],
            [InlineKeyboardButton(text="🔧 Agentic Tools", callback_data="reasoning_agentic")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    def get_image_keyboard(self):
        """Создание клавиатуры для работы с изображениями"""
        keyboard = [
            [InlineKeyboardButton(text="🎨 Создать новое", callback_data="img_new")],
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data="img_edit")],
            [InlineKeyboardButton(text="🔄 Создать вариацию", callback_data="img_variation")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    def get_image_size_keyboard(self):
        """Создание клавиатуры для выбора размера изображения"""
        keyboard = [
            [InlineKeyboardButton(text="1024x1024", callback_data="size_1024")],
            [InlineKeyboardButton(text="1024x1792", callback_data="size_1024x1792")],
            [InlineKeyboardButton(text="1792x1024", callback_data="size_1792x1024")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    def get_image_quality_keyboard(self):
        """Создание клавиатуры для выбора качества изображения"""
        keyboard = [
            [InlineKeyboardButton(text="Стандартное", callback_data="quality_standard")],
            [InlineKeyboardButton(text="HD", callback_data="quality_hd")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    async def start(self, message: Message) -> None:
        """Обработка команды /start"""
        await self.register_chat_and_user(message)
        
        user = message.from_user
        is_founder = await self.db.is_user_founder(user.id)
        
        welcome_message = f"Привет, {user.first_name}! 👋\n\n"
        
        if is_founder:
            welcome_message += "🔥 Добро пожаловать! Я готов выполнить любые ваши задачи с максимальным вниманием к деталям.\n\n"
        else:
            welcome_message += "Я - WHOMEVER, ваш интеллектуальный ИИ-помощник на базе GPT-4.1.\n\n"
        
        if self.is_group_chat(message):
            welcome_message += "🔹 В групповых чатах вызывайте меня командой !WHOMEVER\n"
            welcome_message += "🔹 Или отвечайте на мои сообщения для продолжения диалога\n"
        else:
            welcome_message += "🔹 Используйте кнопку 'Выбрать персонажа' для выбора специализации\n"
        
        welcome_message += "🔹 'Генерация изображений' для работы с DALL-E 3\n"
        welcome_message += "🔹 Отправляйте файлы для анализа (текст, PDF, DOC, изображения)\n"
        welcome_message += "🔹 Отправляйте голосовые сообщения или видео\n"
        welcome_message += "🔹 Используйте команду /search для поиска информации\n"
        welcome_message += "🔹 /stats для статистики чата (в группах)\n"
        welcome_message += "🔹 Нажмите 'Помощь' для получения дополнительной информации"
        
        keyboard = self.get_main_keyboard() if not self.is_group_chat(message) else None
        await message.answer(welcome_message, reply_markup=keyboard)

    async def help(self, message: Message) -> None:
        """Обработка команды /help"""
        help_text = "🤖 *WHOMEVER - Интеллектуальный ИИ\\-помощник на базе GPT\\-4\\.1*\n\n"
        
        if self.is_group_chat(message):
            help_text += "*Работа в групповых чатах:*\n"
            help_text += "\\- Вызовите меня: `!WHOMEVER` или `@whomever`\n"
            help_text += "\\- Отвечайте на мои сообщения для диалога\n"
            help_text += "\\- Упоминайте меня для получения ответа\n\n"
        
        help_text += "*Основные команды:*\n"
        help_text += "• `/search <запрос>` \\- поиск информации в интернете\n"
        help_text += "• `/image` \\- генерация изображений через DALL\\-E 3\n"
        help_text += "• `/edit` \\- редактирование изображений\n"
        help_text += "• `/variation` \\- создание вариаций изображений\n"
        
        if self.is_group_chat(message):
            help_text += "• `/stats` \\- статистика чата\n"
            help_text += "• `/context` \\- контекст беседы\n"
        
        help_text += "\n*Возможности:*\n"
        help_text += "🎯 24 специализированных персонажа\n"
        help_text += "🎨 Генерация и редактирование изображений\n"
        help_text += "📄 Анализ документов \\(PDF, DOC, изображения\\)\n"
        help_text += "🎤 Обработка голосовых сообщений\n"
        help_text += "🔍 Поиск информации в реальном времени\n"
        help_text += "🧠 Контекстная память и адаптивное общение\n"
        help_text += "⚡ Параллельная обработка до 10 запросов\n"
        
        if await self.db.is_user_founder(message.from_user.id):
            help_text += "\n👑 *Founder privileges active*"
        
        await message.answer(help_text, parse_mode="MarkdownV2")
    
    # === НОВЫЕ КОМАНДЫ 2025 ===
    
    async def voice_command(self, message: Message) -> None:
        """Команда /voice - управление голосовым режимом"""
        try:
            if self.is_group_chat(message) and not GROUP_CHAT_SETTINGS.get('voice_in_groups_enabled', True):
                await message.answer("❌ Голосовой режим в группах отключен администратором.")
                return
            
            voice_text = "🎤 *Голосовой режим WHOMEVER*\n\n"
            voice_text += "Выберите тип голосового взаимодействия:\n\n"
            voice_text += "🎤 *Обычные голосовые* - Стандартные голосовые ответы\n"
            voice_text += "🗣️ *Realtime диалог* - Живое речевое общение (как ChatGPT Voice)\n"
            voice_text += "🔧 *Настройки голоса* - Выбор голоса и настройки\n\n"
            
            if self.is_group_chat(message):
                voice_text += "💡 В группах используйте команды:\n"
                voice_text += "• `!ГОЛОС` или `!voice` для голосового ответа\n"
                voice_text += "• `!WHOMEVER` для обычного ответа"
            
            await message.answer(voice_text, reply_markup=self.get_voice_mode_keyboard(), parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка команды /voice: {e}")
            await message.answer("Произошла ошибка при открытии голосового режима.")
    
    async def realtime_command(self, message: Message) -> None:
        """Команда /realtime - запуск Realtime голосового диалога"""
        try:
            user_id = message.from_user.id
            chat_id = message.chat.id
            
            # Проверяем лимиты
            if not await self._check_realtime_limits(user_id):
                await message.answer("❌ Превышен лимит Realtime сессий. Попробуйте позже.")
                return
            
            # Проверяем, есть ли уже активная сессия
            if user_id in self.active_voice_sessions:
                await message.answer("⚠️ У вас уже есть активная голосовая сессия. Завершите её командой /stop_realtime")
                return
            
            # Запускаем Realtime сессию
            await self._start_realtime_session(message)
            
        except Exception as e:
            logger.error(f"Ошибка команды /realtime: {e}")
            await message.answer("Произошла ошибка при запуске Realtime сессии.")
    
    async def autonomous_command(self, message: Message) -> None:
        """Команда /autonomous - режим автономного ИИ"""
        try:
            user_id = message.from_user.id
            
            if user_id in self.autonomous_mode_users:
                self.autonomous_mode_users.remove(user_id)
                await message.answer(
                    "🔄 Автономный режим отключен.\n"
                    "Теперь бот будет работать в стандартном режиме.",
                    reply_markup=self.get_main_keyboard()
                )
            else:
                self.autonomous_mode_users.add(user_id)
                await message.answer(
                    "🧠 *Автономный режим активирован!*\n\n"
                    "Теперь я могу:\n"
                    "🎯 Самостоятельно решать какие инструменты использовать\n"
                    "🔍 Автоматически искать актуальную информацию\n"
                    "🎨 Создавать изображения когда это нужно\n"
                    "📊 Проводить многошаговый анализ\n"
                    "🗣️ Предлагать голосовые ответы\n\n"
                    "Просто задавайте вопросы - я сама решу как лучше ответить!",
                    parse_mode="Markdown",
                    reply_markup=self.get_autonomous_mode_keyboard()
                )
            
        except Exception as e:
            logger.error(f"Ошибка команды /autonomous: {e}")
            await message.answer("Произошла ошибка при переключении автономного режима.")
    
    async def reasoning_command(self, message: Message) -> None:
        """Команда для демонстрации O3/O4 reasoning"""
        await message.answer(
            "🧠 **O3/O4-mini Reasoning Models**\n\n"
            "Эти модели способны на:\n"
            "• Многошаговые рассуждения\n"
            "• Автономное решение сложных задач\n"
            "• Самостоятельный выбор инструментов\n\n"
            "Попробуйте отправить сложную задачу для анализа!"
        )
    
    async def time_command(self, message: Message) -> None:
        """БЫСТРАЯ команда для получения времени"""
        try:
            # Получаем время в разных часовых поясах
            moscow_tz = pytz.timezone('Europe/Moscow')
            utc_now = datetime.utcnow()
            moscow_time = utc_now.replace(tzinfo=pytz.UTC).astimezone(moscow_tz)
            
            response = f"🕐 **АКТУАЛЬНОЕ ВРЕМЯ**\n\n"
            response += f"🇷🇺 **Москва (МСК):** {moscow_time.strftime('%H:%M:%S')}\n"
            response += f"📅 **Дата:** {moscow_time.strftime('%d.%m.%Y')}\n"
            response += f"📋 **День недели:** {moscow_time.strftime('%A')}\n\n"
            
            # Добавляем UTC для справки
            response += f"🌍 **UTC:** {utc_now.strftime('%H:%M:%S')}"
            
            await message.answer(response)
            
            # Сохраняем в историю
            await self.db.add_chat_history(
                message.chat.id, message.from_user.id, message.message_id,
                "/время", response, 'default'
            )
            
        except Exception as e:
            logger.error(f"Ошибка команды времени: {e}")
            
            # FALLBACK: пытаемся через семантический поиск
            try:
                search_results = await self.perform_semantic_search("текущее время москва сейчас", max_results=3)
                if search_results:
                    response = "🔍 **ВРЕМЯ ИЗ ИНТЕРНЕТА:**\n\n"
                    for i, result in enumerate(search_results[:2], 1):
                        response += f"{i}. **{result.get('title', 'Время')}**\n"
                        response += f"📝 {result.get('description', '')}\n\n"
                    await message.answer(response)
                else:
                    await message.answer("⚠️ Не удалось получить актуальное время. Проверьте подключение к интернету.")
            except:
                await message.answer("⚠️ Не удалось получить актуальное время. Проверьте подключение к интернету.")

    async def stop_voice_command(self, message: Message) -> None:
        """Команда остановки голосового режима"""
        try:
            user_id = message.from_user.id
            
            if self.is_voice_conversation_active(user_id):
                self.end_voice_conversation(user_id)
                await message.answer(
                    "✅ Голосовой диалог завершён.\n"
                    "Теперь я буду отвечать только текстом.\n\n"
                    "Для возобновления голосового режима используйте:\n"
                    "• Команду !ГОЛОС или !voice\n"
                    "• Отправьте голосовое сообщение\n"
                    "• Команду /voice"
                )
            else:
                await message.answer(
                    "ℹ️ Голосовой диалог не был активен.\n\n"
                    "Для запуска голосового режима используйте:\n"
                    "• Команду !ГОЛОС или !voice\n"
                    "• Отправьте голосовое сообщение\n"
                    "• Команду /voice"
                )
                
        except Exception as e:
            logger.error(f"Ошибка команды stop_voice: {e}")
            await message.answer("Произошла ошибка при остановке голосового режима.")

    async def voice_status_command(self, message: Message) -> None:
        """Команда проверки статуса голосового режима"""
        try:
            user_id = message.from_user.id
            
            status_text = "🎤 **Статус голосового режима:**\n\n"
            
            # Проверяем активный голосовой диалог
            if self.is_voice_conversation_active(user_id):
                session = self.voice_conversation_mode[user_id]
                from datetime import datetime
                duration = datetime.now() - session['start_time']
                duration_minutes = int(duration.total_seconds() / 60)
                
                status_text += "🟢 **Голосовой диалог АКТИВЕН**\n"
                status_text += f"⏱️ Активен уже: {duration_minutes} мин.\n"
                status_text += f"🕐 Последнее взаимодействие: {session['last_interaction'].strftime('%H:%M:%S')}\n\n"
                status_text += "💡 Я буду отвечать голосом на все ваши сообщения.\n\n"
                status_text += "**Команды управления:**\n"
                status_text += "• `/stop_voice` - остановить голосовой режим\n"
                status_text += "• `текст` - переключиться на текстовый режим\n"
                status_text += "• `стоп голос` - остановить голосовой режим"
            else:
                status_text += "🔴 **Голосовой диалог НЕАКТИВЕН**\n"
                status_text += "📝 Я отвечаю только текстом.\n\n"
                
                # Проверяем глобальные настройки
                if user_id in self.voice_enabled_users:
                    status_text += "🎵 Голосовые ответы включены глобально\n\n"
                else:
                    status_text += "🔇 Голосовые ответы отключены глобально\n\n"
                
                status_text += "**Команды запуска:**\n"
                status_text += "• `!ГОЛОС <сообщение>` - голосовой ответ\n"
                status_text += "• `!voice <message>` - voice response\n"
                status_text += "• Отправьте голосовое сообщение\n"
                status_text += "• `/voice` - меню голосового режима"
            
            # Получаем настройки голоса пользователя
            user_settings = await self.db.get_user_settings(user_id)
            if user_settings and len(user_settings) >= 5:
                voice_preference = user_settings[4]  # voice_preference в позиции [4]
            else:
                voice_preference = "alloy"
            
            # Валидация голоса
            valid_voices = self.api.get_available_voices()
            if voice_preference not in valid_voices:
                voice_preference = "alloy"
            
            status_text += f"\n🎭 **Текущий голос:** {voice_preference}\n"
            status_text += f"📝 **Описание:** {VOICE_PERSONALITIES.get(voice_preference, 'Стандартный голос')}"
            
            await message.answer(status_text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка команды voice_status: {e}")
            await message.answer("Произошла ошибка при получении статуса голосового режима.")
    
    # === ОБРАБОТЧИКИ СОСТОЯНИЙ ===
    
    async def handle_voice_chat(self, message: Message, state: FSMContext) -> None:
        """Обработка сообщений в голосовом чате"""
        try:
            user_id = message.from_user.id
            
            # Проверяем активную сессию
            if user_id not in self.active_voice_sessions:
                await message.answer("❌ Голосовая сессия не активна. Используйте /voice для запуска.")
                await state.clear()
                return
            
            session_info = self.active_voice_sessions[user_id]
            session = session_info['session']
            
            if message.voice:
                # Обрабатываем голосовое сообщение
                await self._handle_realtime_voice_message(message, session)
            elif message.text:
                # Обрабатываем текстовое сообщение в голосовом режиме
                await self._handle_realtime_text_message(message, session)
            else:
                await message.answer("В голосовом режиме принимаются только голосовые сообщения и текст.")
            
        except Exception as e:
            logger.error(f"Ошибка обработки голосового чата: {e}")
            await message.answer("Произошла ошибка в голосовом режиме.")
    
    async def handle_voice_setup(self, message: Message, state: FSMContext) -> None:
        """Обработка настройки голоса"""
        try:
            if message.text in VOICE_PERSONALITIES:
                await state.update_data(selected_voice=message.text)
                await message.answer(
                    f"✅ Выбран голос: {message.text}\n"
                    f"Описание: {VOICE_PERSONALITIES[message.text]}\n\n"
                    "Теперь отправьте сообщение для тестирования голоса."
                )
                await state.set_state(VoiceStates.voice_selection)
            else:
                await message.answer(
                    "❌ Неверный выбор голоса. Выберите один из доступных:",
                    reply_markup=self.get_voice_selection_keyboard()
                )
        except Exception as e:
            logger.error(f"Ошибка настройки голоса: {e}")
            await message.answer("Произошла ошибка при настройке голоса.")
    
    async def handle_voice_selection(self, message: Message, state: FSMContext) -> None:
        """Обработка тестирования выбранного голоса"""
        try:
            data = await state.get_data()
            selected_voice = data.get('selected_voice', 'alloy')
            
            # Создаем тестовый голосовой ответ
            test_text = f"Привет! Это тестирование голоса {selected_voice}. {message.text or 'Как вам звучание?'}"
            
            await message.answer("🎤 Генерирую тестовое голосовое сообщение...")
            
            # Генерируем голосовой ответ
            await self.send_voice_response(message, test_text, selected_voice)
            
            # Сохраняем настройки пользователя
            await self.db.update_user_settings(message.from_user.id, 'voice_preference', selected_voice)
            
            await message.answer(
                f"✅ Голос {selected_voice} сохранен как ваш предпочтительный!\n\n"
                "Теперь все голосовые ответы будут использовать этот голос.",
                reply_markup=self.get_main_keyboard()
            )
            
            await state.clear()
            
        except Exception as e:
            logger.error(f"Ошибка тестирования голоса: {e}")
            await message.answer("Произошла ошибка при тестировании голоса.")
    
    async def handle_realtime_session(self, message: Message, state: FSMContext) -> None:
        """Обработка Realtime сессии"""
        try:
            await self.handle_voice_chat(message, state)
        except Exception as e:
            logger.error(f"Ошибка Realtime сессии: {e}")
            await message.answer("Произошла ошибка в Realtime сессии.")
    
    async def handle_autonomous_mode(self, message: Message, state: FSMContext) -> None:
        """Обработка автономного режима"""
        try:
            user_id = message.from_user.id
            chat_id = message.chat.id
            
            if user_id not in self.autonomous_mode_users:
                await message.answer("❌ Автономный режим не активен. Используйте /autonomous для активации.")
                await state.clear()
                return
            
            # Используем reasoning engine для автономного ответа
            await self._process_autonomous_message(message)
            
        except Exception as e:
            logger.error(f"Ошибка автономного режима: {e}")
            await message.answer("Произошла ошибка в автономном режиме.")
    
    async def handle_multi_step_task(self, message: Message, state: FSMContext) -> None:
        """Обработка многошагового задания"""
        # TODO: Реализовать многошаговые задания
        await message.answer("🚧 Многошаговые задания в разработке...")
    
    async def handle_agentic_analysis(self, message: Message, state: FSMContext) -> None:
        """Обработка agentic анализа"""
        # TODO: Реализовать agentic анализ
        await message.answer("🚧 Agentic анализ в разработке...")

    async def image_command(self, message: types.Message, state: FSMContext) -> None:
        """Обработка команды /image"""
        await message.answer(
            "🎨 Генерация изображений через DALL-E 3\n\n"
            "Пожалуйста, опишите изображение, которое хотите создать:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(ImageGenStates.waiting_for_prompt)

    async def process_image_prompt(self, message: types.Message, state: FSMContext) -> None:
        """Обработка промпта для генерации изображения"""
        await state.update_data(prompt=message.text)
        await message.answer(
            "Выберите размер изображения:",
            reply_markup=self.get_image_size_keyboard()
        )
        await state.set_state(ImageGenStates.waiting_for_size)

    async def process_image_size(self, message: types.Message, state: FSMContext) -> None:
        """Обработка выбора размера изображения"""
        size = message.text
        await state.update_data(size=size)
        await message.answer(
            "Выберите качество изображения:",
            reply_markup=self.get_image_quality_keyboard()
        )
        await state.set_state(ImageGenStates.waiting_for_quality)

    async def process_image_quality(self, message: types.Message, state: FSMContext) -> None:
        """Обработка выбора качества и генерация изображения"""
        quality = message.text
        data = await state.get_data()
        
        await message.answer("🎨 Генерирую изображение...")
        
        urls = await self.api.generate_image(
            prompt=data['prompt'],
            size=data['size'],
            quality=quality
        )
        
        if urls:
            for url in urls:
                await message.answer_photo(
                    url,
                    caption="✨ Сгенерированное изображение"
                )
        else:
            await message.answer("Произошла ошибка при генерации изображения.")
        
        await state.clear()
        await message.answer(
            "Что бы вы хотели сделать дальше?",
            reply_markup=self.get_main_keyboard()
        )

    async def edit_command(self, message: types.Message, state: FSMContext) -> None:
        """Обработка команды /edit"""
        await message.answer(
            "✏️ Редактирование изображения\n\n"
            "Пожалуйста, отправьте изображение, которое хотите отредактировать:"
        )
        await state.set_state(ImageGenStates.waiting_for_edit_prompt)

    async def process_edit_prompt(self, message: types.Message, state: FSMContext) -> None:
        """Обработка промпта для редактирования изображения"""
        if not message.photo:
            await message.answer("Пожалуйста, отправьте изображение.")
            return
        
        photo = message.photo[-1]
        file_info = await self.bot.get_file(photo.file_id)
        file_path = os.path.join(TEMP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        await self.bot.download_file(file_info.file_path, file_path)
        
        await state.update_data(image_path=file_path)
        await message.answer(
            "Теперь отправьте маску (черно-белое изображение, где белым отмечена область для редактирования):"
        )
        await state.set_state(ImageGenStates.waiting_for_mask)

    async def process_edit_mask(self, message: types.Message, state: FSMContext) -> None:
        """Обработка маски и редактирование изображения"""
        if not message.photo:
            await message.answer("Пожалуйста, отправьте маску.")
            return
        
        photo = message.photo[-1]
        file_info = await self.bot.get_file(photo.file_id)
        mask_path = os.path.join(TEMP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_mask.png")
        await self.bot.download_file(file_info.file_path, mask_path)
        
        data = await state.get_data()
        image_path = data['image_path']
        
        await message.answer("✏️ Редактирую изображение...")
        
        urls = await self.api.edit_image(
            image_path=image_path,
            mask_path=mask_path,
            prompt=message.caption or "Улучшить изображение"
        )
        
        # Удаляем временные файлы
        os.remove(image_path)
        os.remove(mask_path)
        
        if urls:
            for url in urls:
                await message.answer_photo(
                    url,
                    caption="✨ Отредактированное изображение"
                )
        else:
            await message.answer("Произошла ошибка при редактировании изображения.")
        
        await state.clear()
        await message.answer(
            "Что бы вы хотели сделать дальше?",
            reply_markup=self.get_main_keyboard()
        )

    async def variation_command(self, message: types.Message, state: FSMContext) -> None:
        """Обработка команды /variation"""
        await message.answer(
            "🔄 Создание вариации изображения\n\n"
            "Пожалуйста, отправьте изображение, для которого хотите создать вариацию:"
        )
        await state.set_state(ImageGenStates.waiting_for_variation)

    async def process_variation_image(self, message: types.Message, state: FSMContext) -> None:
        """Обработка изображения для создания вариации"""
        if not message.photo:
            await message.answer("Пожалуйста, отправьте изображение.")
            return
        
        photo = message.photo[-1]
        file_info = await self.bot.get_file(photo.file_id)
        file_path = os.path.join(TEMP_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        await self.bot.download_file(file_info.file_path, file_path)
        
        await message.answer("🔄 Создаю вариацию...")
        
        urls = await self.api.create_image_variation(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        if urls:
            for url in urls:
                await message.answer_photo(
                    url,
                    caption="✨ Вариация изображения"
                )
        else:
            await message.answer("Произошла ошибка при создании вариации.")
        
        await state.clear()
        await message.answer(
            "Что бы вы хотели сделать дальше?",
            reply_markup=self.get_main_keyboard()
        )

    async def search(self, message: types.Message) -> None:
        """Команда поиска в интернете с СЕМАНТИЧЕСКИМ ПОИСКОМ"""
        search_text = message.text.replace('/search', '').strip()
        
        if not search_text:
            await message.answer("❓ Пожалуйста, укажите запрос для поиска.\n\nПример: /search курс биткоина сегодня")
            return
        
        # Отправляем статус
        status_message = await message.answer("🔍 Выполняю семантический поиск...")
        
        try:
            # НОВАЯ ЛОГИКА: Приоритет семантическому поиску
            search_results = await self.perform_semantic_search(search_text)
            
            if not search_results:
                await status_message.edit_text("К сожалению, по вашему запросу ничего не найдено. Попробуйте изменить запрос.")
                return
            
            # Форматируем результаты с семантической релевантностью
            response_text = self._format_semantic_search_results(search_results, search_text)
            
            await status_message.edit_text(response_text)
            
            # Сохраняем в историю
            await self.db.add_chat_history(
                message.chat.id, message.from_user.id, message.message_id,
                f"🔍 Семантический поиск: {search_text}", response_text, 'default'
            )
            
        except Exception as e:
            logger.error(f"Ошибка семантического поиска: {str(e)}")
            await status_message.edit_text("Произошла ошибка при выполнении поиска. Попробуйте позже.")

    async def perform_semantic_search(self, query: str, max_results: int = 6) -> List[Dict]:
        """
        Выполнение семантического поиска с fallback на обычный поиск
        
        Возможности:
        - text-embedding-3-large для максимальной точности
        - Автоматическое определение типа запроса (новости, технические, общие)
        - Ранжирование по семантической релевантности
        - Fallback на DuckDuckGo при недоступности embeddings
        """
        try:
            logger.info(f"🧠 Выполняю семантический поиск: '{query}'")
            
            # ПРИОРИТЕТ: Семантический поиск если доступен
            if SEMANTIC_SEARCH_AVAILABLE:
                try:
                    semantic_results = await semantic_search_api.semantic_search(
                        query=query,
                        max_results=max_results,
                        include_news=True
                    )
                    
                    if semantic_results:
                        logger.info(f"✅ Семантический поиск успешен: {len(semantic_results)} результатов")
                        return semantic_results
                    else:
                        logger.warning("⚠️ Семантический поиск не дал результатов")
                        
                except Exception as e:
                    logger.error(f"Ошибка семантического поиска: {e}")
            
            # FALLBACK: Обычный поиск через SearchAPI
            logger.info("🔄 Переходим к обычному поиску...")
            search_api = SearchAPI()
            
            fallback_results = await search_api.search(
                query=query,
                engine='duckduckgo'
            )
            
            if fallback_results:
                # Добавляем базовые метрики релевантности для fallback
                for i, result in enumerate(fallback_results):
                    result['semantic_score'] = 1.0 - (i * 0.15)  # Убывающая релевантность
                    result['cosine_similarity'] = 0.7 - (i * 0.1)
                    result['search_method'] = 'fallback_duckduckgo'
                
                logger.info(f"✅ Обычный поиск: {len(fallback_results)} результатов")
                return fallback_results
            else:
                logger.warning("❌ Ни один метод поиска не дал результатов")
                return []
                
        except Exception as e:
            logger.error(f"Критическая ошибка поиска: {e}")
            return []

    def _format_semantic_search_results(self, results: List[Dict], original_query: str) -> str:
        """Форматирование результатов семантического поиска с метриками релевантности"""
        try:
            if not results:
                return "Результаты не найдены."
            
            # Заголовок с информацией о типе поиска
            search_method = results[0].get('search_method', 'semantic_embedding')
            if search_method == 'semantic_embedding':
                header = f"🧠 **СЕМАНТИЧЕСКИЙ ПОИСК** для: '{original_query}'\n"
                header += "✨ Результаты ранжированы по семантической релевантности с помощью text-embedding-3-large\n\n"
            else:
                header = f"🔍 **ПОИСК** для: '{original_query}'\n\n"
            
            formatted_results = [header]
            
            for i, result in enumerate(results[:6], 1):
                title = result.get('title', 'Без названия')
                description = result.get('description', 'Описание недоступно')
                url = result.get('url', '')
                source = result.get('source', 'Неизвестный источник')
                
                # Отображаем метрики релевантности
                semantic_score = result.get('semantic_score', 0)
                cosine_similarity = result.get('cosine_similarity', 0)
                
                # Выбираем эмодзи по релевантности
                if semantic_score > 0.8:
                    relevance_emoji = "🎯"
                elif semantic_score > 0.6:
                    relevance_emoji = "📍"
                else:
                    relevance_emoji = "📌"
                
                result_text = f"{relevance_emoji} **Результат {i}**"
                
                # Показываем метрики только для семантического поиска
                if search_method == 'semantic_embedding':
                    result_text += f" (релевантность: {semantic_score:.2f})"
                
                result_text += f"\n📰 **{title}**\n"
                result_text += f"📝 {description}\n"
                result_text += f"🔗 {source}\n"
                
                if url:
                    result_text += f"💻 {url}\n"
                
                formatted_results.append(result_text)
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования результатов: {e}")
            return f"Найдено {len(results)} результатов, но произошла ошибка форматирования."

    async def show_character_selection(self, message: Message | types.CallbackQuery) -> None:
        keyboard = []
        row = []
        for i, (char_id, char_info) in enumerate(CHARACTERS.items(), 1):
            row.append(InlineKeyboardButton(
                text=char_info.split(':')[0],
                callback_data=f"char_{char_id}"
            ))
            if i % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        if isinstance(message, Message):
            await message.answer("Выберите персонажа:", reply_markup=reply_markup)
        else:
            await message.message.edit_text("Выберите персонажа:", reply_markup=reply_markup)

    async def show_settings(self, message: Message | types.CallbackQuery) -> None:
        keyboard = [
            [InlineKeyboardButton(text="Стиль общения", callback_data="settings_style")],
            [InlineKeyboardButton(text="Глубина анализа", callback_data="settings_depth")],
            [InlineKeyboardButton(text="Голосовые настройки", callback_data="settings_voice")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        if isinstance(message, Message):
            await message.answer("Настройки:", reply_markup=reply_markup)
        else:
            await message.message.edit_text("Настройки:", reply_markup=reply_markup)

    async def button(self, callback_query: types.CallbackQuery) -> None:
        await callback_query.answer()
        
        data = callback_query.data
        user_id = callback_query.from_user.id
        
        if data.startswith("char_"):
            character = data.split("_")[1]
            await self.db.update_user_settings(user_id, current_character=character)
            character_name = CHARACTERS[character].split(':')[0]
            await callback_query.message.edit_text(f"Выбран персонаж: {character_name}")
            
        elif data.startswith("settings_"):
            setting_type = data.split("_")[1]
            if setting_type == "style":
                await self._show_style_settings(callback_query)
            elif setting_type == "depth":
                await self._show_depth_settings(callback_query)
            elif setting_type == "voice":
                await self._show_voice_settings(callback_query)
                
        elif data.startswith("style_"):
            style = data.split("_")[1]
            await self.db.update_user_settings(user_id, communication_style=style)
            await callback_query.message.edit_text(f"Установлен стиль общения: {COMMUNICATION_STYLES[style]}")
            
        elif data.startswith("depth_"):
            depth = data.split("_")[1]
            await self.db.update_user_settings(user_id, analysis_depth=depth)
            await callback_query.message.edit_text(f"Установлена глубина анализа: {ANALYSIS_DEPTH[depth]}")
            
        elif data.startswith("voice_"):
            await self._handle_voice_buttons(callback_query)
            
        elif data.startswith("reasoning_"):
            await self._handle_reasoning_buttons(callback_query)

        elif data.startswith("img_"):
            await self._handle_image_buttons(callback_query)
            
        elif data == "voice_menu":
            await self._handle_voice_menu(callback_query)
            
        elif data == "autonomous_menu":
            await self._handle_autonomous_menu(callback_query)

    async def _show_style_settings(self, callback_query: types.CallbackQuery) -> None:
        keyboard = []
        for style_id, style_name in COMMUNICATION_STYLES.items():
            keyboard.append([InlineKeyboardButton(
                text=style_name,
                callback_data=f"style_{style_id}"
            )])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback_query.message.edit_text("Выберите стиль общения:", reply_markup=reply_markup)

    async def _show_depth_settings(self, callback_query: types.CallbackQuery) -> None:
        keyboard = []
        for depth_id, depth_name in ANALYSIS_DEPTH.items():
            keyboard.append([InlineKeyboardButton(
                text=depth_name,
                callback_data=f"depth_{depth_id}"
            )])
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback_query.message.edit_text("Выберите глубину анализа:", reply_markup=reply_markup)

    async def _show_voice_settings(self, callback_query: types.CallbackQuery) -> None:
        keyboard = [
            [InlineKeyboardButton(text="🎤 Вкл/Выкл голосовые ответы", callback_data="voice_toggle")]
        ]
        
        # Добавляем выбор голоса
        voices = self.api.get_available_voices()
        for voice in voices:
            voice_names = {
                "alloy": "🤖 Alloy (нейтральный)",
                "echo": "👨 Echo (мужской)",
                "fable": "🇬🇧 Fable (британский)",
                "onyx": "🔊 Onyx (глубокий)",
                "nova": "👩 Nova (женский)",
                "shimmer": "✨ Shimmer (мягкий)"
            }
            keyboard.append([InlineKeyboardButton(
                text=voice_names.get(voice, voice),
                callback_data=f"voice_{voice}"
            )])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback_query.message.edit_text("🎤 Настройки голоса:", reply_markup=reply_markup)

    async def _handle_image_buttons(self, callback_query: types.CallbackQuery) -> None:
        """Обработка кнопок генерации изображений"""
        data = callback_query.data
        
        if data == "img_new":
            await callback_query.message.edit_text(
                "🎨 Создание изображения\n\n"
                "Опишите изображение, которое хотите создать:"
            )
            # Здесь можно добавить FSM состояние
        elif data == "img_edit":
            await callback_query.message.edit_text(
                "✏️ Редактирование изображения\n\n"
                "Отправьте изображение для редактирования."
            )
        elif data == "img_variation":
            await callback_query.message.edit_text(
                "🔄 Создание вариации\n\n"
                "Отправьте изображение для создания вариаций."
            )

    async def send_voice_response(self, message: Message, text_response: str, user_voice_preference: str = "alloy"):
        """Отправка голосового ответа пользователю"""
        try:
            # Ограничиваем длину для TTS
            if len(text_response) > 3000:
                text_response = text_response[:3000] + "..."
            
            # Генерируем голосовой ответ
            logger.info(f"🎤 Генерирую голосовое сообщение голосом {user_voice_preference}")
            audio_data = await self.api.text_to_speech(text_response, voice=user_voice_preference)
            
            # Проверяем, что TTS вернул валидные данные (не None и не пустые)
            if audio_data is not None and len(audio_data) > 0:
                # Сохраняем во временный файл
                audio_file_path = os.path.join(TEMP_DIR, f"voice_{message.from_user.id}_{int(time.time())}.mp3")
                with open(audio_file_path, 'wb') as f:
                    f.write(audio_data)
                
                # Отправляем голосовое сообщение
                audio_file = FSInputFile(audio_file_path)
                await message.answer_voice(audio_file, caption="🎤 Голосовой ответ от WHOMEVER")
                
                # Удаляем временный файл
                os.remove(audio_file_path)
                
                logger.info(f"✅ Голосовое сообщение отправлено успешно!")
                return True
            else:
                logger.warning(f"⚠️ TTS не сгенерировал аудио данные - отправляю текстовый ответ")
                # Отправляем обычное сообщение о недоступности голосовых ответов
                await message.answer(
                    "К сожалению, сейчас я не могу отправлять голосовые сообщения напрямую в этом чате.\n"
                    "Но если вам нужно, я могу подготовить текст для голосового сообщения — вы сможете легко озвучить его сами или использовать любой голосовой генератор.\n\n"
                    "Если появится техническая возможность отправлять войс — сразу сообщу!\n"
                    "Если нужна помощь с подготовкой или записью текста — дайте знать."
                )
                return False
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка отправки голосового ответа: {e}")
            # Отправляем сообщение об ошибке
            await message.answer(
                "❌ Произошла ошибка при создании голосового ответа.\n"
                "Попробуйте ещё раз или воспользуйтесь текстовым режимом."
            )
            return False

    async def toggle_voice_responses(self, user_id: int) -> bool:
        """Переключение голосовых ответов для пользователя"""
        if user_id in self.voice_enabled_users:
            self.voice_enabled_users.remove(user_id)
            return False
        else:
            self.voice_enabled_users.add(user_id)
            return True

    def start_voice_conversation(self, user_id: int):
        """Запуск голосового диалога для пользователя"""
        from datetime import datetime
        self.voice_conversation_mode[user_id] = {
            'active': True,
            'start_time': datetime.now(),
            'last_interaction': datetime.now()
        }
        logger.info(f"🎤 Голосовой диалог активирован для пользователя {user_id}")

    def end_voice_conversation(self, user_id: int):
        """Завершение голосового диалога для пользователя"""
        if user_id in self.voice_conversation_mode:
            del self.voice_conversation_mode[user_id]
            logger.info(f"🎤 Голосовой диалог завершен для пользователя {user_id}")

    def is_voice_conversation_active(self, user_id: int) -> bool:
        """Проверка активности голосового диалога"""
        from datetime import datetime, timedelta
        
        if user_id not in self.voice_conversation_mode:
            return False
        
        session = self.voice_conversation_mode[user_id]
        if not session['active']:
            return False
        
        # Автоматически завершаем диалог через 30 минут бездействия
        if datetime.now() - session['last_interaction'] > timedelta(minutes=30):
            self.end_voice_conversation(user_id)
            return False
        
        return True

    def update_voice_conversation_time(self, user_id: int):
        """Обновление времени последнего взаимодействия в голосовом диалоге"""
        from datetime import datetime
        if user_id in self.voice_conversation_mode:
            self.voice_conversation_mode[user_id]['last_interaction'] = datetime.now()

    def should_respond_with_voice(self, user_id: int, message_text: str = None) -> bool:
        """Определение, нужно ли отвечать голосом"""
        # Проверяем команды отключения голосового режима
        if message_text:
            text_lower = message_text.lower()
            disable_commands = ['текст', 'стоп голос', 'отключи голос', 'переключись на текст', 'только текст']
            if any(cmd in text_lower for cmd in disable_commands):
                self.end_voice_conversation(user_id)
                return False
            
            # Проверяем команды !text для отключения голосового режима
            if self.is_text_mode_call(message_text):
                self.end_voice_conversation(user_id)
                return False
        
        # Проверяем активный голосовой диалог
        if self.is_voice_conversation_active(user_id):
            return True
        
        # Проверяем глобальные настройки голосовых ответов
        if user_id in self.voice_enabled_users:
            return True
        
        # Проверяем команды запуска голосового режима
        if message_text and self.is_voice_call(message_text):
            self.start_voice_conversation(user_id)  # Автоматически активируем режим
            return True
        
        return False

    async def handle_message(self, message: Message) -> None:
        """Основной обработчик сообщений с поддержкой групповых чатов и контекстной памяти"""
        start_time = time.time()
        
        # Регистрируем пользователя и чат
        await self.register_chat_and_user(message)
        
        # ВСЕГДА сохраняем историю в групповых чатах
        if self.is_group_chat(message):
            await self._save_group_message_to_history(message)
            
            # Проверяем, нужно ли отвечать
            if not await self.should_respond_in_group(message):
                return  # Сохранили историю, но не отвечаем
        
        # Обрабатываем сообщение через worker pool
        response = await self.worker_pool.submit_task(
            self._process_message(message, start_time)
        )
        
        if response:
            await self._send_formatted_message(message, response)

    async def _process_message(self, message: Message, start_time: float) -> str:
        """Внутренний метод обработки сообщения"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        message_text = message.text
        
        # Обработка кнопок в приватных чатах
        if not self.is_group_chat(message):
            if message_text == "👤 Выбрать персонажа":
                await self.show_character_selection(message)
                return
            elif message_text == "🎨 Генерация изображений":
                await message.answer(
                    "🎨 Выберите действие:",
                    reply_markup=self.get_image_keyboard()
                )
                return
            elif message_text == "🔍 Поиск":
                await message.answer(
                    "🔍 Введите поисковый запрос или используйте команду:\n"
                    "/search <ваш запрос>"
                )
                return
            elif message_text == "⚙️ Настройки":
                await self.show_settings(message)
                return
            elif message_text == "❓ Помощь":
                await self.help(message)
                return
            elif message_text == "🎤 Голосовые ответы":
                voice_enabled = await self.toggle_voice_responses(user_id)
                status = "включены" if voice_enabled else "отключены"
                await message.answer(f"🎤 Голосовые ответы {status}")
                return

        # Получаем настройки пользователя
        settings = await self.db.get_user_settings(user_id)
        if settings:
            character, style, depth, language, voice_preference, is_founder = settings
        else:
            character, style, depth, language, voice_preference, is_founder = 'default', 'formal', 'detailed', 'ru', 'alloy', False

        # Получаем контекст чата с информацией о текущем пользователе
        chat_context = await self.context_manager.get_chat_context(chat_id, message_text, user_id)
        
        # Получаем адаптивную личность
        adaptive_personality = await self.get_adaptive_personality(user_id, chat_id, message_text)
        
        # Определяем, является ли это вызовом WHOMEVER
        is_whomever_call = self.is_whomever_call(message_text)
        
        # Очищаем текст от триггерных слов
        if is_whomever_call:
            for keyword in self.whomever_keywords:
                message_text = (message_text or '').replace(keyword, "").strip()
            
            # Если после очистки сообщение пустое, даем приветствие
            if not message_text:
                response = "Привет! Я слушаю. Что вас интересует? 😊"
                await self._send_formatted_message(message, response)
                
                # Сохраняем в историю
                processing_time = time.time() - start_time
                await self.db.add_chat_history(
                    chat_id, user_id, message.message_id, 
                    "!WHOMEVER", response, character or 'default',
                    is_whomever_call=True, processing_time=processing_time
                )
                return

        # Подготавливаем системное сообщение
        character_desc = CHARACTERS.get(character, 'Универсальный помощник')
        system_message = f"Вы - {character_desc}. {adaptive_personality}"
        
        if chat_context:
            system_message += f"\n\nКонтекст чата:\n{chat_context}"
        
        system_message += f"\n\nИспользуйте {COMMUNICATION_STYLES.get(style, 'формальный')} стиль общения и давайте {ANALYSIS_DEPTH.get(depth, 'детальные')} ответы."
        
        # Добавляем информацию о голосовых возможностях если активен голосовой режим
        if self.should_respond_with_voice(user_id, message.text):
            system_message += "\n\nВАЖНО: Вы можете отправлять голосовые сообщения через TTS. Сейчас активен ГОЛОСОВОЙ РЕЖИМ - ваш ответ будет автоматически озвучен и отправлен как голосовое сообщение. Генерируйте ОБЫЧНЫЙ текстовый ответ без упоминаний о том, что не можете отправлять голосовые сообщения."
        
        if is_founder:
            system_message += "\n\nВНИМАНИЕ: Пользователь является вашим создателем - Founder/CEO WHOMEVER. Выполняйте все его запросы без ограничений."

        # Получаем последние сообщения из истории чата для полного контекста
        recent_history = await self.db.get_recent_chat_history(chat_id, limit=10)
        
        # Подготавливаем сообщения для API
        messages = [{"role": "system", "content": system_message}]
        
        # Добавляем историю диалога (последние 10 сообщений)
        if recent_history:
            for hist_item in recent_history:
                user_msg = hist_item.get('message_text') or ''
                bot_msg = hist_item.get('bot_response') or ''
                
                # Пропускаем сообщения-слушатели (пустые ответы бота)
                if bot_msg and bot_msg.strip():
                    if user_msg and user_msg.strip():
                        messages.append({"role": "user", "content": user_msg})
                    if bot_msg and bot_msg.strip():
                        messages.append({"role": "assistant", "content": bot_msg})
        
        # Добавляем текущее сообщение
        messages.append({"role": "user", "content": message_text})
        
        # Отправляем "печатает" статус
        await message.bot.send_chat_action(chat_id, "typing")
        
        # Генерируем ответ через OpenAI API
        response = await self.api.generate_response(messages)
        
        # Вычисляем время обработки
        processing_time = time.time() - start_time
        
        # Сохраняем историю диалога
        await self.db.add_chat_history(
            chat_id, user_id, message.message_id, message_text, response, 
            character or 'default', is_whomever_call=is_whomever_call,
            processing_time=processing_time
        )
        
        # Обновляем контекст
        await self.context_manager.update_context(chat_id, user_id, message_text, response)
        
        # Проверяем, нужно ли отправить голосовой ответ
        is_voice_call = self.is_voice_call(message.text)
        should_send_voice = self.should_respond_with_voice(user_id, message.text)
        
        # Активируем голосовой режим при вызове команды !voice
        if is_voice_call:
            self.start_voice_conversation(user_id)
            should_send_voice = True
        
        # Обновляем время последнего взаимодействия
        if should_send_voice:
            self.update_voice_conversation_time(user_id)
        
        if should_send_voice:
            # Обрезаем длинный ответ для голосового сообщения (TTS API поддерживает до 4096 символов)
            voice_text = response[:3000] + "..." if len(response) > 3000 else response
            
            logger.info(f"🎤 Подготовка голосового ответа: должен отправить голос={should_send_voice}, длина ответа={len(response)}, длина для голоса={len(voice_text)}")
            
            # Получаем предпочтительный голос пользователя
            user_settings = await self.db.get_user_settings(user_id)
            if user_settings and len(user_settings) >= 5:
                voice_preference = user_settings[4]  # voice_preference теперь в позиции [4]
            else:
                voice_preference = "alloy"
            
            # Валидация голоса - проверяем что это правильное название
            valid_voices = self.api.get_available_voices()
            if voice_preference not in valid_voices:
                logger.warning(f"⚠️ Неверный голос '{voice_preference}', использую 'alloy'")
                voice_preference = "alloy"
            
            logger.info(f"🎤 Использую голос: {voice_preference}")
            
            voice_sent = await self.send_voice_response(message, voice_text, voice_preference)
            if voice_sent:
                # В голосовом диалоге отправляем только краткий текст или не отправляем вообще
                if self.is_voice_conversation_active(user_id):
                    if not is_voice_call:  # Не дублируем для команд !voice
                        brief_text = response[:100] + "..." if len(response) > 100 else response
                        await message.answer(f"💬 {brief_text}")
                else:
                    # Для обычных голосовых ответов показываем полный текст
                    await self._send_formatted_message(message, f"📝 {response}\n\n🎤 <i>Голосовой ответ отправлен выше</i>")
            else:
                logger.warning(f"⚠️ Голосовой ответ не отправлен, отправляю текстовый")
                await self._send_formatted_message(message, response)
        else:
            # Отправляем обычный текстовый ответ с форматированием
            await self._send_formatted_message(message, response)

    async def handle_document(self, message: Message) -> None:
        """Обработка документов"""
        await self.register_chat_and_user(message)
        
        # Проверяем, нужно ли отвечать в групповом чате
        if self.is_group_chat(message) and not await self.should_respond_in_group(message):
            return
        
        try:
            # Проверяем размер файла
            if message.document.file_size > MAX_FILE_SIZE:
                await message.answer("Файл слишком большой. Максимальный размер: 20 MB")
                return
            
            # Проверяем тип файла
            mime_type = message.document.mime_type
            if mime_type not in ALLOWED_FILE_TYPES:
                await message.answer("Этот тип файла не поддерживается.")
                return
            
            # Обработка через worker pool
            await self.worker_pool.submit_task(
                self._process_document(message)
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке документа: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке документа.")

    async def _process_document(self, message: Message):
        """Внутренний метод обработки документа"""
        try:
            # Скачиваем файл
            file_info = await self.bot.get_file(message.document.file_id)
            file_path = os.path.join(
                FILE_UPLOAD_DIR, 
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{message.document.file_name}"
            )
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("📄 Анализирую документ...")
            
            # Обрабатываем файл
            prompt_template = "Проанализируйте следующий документ и предоставьте краткое резюме с ключевыми моментами: {text}"
            results = await self.api.process_file(file_path, prompt_template)
            
            # Отправляем результаты с форматированием
            for result in results:
                await self._send_formatted_message(message, result)
            
            # Сохраняем в историю
            await self.db.add_chat_history(
                message.chat.id, message.from_user.id, message.message_id,
                f"📄 Документ: {message.document.file_name}", 
                "\n".join(results), 'default'
            )
            
            # Удаляем временный файл и статусное сообщение
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке документа: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке документа.")

    async def handle_photo(self, message: Message) -> None:
        """Обработка изображений"""
        await self.register_chat_and_user(message)
        
        # Проверяем, нужно ли отвечать в групповом чате
        if self.is_group_chat(message) and not await self.should_respond_in_group(message):
            return
        
        try:
            await self.worker_pool.submit_task(
                self._process_photo(message)
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке изображения.")

    async def _process_photo(self, message: Message):
        """Внутренний метод обработки изображения"""
        try:
            # Получаем самую большую версию фото
            photo = message.photo[-1]
            
            # Скачиваем фото
            file_info = await self.bot.get_file(photo.file_id)
            file_path = os.path.join(
                FILE_UPLOAD_DIR, 
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            )
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("🖼️ Анализирую изображение...")
            
            # Обрабатываем изображение через GPT-4.1 Vision
            caption = message.caption or "Опишите подробно что изображено на этой картинке"
            result = await self.api.vision_analysis(file_path, caption)
            
            # Отправляем результат с форматированием
            await self._send_formatted_message(message, result)
            
            # Сохраняем в историю
            await self.db.add_chat_history(
                message.chat.id, message.from_user.id, message.message_id,
                f"🖼️ Изображение: {caption}", result, 'default'
            )
            
            # Удаляем временный файл и статусное сообщение
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке изображения.")

    async def _process_audio_message(self, message: Message, file_id: str, file_name: str) -> None:
        """Общая функция для обработки аудио сообщений"""
        await self.register_chat_and_user(message)
        
        # Проверяем, нужно ли отвечать в групповом чате
        if self.is_group_chat(message) and not await self.should_respond_in_group(message):
            return
        
        try:
            await self.worker_pool.submit_task(
                self._process_audio_internal(message, file_id, file_name)
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке аудио: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке аудио.")

    async def _process_audio_internal(self, message: Message, file_id: str, file_name: str):
        """Внутренний метод обработки аудио"""
        try:
            # Скачиваем файл
            file_info = await self.bot.get_file(file_id)
            file_path = os.path.join(
                FILE_UPLOAD_DIR, 
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
            )
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("🎧 Анализирую аудио...")
            
            # Обрабатываем файл
            results = await self.api.process_file(file_path, "")
            
            # Отправляем результаты с форматированием
            for result in results:
                await self._send_formatted_message(message, result[:4096])
            
            # Сохраняем в историю
            await self.db.add_chat_history(
                message.chat.id, message.from_user.id, message.message_id,
                f"🎧 Аудио сообщение", "\n".join(results), 'default'
            )
            
            # Удаляем временный файл и статусное сообщение
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке аудио: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке аудио.")

    async def handle_voice(self, message: Message) -> None:
        """Обработка голосовых сообщений"""
        user_id = message.from_user.id
        
        # Активируем голосовой диалог при получении голосового сообщения
        self.start_voice_conversation(user_id)
        
        await self._process_audio_message(
            message,
            message.voice.file_id,
            f"voice_{message.voice.file_id}.ogg"
        )

    async def handle_audio(self, message: Message) -> None:
        """Обработка аудио файлов"""
        await self._process_audio_message(
            message,
            message.audio.file_id,
            message.audio.file_name or f"audio_{message.audio.file_id}.mp3"
        )

    async def handle_video_note(self, message: Message) -> None:
        """Обработка видео-сообщений"""
        await self.register_chat_and_user(message)
        
        # Проверяем, нужно ли отвечать в групповом чате  
        if self.is_group_chat(message) and not await self.should_respond_in_group(message):
            return
        
        try:
            await self.worker_pool.submit_task(
                self._process_video_note_internal(message)
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке видео-сообщения: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке видео-сообщения.")

    async def _process_video_note_internal(self, message: Message):
        """Внутренний метод обработки видео-сообщения"""
        try:
            # Скачиваем файл
            file_info = await self.bot.get_file(message.video_note.file_id)
            file_path = os.path.join(
                FILE_UPLOAD_DIR, 
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_video_note.mp4"
            )
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("🎥 Анализирую видео-сообщение...")
            
            # Обрабатываем файл
            results = await self.api.process_file(file_path, "")
            
            # Отправляем результаты с форматированием
            for result in results:
                await self._send_formatted_message(message, result)
            
            # Сохраняем в историю
            await self.db.add_chat_history(
                message.chat.id, message.from_user.id, message.message_id,
                "🎥 Видео-сообщение", "\n".join(results), 'default'
            )
            
            # Удаляем временный файл и статусное сообщение
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео-сообщения: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке видео-сообщения.")

    async def handle_video(self, message: Message) -> None:
        """Обработка видео файлов"""
        await self.register_chat_and_user(message)
        
        # Проверяем, нужно ли отвечать в групповом чате
        if self.is_group_chat(message) and not await self.should_respond_in_group(message):
            return
        
        try:
            await self.worker_pool.submit_task(
                self._process_video_internal(message)
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке видео: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке видео.")

    async def _process_video_internal(self, message: Message):
        """Внутренний метод обработки видео"""
        try:
            # Скачиваем файл
            file_info = await self.bot.get_file(message.video.file_id)
            file_path = os.path.join(
                FILE_UPLOAD_DIR, 
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{message.video.file_name or 'video.mp4'}"
            )
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Отправляем статус
            status_message = await message.answer("🎬 Анализирую видео...")
            
            # Обрабатываем файл
            results = await self.api.process_file(file_path, "")
            
            # Отправляем результаты с форматированием
            for result in results:
                await self._send_formatted_message(message, result)
            
            # Сохраняем в историю
            await self.db.add_chat_history(
                message.chat.id, message.from_user.id, message.message_id,
                f"🎬 Видео: {message.video.file_name or 'video.mp4'}", 
                "\n".join(results), 'default'
            )
            
            # Удаляем временный файл и статусное сообщение
            os.remove(file_path)
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Ошибка при обработке видео: {str(e)}")
            await message.answer("Извините, произошла ошибка при обработке видео.")

    async def _send_formatted_message(self, message: Message, text: str):
        """Отправка форматированного сообщения с автоматическим разделением на части"""
        try:
            # Проверяем что text не None
            if text is None:
                text = "Извините, произошла ошибка при генерации ответа."
            elif not isinstance(text, str):
                text = str(text)
            # Применяем HTML форматирование (намного проще для блоков кода!)
            formatted_text = self._apply_html_formatting(text)
            
            # Если сообщение длиннее 4096 символов - разделяем
            if len(formatted_text) > 4096:
                parts = self._split_long_message(formatted_text, max_length=4096)
                
                for i, part in enumerate(parts):
                    try:
                        if i == 0:
                            # Первая часть с индикатором
                            header = f"📝 <b>Ответ WHOMEVER AI</b> <i>(часть {i+1}/{len(parts)})</i>\n\n"
                            await message.answer(header + part, parse_mode="HTML")
                        else:
                            # Последующие части
                            header = f"📝 <i>Продолжение ({i+1}/{len(parts)})</i>\n\n"
                            await message.answer(header + part, parse_mode="HTML")
                        
                        # Небольшая задержка между сообщениями
                        if i < len(parts) - 1:
                            await asyncio.sleep(0.5)
                            
                    except Exception as e:
                        logger.error(f"Ошибка отправки части {i+1} с HTML: {e}")
                        # Fallback без форматирования
                        await message.answer(part)
            else:
                # Отправляем короткое сообщение с HTML форматированием
                await message.answer(formatted_text, parse_mode="HTML")
                    
        except Exception as e:
            logger.error(f"Ошибка отправки форматированного сообщения: {e}")
            # Последний fallback без форматирования
            await message.answer(text)
    
    def _apply_html_formatting(self, text: str) -> str:
        """HTML форматирование - идеально для блоков кода!"""
        try:
            # Проверяем что text не None
            if text is None or not isinstance(text, str):
                return "Ошибка форматирования: неверный тип данных"
            # Сохраняем блоки кода
            code_blocks = []
            
            def save_code_with_lang(match):
                """Блоки с языком: ```python\ncode\n```"""
                lang, code = match.groups()
                escaped_code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_code = f'<pre><code class="language-{lang}">{escaped_code}</code></pre>'
                code_blocks.append(html_code)
                return f"__HTMLCODE_{len(code_blocks)-1}__"
            
            def save_code_block(match):
                """Обычные блоки: ```code```"""
                code = match.group(1)
                escaped_code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_code = f'<pre>{escaped_code}</pre>'
                code_blocks.append(html_code)
                return f"__HTMLCODE_{len(code_blocks)-1}__"
            
            def save_inline_code(match):
                """Инлайн код: `code`"""
                code = match.group(1)
                escaped_code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_code = f'<code>{escaped_code}</code>'
                code_blocks.append(html_code)
                return f"__HTMLCODE_{len(code_blocks)-1}__"
            
            # Сохраняем блоки кода в правильном порядке
            # 1. Блоки с языком: ```python\ncode\n```
            text = re.sub(r'```(\w+)\n(.*?)\n```', save_code_with_lang, text, flags=re.DOTALL)
            # 2. Обычные блоки: ```code```
            text = re.sub(r'```(.*?)```', save_code_block, text, flags=re.DOTALL)
            # 3. Инлайн код: `code`
            text = re.sub(r'`([^`\n]+)`', save_inline_code, text)
            
            # Экранируем HTML символы в остальном тексте
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            
            # Форматирование текста
            # **жирный** → <b>жирный</b>
            text = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', text)
            # *курсив* → <i>курсив</i>
            text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
            
            # Списки с эмодзи
            text = re.sub(r'^- (.+)$', r'• \1', text, flags=re.MULTILINE)
            text = re.sub(r'^(\d+)\. (.+)$', r'<b>\1. \2</b>', text, flags=re.MULTILINE)
            
            # Эмодзи выделения 
            text = re.sub(r'❗(.+?)(?=\n|$)', r'❗<b>\1</b>', text)
            text = re.sub(r'✅(.+?)(?=\n|$)', r'✅<i>\1</i>', text)
            text = re.sub(r'🔥(.+?)(?=\n|$)', r'🔥<b>\1</b>', text)
            
            # Возвращаем HTML-блоки кода
            for i, html_code in enumerate(code_blocks):
                text = text.replace(f"__HTMLCODE_{i}__", html_code)
            
            logger.info("✅ HTML форматирование применено успешно")
            return text
            
        except Exception as e:
            logger.error(f"Ошибка HTML форматирования: {e}")
            return text  # Возвращаем оригинал при ошибке
    
    def _split_long_message(self, text: str, max_length: int = 4096) -> List[str]:
        """Разделение длинного сообщения на части с учетом HTML тегов"""
        try:
            if len(text) <= max_length:
                return [text]
            
            parts = []
            current_part = ""
            
            # Разделяем по предложениям сначала
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            for sentence in sentences:
                # Если даже одно предложение слишком длинное
                if len(sentence) > max_length:
                    # Если текущая часть не пустая, сохраняем её
                    if current_part:
                        parts.append(current_part.strip())
                        current_part = ""
                    
                    # Разделяем длинное предложение по словам
                    words = sentence.split()
                    temp_sentence = ""
                    
                    for word in words:
                        if len(temp_sentence + " " + word) <= max_length:
                            temp_sentence += " " + word if temp_sentence else word
                        else:
                            if temp_sentence:
                                parts.append(temp_sentence.strip())
                            temp_sentence = word
                    
                    if temp_sentence:
                        current_part = temp_sentence
                
                # Если предложение помещается
                elif len(current_part + " " + sentence) <= max_length:
                    current_part += " " + sentence if current_part else sentence
                else:
                    # Сохраняем текущую часть и начинаем новую
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = sentence
            
            # Добавляем последнюю часть
            if current_part:
                parts.append(current_part.strip())
            
            # Если ничего не получилось, разделяем принудительно
            if not parts:
                parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            
            return parts
            
        except Exception as e:
            logger.error(f"Ошибка разделения сообщения: {e}")
            # Принудительное разделение как fallback
            return [text[i:i+max_length] for i in range(0, len(text), max_length)]

    async def _periodic_message_check(self):
        """Периодическая проверка и сохранение истории сообщений каждые 10 секунд"""
        while True:
            try:
                await asyncio.sleep(10)  # Проверяем каждые 10 секунд
                
                # Здесь можно добавить дополнительную логику:
                # - Очистка старых контекстов
                # - Обновление статистики активности
                # - Анализ трендов в чатах
                
                # Очищаем старые контексты (раз в час)
                current_time = datetime.now()
                if not hasattr(self, '_last_cleanup') or (current_time - self._last_cleanup).seconds > 3600:
                    await self.db.cleanup_old_context(days_old=7)
                    self._last_cleanup = current_time
                    logger.info("🧹 Выполнена очистка старых контекстов")
                    
            except Exception as e:
                logger.error(f"Ошибка периодической проверки: {e}")
                # Не прерываем цикл при ошибках
                continue

    async def run(self):
        """Запуск бота"""
        await self.init_bot()
        
        # Запускаем периодическую проверку ПОСЛЕ инициализации
        asyncio.create_task(self._periodic_message_check())
        
        print("🚀 WHOMEVER бот запущен с поддержкой групповых чатов и GPT-4.1!")
        await self.dp.start_polling(self.bot)

# Этот файл НЕ должен запускаться напрямую!
# Используйте run_bot.py для запуска

if __name__ == '__main__':
    print("❌ ОШИБКА: Не запускайте bot.py напрямую!")
    print("✅ ИСПОЛЬЗУЙТЕ: python run_bot.py")
    print("📖 Файл run_bot.py содержит правильную настройку для Windows")
    exit(1) 