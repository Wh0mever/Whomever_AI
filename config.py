# Конфигурация для Telegram-бота

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# API ключи
DEEPSEEKCHAT_API_KEY = '1111111111111111111111111111111111'
TELEGRAM_BOT_TOKEN = '11111111111111111111'  # Замените на ваш токен
OPENAI_API_KEY = '1111111111111111111111111111'  # Замените на ваш ключ OpenAI
FETCHSERP_API_KEY = '1111111111111111111111111111111111'

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
    'voice_processing': True
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
    }
}

# Языковые настройки
SUPPORTED_LANGUAGES = ['ru', 'en']

# Настройки безопасности
RATE_LIMIT = {
    'messages_per_minute': 60,
    'images_per_day': 50,
    'voice_messages_per_day': 100
}

# Настройки кэширования
CACHE_SETTINGS = {
    'enabled': True,
    'ttl': 3600,  # 1 hour
    'max_size': 1000  # Maximum number of items in cache
}

# Настройки поиска
SEARCH_SETTINGS = {
    'default_engine': 'bing',
    'supported_engines': ['google', 'bing', 'duckduckgo', 'yahoo', 'yandex'],
    'results_per_page': 10,
    'max_pages': 3,
    'default_country': 'ru',
    'cache_duration': 3600  # 1 час
}

# Настройки FetchSERP
FETCHSERP_SETTINGS = {
    'base_url': 'https://www.fetchserp.com/api/v1',
    'endpoints': {
        'search': '/search',
        'ranking': '/ranking',
        'web_pages': '/serp_web_pages',
        'suggestions': '/keywords_suggestions'
    },
    'max_retries': 3,
    'timeout': 30,
    'rate_limit': {
        'requests_per_minute': 60,
        'max_concurrent': 5
    }
}

# Добавьте другие настройки, если необходимо 

DATABASE_NAME = 'bot_database.db'
BOT_TOKEN = 'YOUR_BOT_TOKEN' 