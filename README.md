# 🤖 WHOMEVER AI Bot 2025

> **Передовой Telegram-бот с интеграцией новейших возможностей OpenAI 2025**

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4.1-green.svg)](https://openai.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4.svg)](https://telegram.org)
[![Embeddings](https://img.shields.io/badge/Embeddings-text--embedding--3--large-orange.svg)](https://openai.com)

## 🌟 **Основные возможности**

### 🗣️ **Realtime Voice API (речь-в-речь)**
- Прямое голосовое общение без промежуточного текста
- Натуральные прерывания и эмоциональные интонации  
- WebSocket подключения для низкой задержки
- Поддержка функций прямо в голосовом режиме

### 🧠 **O3/O4-mini Reasoning Models**
- Автономное принятие решений (agentic tool use)
- ИИ сам решает когда и какие инструменты использовать
- Визуальное мышление - анализ изображений в процессе рассуждения
- Многошаговые рассуждения для сложных задач

### 🔍 **Семантический поиск с Embeddings**
- **text-embedding-3-large** для максимальной точности
- Автоматическое определение типа запросов
- Ранжирование по семантической релевантности
- Кэширование embeddings для быстродействия

### 👁️ **Visual Reasoning & GPT-4.1 Vision**
- Анализ изображений с контекстным пониманием
- 1M токенов контекста для длинных диалогов
- Обработка целых книг и документов

## 📁 **Структура проекта**

```
Whomever_AI/
├── 🤖 bot.py                    # Основной модуль бота
├── ⚙️ config.py                 # Конфигурация и настройки
├── 🗄️ database.py               # Управление базой данных
├── 🧠 openai_api.py             # Интеграция с OpenAI API
├── 🔍 search_api.py             # Базовый поиск в интернете
├── 🎯 semantic_search_api.py    # Семантический поиск с embeddings
├── 🎤 realtime_voice.py         # Realtime Voice API
├── 🤔 reasoning_api.py          # O3/O4-mini reasoning models
├── 🔧 bot_extensions_2025.py    # Расширения OpenAI 2025
├── 🚀 run_bot.py                # Скрипт запуска
├── 📦 requirements.txt          # Зависимости Python
├── 📖 README.md                 # Документация
├── 🛠️ SETUP_2025.md            # Руководство по настройке
├── 📊 bot_database.db           # База данных SQLite
├── 📁 uploads/                  # Загруженные файлы
├── 📁 temp/                     # Временные файлы
└── 📁 logs/                     # Логи работы
```

## 🚀 **Быстрый старт**

### 1. **Установка зависимостей**
```bash
pip install -r requirements.txt
```

### 2. **Настройка переменных окружения**
Создайте файл `.env`:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
```

### 3. **Запуск бота**
```bash
python run_bot.py
```

## 🎯 **Новые возможности 2025**

### ⚡ **Команды для времени**
```
/время                    # Мгновенное получение времени
/time                     # То же на английском
сейчас какая время по мск? # Естественный запрос
```

### 🔍 **Семантический поиск**
```
/search курс биткоина     # Поиск с ранжированием
найди последние новости   # Автоматический поиск
```

### 🗣️ **Голосовые команды**
```
/voice                    # Включить голосовые ответы
!ГОЛОС                    # В группах для голосового ответа
/realtime                 # Realtime Voice API
```

### 🤖 **Автономный режим**
```
/autonomous               # ИИ сам выбирает инструменты
/reasoning                # O3/O4-mini рассуждения
```

## 🔧 **Архитектура компонентов**

### **📡 OpenAI Integration**
- **GPT-4.1** с 1M токенов контекста
- **DALL-E 3** для генерации изображений
- **Whisper** для транскрибации аудио
- **TTS-1-HD** для синтеза речи
- **text-embedding-3-large** для семантики

### **🗄️ Database Layer**
- **SQLite** для локального хранения
- **Контекстная память** до 1M токенов
- **История диалогов** с метаданными
- **Профили пользователей** с адаптацией

### **🔍 Search Layer**
```python
┌─ SemanticSearchAPI ────────────────────┐
│  ├─ text-embedding-3-large            │
│  ├─ Cosine similarity ranking         │
│  ├─ Embedding cache                   │
│  └─ Fallback to DuckDuckGo           │
└────────────────────────────────────────┘
```

### **🎤 Voice Layer**  
```python
┌─ RealtimeVoiceManager ─────────────────┐
│  ├─ WebSocket connections             │
│  ├─ Audio streaming                   │
│  ├─ Interruption handling             │
│  └─ Multiple voice personalities      │
└────────────────────────────────────────┘
```

## 🛠️ **Конфигурация**

### **OpenAI Models 2025**
```python
OPENAI_MODELS = {
    'text': 'gpt-4.1-2025-04-14',           # GPT-4.1 с 1M токенов
    'reasoning': 'o3-2025-04-16',           # O3 для сложных задач  
    'reasoning_mini': 'o4-mini-2025-04-16', # O4-mini для быстрых задач
    'realtime': 'gpt-4o-realtime-preview',  # Realtime Voice
    'vision': 'gpt-4.1-2025-04-14'         # GPT-4.1 Vision
}
```

### **Семантический поиск**
```python
SEMANTIC_SEARCH = {
    'model': 'text-embedding-3-large',
    'dimensions': 3072,
    'cache_size': 1000,
    'max_results': 8
}
```

### **Голосовые настройки**
```python
VOICE_SETTINGS = {
    'sample_rate': 24000,
    'voices': ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
    'max_duration': 300,
    'interruption_detection': True
}
```

## 📈 **Мониторинг и логи**

### **Структура логирования**
```
INFO:openai_api:🧠 Семантический поиск активирован
INFO:openai_api:🕐 ЗАПРОС О ВРЕМЕНИ ОБНАРУЖЕН  
INFO:openai_api:🔍 Выполняю умный поиск
INFO:openai_api:✅ Получено системное время для Москвы
INFO:bot:✅ HTML форматирование применено успешно
```

### **Метрики производительности**
- ⚡ **Время ответа:** < 2 сек для текста
- 🔍 **Поиск:** < 5 сек с семантическим ранжированием  
- 🎤 **Голос:** < 1 сек задержка в realtime режиме
- 💾 **Память:** Контекст до 1M токенов

## 🔐 **Безопасность**

### **Rate Limiting**
```python
RATE_LIMITS = {
    'messages_per_minute': 60,
    'images_per_day': 50,
    'voice_messages_per_day': 100,
    'realtime_sessions_per_hour': 10
}
```

### **Группы и права доступа**
- 👑 **Founder** - полный доступ ко всем функциям
- 👥 **Группы** - голосовые команды через `!ГОЛОС`
- 🔒 **Приватные чаты** - все возможности доступны

## 🧪 **Тестирование**

### **Основные сценарии**
```bash
# Тест времени
/время

# Тест поиска  
/search последние новости ИИ

# Тест изображений
[Отправить фото] + "что на картинке?"

# Тест голоса
/voice
```

## 🤝 **Участие в разработке**

### **Основные компоненты для расширения:**
1. **Новые источники поиска** в `semantic_search_api.py`
2. **Дополнительные голосовые команды** в `realtime_voice.py`  
3. **Reasoning шаблоны** в `reasoning_api.py`
4. **Обработчики файлов** в `openai_api.py`

### **Архитектурные принципы:**
- 🔄 **Асинхронность** - все API вызовы через `aiohttp`
- 🛡️ **Отказоустойчивость** - fallback для всех критичных функций
- 📊 **Логирование** - подробные логи для отладки
- ⚡ **Производительность** - кэширование и пулы подключений

## 📞 **Поддержка**

### **Полезные команды**
```
/help     - Справка по командам
/stats    - Статистика использования  
/context  - Управление контекстом
/settings - Настройки бота
```

### **Логи и отладка**
```bash
# Просмотр логов в реальном времени
tail -f logs/bot.log

# Проверка статуса компонентов  
python -c "from bot import TelegramBot; print('OK')"
```

---

## 🎉 **Результат**

**WHOMEVER AI Bot 2025** - это полнофункциональный ИИ-ассистент с передовыми возможностями:

✅ **Семантический поиск** с text-embedding-3-large  
✅ **Realtime Voice API** для живого общения  
✅ **O3/O4-mini reasoning** для сложных задач  
✅ **GPT-4.1 Vision** с 1M токенов контекста  
✅ **Автономное использование инструментов**  
✅ **Мгновенное получение времени**  
✅ **Анализ изображений в реальном времени**  

**Готов к использованию прямо сейчас!** 🚀 