#!/usr/bin/env python3
"""
WHOMEVER AI Bot - Запуск с новыми возможностями OpenAI 2025
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Добавляем текущую директорию в path
sys.path.append(str(Path(__file__).parent))

from bot import TelegramBot
from database import Database
from openai_api import OpenAIAPI
from search_api import SearchAPI
from realtime_voice import RealtimeVoiceManager
from reasoning_api import AgenticReasoningEngine

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота с новыми возможностями 2025"""
    try:
        logger.info("🚀 Запуск WHOMEVER AI Bot с интеграцией OpenAI 2025...")
        
        # Создаем директории если не существуют
        os.makedirs('logs', exist_ok=True)
        os.makedirs('temp', exist_ok=True)
        os.makedirs('uploads', exist_ok=True)
        
        # Инициализация компонентов
        logger.info("📊 Инициализация базы данных...")
        db = Database()
        await db.init_db()
        
        logger.info("🤖 Инициализация OpenAI API...")
        api = OpenAIAPI()
        
        logger.info("🔍 Инициализация Search API...")
        search_api = SearchAPI()
        
        logger.info("🎤 Инициализация Realtime Voice Manager...")
        from config import OPENAI_API_KEY
        voice_manager = RealtimeVoiceManager(OPENAI_API_KEY)
        
        logger.info("🧠 Инициализация Agentic Reasoning Engine...")
        reasoning_engine = AgenticReasoningEngine(OPENAI_API_KEY)
        
        # Создание основного экземпляра бота
        logger.info("🤖 Создание экземпляра TelegramBot...")
        bot = TelegramBot()
        
        # Интеграция новых компонентов (они уже инициализированы в bot.py)
        # bot.voice_manager и bot.reasoning_engine уже созданы в __init__
        logger.info("🔧 Интеграция новых компонентов...")
        
        # Обновляем voice_manager с корректным API ключом
        bot.voice_manager = voice_manager
        bot.reasoning_engine = reasoning_engine
        
        logger.info("✅ Все компоненты инициализированы успешно!")
        logger.info("🎯 Новые возможности 2025:")
        logger.info("   🗣️ Realtime Voice API (речь-в-речь)")
        logger.info("   🧠 O3/O4-mini Reasoning Models")
        logger.info("   🔧 Agentic Tool Use (автономные инструменты)")
        logger.info("   👁️ Visual Reasoning (визуальное мышление)")
        logger.info("   📚 GPT-4.1 с 1M токенов контекста")
        
        # Запуск бота
        logger.info("🚀 Запуск основного цикла бота...")
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Получен сигнал остановки. Завершение работы...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}")
        raise
    finally:
        logger.info("🔄 Очистка ресурсов...")
        # Здесь можно добавить очистку ресурсов
        logger.info("✅ Бот остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Остановка бота...")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1) 