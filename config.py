# Конфигурация для Telegram-бота

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# API ключи (перенесены в переменные окружения для безопасности)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'your_telegram_bot_token_here')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your_openai_api_key_here')

# Настройки бота
DEFAULT_LANGUAGE = 'ru'
MAX_REQUESTS_PER_MINUTE = 20
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_FILE_TYPES = {
    'text/plain',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/png',
    'audio/ogg',
    'audio/mpeg',
    'audio/wav',
    'video/mp4'
}

# OpenAI Models Configuration 2025
OPENAI_MODELS = {
    'text': 'gpt-4.1-2025-04-14',  # GPT-4.1 с 1M токенов
    'reasoning': 'o3-2025-04-16',  # O3 для сложных задач
    'reasoning_mini': 'o4-mini-2025-04-16',  # O4-mini для быстрых задач
    'realtime': 'gpt-4o-realtime-preview-2024-12-17',  # Realtime Voice
    'vision': 'gpt-4.1-2025-04-14'  # GPT-4.1 Vision
}

# Realtime Voice API Settings
REALTIME_VOICE_SETTINGS = {
    'enabled': True,
    'max_concurrent_sessions': 50,
    'sample_rate': 24000,
    'audio_format': 'pcm16',
    'default_voice': 'alloy',
    'available_voices': ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
    'session_timeout_minutes': 30,
    'max_audio_duration_seconds': 300,  # 5 минут макс на одно аудио
    'interrupt_detection': True,
    'vad_threshold': 0.5,
    'silence_duration_ms': 200
}

# O3/O4 Reasoning Models Settings
REASONING_MODELS_SETTINGS = {
    'o3_enabled': True,
    'o4_mini_enabled': True,
    'auto_model_selection': True,  # Автоматический выбор модели по сложности задачи
    'agentic_tools_enabled': True,  # Автономное использование инструментов
    'visual_reasoning_enabled': True,  # Визуальное мышление
    'max_reasoning_steps': 10,
    'reasoning_timeout_seconds': 60
}

# Agentic Tools Configuration
AGENTIC_TOOLS = {
    'auto_search_enabled': True,
    'auto_image_generation': True,
    'auto_image_analysis': True,
    'auto_document_analysis': True,
    'auto_voice_response': True,
    'function_calling_voice': True,  # Вызов функций голосом
    'autonomous_task_execution': True  # Автономное выполнение многошаговых задач
}

# Персонажи бота
CHARACTERS = {
    'default': 'Обычный режим: Я буду отвечать как обычный помощник',
    'doctor': 'Врач-терапевт: Опытный медицинский специалист',
    'lawyer': 'Юрист: Эксперт в области права',
    'psychologist': 'Психолог: Специалист по душевному здоровью',
    'dentist': 'Стоматолог: Специалист по лечению зубов',
    'trainer': 'Фитнес-тренер: Эксперт по физической подготовке',
    'programmer': 'Программист: Я специализируюсь на разработке программного обеспечения',
    'teacher': 'Учитель: Я объясню сложные темы простым языком',
    'business': 'Бизнес-консультант: Эксперт по развитию бизнеса',
    'architect': 'Архитектор: Специалист по проектированию',
    'historian': 'Историк: Эксперт по историческим событиям',
    'political': 'Политолог: Аналитик политических процессов',
    'engineer': 'Инженер: Технический специалист',
    'auto': 'Автоэксперт: Специалист по автомобилям',
    'electrician': 'Электрик: Специалист по электрике',
    'biologist': 'Биолог: Эксперт в области биологии',
    'gamedev': 'Гейм-дизайнер: Разработчик игр',
    'marketer': 'Маркетолог: Специалист по продвижению',
    'artist': 'Художник: Я помогу с визуальным искусством и дизайном',
    'cook': 'Кулинар: Специалист по приготовлению пищи',
    'financial': 'Финансовый аналитик: Эксперт по финансам',
    'writer': 'Писатель: Я помогу вам с написанием и редактированием текстов',
    'analyst': 'Аналитик: Я помогу с анализом данных и построением отчетов',
    'scientist': 'Ученый: Я объясню научные концепции и исследования'
}

# Voice Personalities for Realtime API
VOICE_PERSONALITIES = {
    'alloy': 'Нейтральный, профессиональный голос',
    'echo': 'Дружелюбный, теплый голос',
    'fable': 'Спокойный, мудрый голос',
    'onyx': 'Глубокий, уверенный голос',
    'nova': 'Энергичный, молодежный голос',
    'shimmer': 'Мягкий, приятный голос'
}

# Настройки стилей общения
COMMUNICATION_STYLES = {
    'formal': 'Формальный',
    'informal': 'Неформальный стиль общения',
    'friendly': 'Дружелюбный',
    'professional': 'Профессиональный',
    'simple': 'Простой',
    'detailed': 'Детальный'
}

# Настройки глубины анализа
ANALYSIS_DEPTH = {
    'brief': 'Краткий',
    'standard': 'Стандартный',
    'detailed': 'Детальный',
    'expert': 'Экспертный'
}

# Настройки для работы с файлами
FILE_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')

# База данных
DATABASE_NAME = 'bot_database.db'

# Настройки для DALL-E
DALLE_IMAGE_SIZES = {
    '1024x1024': '1024x1024',
    '1024x1792': '1024x1792',
    '1792x1024': '1792x1024'
}

DALLE_QUALITY_OPTIONS = {
    'standard': 'standard',
    'hd': 'hd'
}

# Настройки для плагинов
ENABLED_PLUGINS = {
    'image_generation': True,
    'code_analysis': True,
    'file_processing': True,
    'web_search': True,
    'voice_processing': True,
    'realtime_voice': True,  # Новый плагин
    'agentic_reasoning': True,  # O3/O4 модели
    'visual_reasoning': True,  # Визуальное мышление
    'autonomous_tools': True  # Автономные инструменты
}

PLUGIN_SETTINGS = {
    'image_generation': {
        'max_generations_per_day': 50,
        'default_size': '1024x1024',
        'default_quality': 'standard'
    },
    'code_analysis': {
        'supported_languages': ['python', 'javascript', 'typescript', 'java', 'cpp', 'csharp'],
        'max_file_size': 5 * 1024 * 1024  # 5 MB
    },
    'file_processing': {
        'max_parallel_processes': 5,
        'timeout': 300  # 5 minutes
    },
    'web_search': {
        'max_results': 5,
        'cache_duration': 3600  # 1 hour
    },
    'voice_processing': {
        'max_duration': 300,  # 5 minutes
        'supported_formats': ['ogg', 'mp3', 'wav']
    },
    'realtime_voice': {
        'max_session_duration': 1800,  # 30 minutes
        'max_concurrent_sessions': 50,
        'auto_end_inactive_sessions': True,
        'inactive_timeout_seconds': 300  # 5 minutes
    }
}

# Языковые настройки
SUPPORTED_LANGUAGES = ['ru', 'en']

# Настройки безопасности
RATE_LIMIT = {
    'messages_per_minute': 60,
    'images_per_day': 50,
    'voice_messages_per_day': 100,
    'realtime_sessions_per_hour': 10  # Лимит на Realtime сессии
}

# Настройки кэширования
CACHE_SETTINGS = {
    'enabled': True,
    'ttl': 3600,  # 1 hour
    'max_size': 1000  # Maximum number of items in cache
}

# Настройки поиска (используем бесплатные альтернативы)
SEARCH_SETTINGS = {
    'enabled': True,
    'max_results': 5,
    'timeout': 10,
    'user_agent': 'WHOMEVER AI Bot 2.0',
    'search_engines': [
        'duckduckgo',  # Основной - без API ключей
        'google',      # Резервный через парсинг
    ]
}

# Group Chat Settings with Voice
GROUP_CHAT_SETTINGS = {
    'whomever_call_triggers': ['!WHOMEVER', '!whomever', 'WHOMEVER', '@whomever_bot'],
    'voice_call_triggers': ['!ГОЛОС', '!voice', '!говори'],  # Голосовые вызовы в группах
    'auto_voice_response': False,  # Автоматические голосовые ответы в группах (по умолчанию выкл)
    'voice_in_groups_enabled': True,
    'max_voice_duration_in_groups': 60,  # 1 минута максимум в группах
    'require_explicit_voice_permission': True
}

# Multimodal Conversation Settings
MULTIMODAL_SETTINGS = {
    'enabled': True,
    'simultaneous_text_audio': True,  # Одновременная обработка текста и аудио
    'visual_audio_analysis': True,  # Анализ изображений в голосовом режиме
    'context_aware_responses': True,  # Контекстно-зависимые ответы
    'emotion_detection': True,  # Определение эмоций в голосе
    'adaptive_response_style': True  # Адаптивный стиль ответов
}

# WebRTC Settings (для будущей реализации)
WEBRTC_SETTINGS = {
    'enabled': False,  # Пока отключено
    'stun_servers': [
        'stun:stun.l.google.com:19302',
        'stun:stun1.l.google.com:19302'
    ],
    'ice_connection_timeout': 10000,
    'peer_connection_timeout': 30000
}

# Advanced Features
ADVANCED_FEATURES = {
    'autonomous_agent_mode': True,  # Автономный режим агента
    'multi_step_reasoning': True,  # Многошаговое рассуждение
    'proactive_suggestions': True,  # Проактивные предложения
    'learning_from_interactions': True,  # Обучение на взаимодействиях
    'personality_evolution': True,  # Эволюция личности
    'contextual_memory_expansion': True  # Расширение контекстной памяти
}

# Добавьте другие настройки, если необходимо 

DATABASE_NAME = 'bot_database.db'
BOT_TOKEN = 'YOUR_BOT_TOKEN' 