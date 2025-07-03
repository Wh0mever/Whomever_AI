"""
Дополнительные методы для bot.py - расширения 2025
Этот файл содержит методы, которые нужно добавить в основной TelegramBot класс
"""

import asyncio
import logging
import time
import os
from datetime import datetime
from aiogram.types import Message, FSInputFile
from config import REALTIME_VOICE_SETTINGS, VOICE_PERSONALITIES

logger = logging.getLogger(__name__)

class BotExtensions2025:
    """Класс с дополнительными методами для TelegramBot"""
    
    async def _handle_voice_menu(self, callback_query) -> None:
        """Обработка главного меню голосового режима"""
        try:
            await callback_query.message.edit_text(
                "🎤 *Голосовой режим WHOMEVER*\n\n"
                "Выберите тип голосового взаимодействия:\n\n"
                "🎤 *Обычные голосовые* - Стандартные голосовые ответы\n"
                "🗣️ *Realtime диалог* - Живое речевое общение\n"
                "🔧 *Настройки голоса* - Выбор голоса и настройки",
                reply_markup=self.get_voice_mode_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка голосового меню: {e}")
    
    async def _handle_voice_buttons(self, callback_query) -> None:
        """Обработка кнопок голосового режима"""
        try:
            data = callback_query.data
            user_id = callback_query.from_user.id
            
            if data == "voice_standard":
                voice_enabled = await self.toggle_voice_responses(user_id)
                status = "включены" if voice_enabled else "отключены"
                await callback_query.message.edit_text(f"🎤 Стандартные голосовые ответы {status}")
                
            elif data == "voice_realtime":
                await callback_query.message.edit_text(
                    "🗣️ *Запуск Realtime диалога*\n\n"
                    "Начинаю настройку речевого общения в реальном времени...\n\n"
                    "🎤 Отправляйте голосовые сообщения для живого диалога\n"
                    "💬 Или пишите текст - я отвечу голосом\n"
                    "⏹️ Команда /stop_realtime для завершения",
                    parse_mode="Markdown"
                )
                # Сохраняем статус что пользователь в realtime режиме
                self.active_voice_sessions[user_id] = {
                    'mode': 'realtime',
                    'start_time': datetime.now()
                }
                
            elif data == "voice_settings":
                await callback_query.message.edit_text(
                    "🔧 Выберите голос для WHOMEVER:",
                    reply_markup=self.get_voice_selection_keyboard()
                )
                
            elif data.startswith("voice_select_"):
                voice = data.replace("voice_select_", "")
                await self.db.update_user_settings(user_id, voice_preference=voice)
                await callback_query.message.edit_text(
                    f"✅ Выбран голос: {voice}\n"
                    f"Описание: {VOICE_PERSONALITIES[voice]}\n\n"
                    "Голос сохранен для всех будущих ответов!"
                )
                
            elif data == "voice_toggle":
                voice_enabled = await self.toggle_voice_responses(user_id)
                status = "включены" if voice_enabled else "отключены"
                await callback_query.message.edit_text(f"🎤 Голосовые ответы {status}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки голосовых кнопок: {e}")
    
    async def _handle_autonomous_menu(self, callback_query) -> None:
        """Обработка меню автономного режима"""
        try:
            await callback_query.message.edit_text(
                "🧠 *Автономный ИИ режим*\n\n"
                "Выберите режим работы:\n\n"
                "🧠 *O3 Reasoning* - Максимальная мощность рассуждений\n"
                "⚡ *O4-mini Fast* - Быстрые и точные ответы\n"
                "🎯 *Auto-Select* - Автоматический выбор модели\n"
                "🔧 *Agentic Tools* - Автономное использование инструментов",
                reply_markup=self.get_autonomous_mode_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка автономного меню: {e}")
    
    async def _handle_reasoning_buttons(self, callback_query) -> None:
        """Обработка кнопок режимов рассуждения"""
        try:
            data = callback_query.data
            user_id = callback_query.from_user.id
            
            if data == "reasoning_o3":
                self.autonomous_mode_users.add(user_id)
                await callback_query.message.edit_text(
                    "🧠 *Режим O3 Reasoning активирован!*\n\n"
                    "Теперь я использую самую мощную модель рассуждений O3 для:\n"
                    "• Сложных математических задач\n"
                    "• Глубокого анализа и исследований\n" 
                    "• Многошагового планирования\n"
                    "• Продвинутого программирования\n\n"
                    "Задавайте самые сложные вопросы!",
                    parse_mode="Markdown"
                )
                
            elif data == "reasoning_o4mini":
                self.autonomous_mode_users.add(user_id)
                await callback_query.message.edit_text(
                    "⚡ *Режим O4-mini активирован!*\n\n"
                    "Быстрые и точные ответы с использованием O4-mini:\n"
                    "• Высокая скорость обработки\n"
                    "• Эффективное рассуждение\n"
                    "• Отличная математика и кодирование\n"
                    "• Экономичное использование ресурсов\n\n"
                    "Готов к быстрым диалогам!",
                    parse_mode="Markdown"
                )
                
            elif data == "reasoning_auto":
                self.autonomous_mode_users.add(user_id)
                await callback_query.message.edit_text(
                    "🎯 *Автоматический выбор модели активирован!*\n\n"
                    "Я буду автоматически выбирать лучшую модель:\n"
                    "• O3 для сложных задач\n"
                    "• O4-mini для быстрых ответов\n"
                    "• Анализ сложности запроса\n"
                    "• Оптимальное использование ресурсов\n\n"
                    "Просто задавайте вопросы - я сама решу как лучше ответить!",
                    parse_mode="Markdown"
                )
                
            elif data == "reasoning_agentic":
                self.autonomous_mode_users.add(user_id)
                await callback_query.message.edit_text(
                    "🔧 *Agentic Tools режим активирован!*\n\n"
                    "Максимальная автономность - я могу:\n"
                    "🔍 Самостоятельно искать информацию\n"
                    "🎨 Создавать изображения когда нужно\n"
                    "📊 Анализировать документы\n"
                    "🗣️ Отвечать голосом\n"
                    "🧩 Решать многошаговые задачи\n\n"
                    "Я сама решу какие инструменты использовать для идеального ответа!",
                    parse_mode="Markdown"
                )
                
        except Exception as e:
            logger.error(f"Ошибка обработки кнопок рассуждения: {e}")
    
    async def _check_realtime_limits(self, user_id: int) -> bool:
        """Проверка лимитов для Realtime сессий"""
        try:
            # Проверяем общие лимиты
            if len(self.active_voice_sessions) >= REALTIME_VOICE_SETTINGS.get('max_concurrent_sessions', 50):
                return False
            
            # Проверяем пользовательские лимиты (можно добавить в базу данных)
            return True
        except Exception as e:
            logger.error(f"Ошибка проверки лимитов: {e}")
            return False
    
    async def _start_realtime_session(self, message: Message) -> None:
        """Запуск Realtime голосовой сессии"""
        try:
            user_id = message.from_user.id
            
            # Проверяем лимиты
            if not await self._check_realtime_limits(user_id):
                await message.answer("❌ Превышен лимит Realtime сессий. Попробуйте позже.")
                return
            
            # Регистрируем сессию
            self.active_voice_sessions[user_id] = {
                'mode': 'realtime',
                'start_time': datetime.now(),
                'message_count': 0
            }
            
            await message.answer(
                "🗣️ *Realtime диалог активен!*\n\n"
                "✅ Подключение установлено\n"
                "🎤 Отправляйте голосовые сообщения для живого диалога\n"
                "💬 Или пишите текст - я отвечу голосом\n"
                "⏹️ Команда /stop_realtime для завершения\n\n"
                "Говорите - я слушаю! 👂",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Ошибка запуска Realtime сессии: {e}")
            await message.answer("❌ Не удалось запустить Realtime сессию. Попробуйте позже.")
    
    async def _handle_realtime_voice_message(self, message: Message, session=None) -> None:
        """Обработка голосового сообщения в Realtime режиме"""
        try:
            user_id = message.from_user.id
            
            # Обновляем статистику сессии
            if user_id in self.active_voice_sessions:
                self.active_voice_sessions[user_id]['message_count'] += 1
            
            # Показываем что обрабатываем
            await message.answer("🎤 Слушаю и готовлю голосовой ответ...")
            
            # Транскрибируем голосовое сообщение
            file_info = await self.bot.get_file(message.voice.file_id)
            file_path = os.path.join("temp", f"voice_{user_id}_{int(time.time())}.ogg")
            await self.bot.download_file(file_info.file_path, file_path)
            
            # Получаем текст из голосового сообщения
            transcript = await self.api.transcribe_audio(file_path)
            
            if transcript:
                # Обрабатываем как обычное сообщение но отвечаем голосом
                response = await self._process_message_for_realtime(message, transcript)
                
                if response:
                    # Создаем голосовой ответ
                    user_settings = await self.db.get_user_settings(user_id)
                    if user_settings and len(user_settings) >= 5:
                        voice = user_settings[4]  # voice_preference в позиции [4]
                    else:
                        voice = "alloy"
                    
                    # Валидация голоса
                    valid_voices = self.api.get_available_voices()
                    if voice not in valid_voices:
                        voice = "alloy"
                        
                    await self.send_voice_response(message, response, voice)
                    
                    # Также отправляем текст для контроля
                    await message.answer(f"📝 Текст: {response[:200]}{'...' if len(response) > 200 else ''}")
            
            # Удаляем временный файл
            if os.path.exists(file_path):
                os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Ошибка обработки голосового сообщения Realtime: {e}")
            await message.answer("❌ Ошибка обработки голосового сообщения.")
    
    async def _handle_realtime_text_message(self, message: Message, session=None) -> None:
        """Обработка текстового сообщения в Realtime режиме"""
        try:
            user_id = message.from_user.id
            
            # Обновляем статистику сессии
            if user_id in self.active_voice_sessions:
                self.active_voice_sessions[user_id]['message_count'] += 1
            
            # Показываем что обрабатываем
            processing_msg = await message.answer("🗣️ Готовлю голосовой ответ...")
            
            # Обрабатываем сообщение
            response = await self._process_message_for_realtime(message, message.text)
            
            await processing_msg.delete()
            
            if response:
                # Получаем настройки голоса
                user_settings = await self.db.get_user_settings(user_id)
                if user_settings and len(user_settings) >= 5:
                    voice = user_settings[4]  # voice_preference в позиции [4]
                else:
                    voice = "alloy"
                
                # Валидация голоса
                valid_voices = self.api.get_available_voices()
                if voice not in valid_voices:
                    voice = "alloy"
                
                # Отправляем голосовой ответ
                await self.send_voice_response(message, response, voice)
                
                # Также отправляем краткий текст
                await message.answer(f"💬 {response[:100]}{'...' if len(response) > 100 else ''}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки текстового сообщения Realtime: {e}")
            await message.answer("❌ Ошибка обработки сообщения.")
    
    async def _process_message_for_realtime(self, message: Message, text: str) -> str:
        """Обработка сообщения специально для Realtime режима"""
        try:
            # Используем обычную обработку но адаптируем для голоса
            user_id = message.from_user.id
            chat_id = message.chat.id
            
            # Получаем настройки пользователя
            settings = await self.db.get_user_settings(user_id)
            if settings:
                character, style, depth, language, is_founder = settings
            else:
                character, style, depth, language, is_founder = 'default', 'friendly', 'brief', 'ru', False
            
            # Создаем адаптивную личность для голосового режима
            personality = await self.get_adaptive_personality(user_id, chat_id, text)
            
            # Получаем контекст чата
            context = await self.context_manager.get_chat_context(chat_id, text, user_id)
            
            # Формируем сообщения для API с акцентом на голосовое общение
            messages = [
                {
                    "role": "system",
                    "content": f"""Ты WHOMEVER - дружелюбный голосовой ИИ-помощник.

{personality}

ВАЖНО: Отвечай КРАТКО и ЕСТЕСТВЕННО, как в живом разговоре:
- Используй простые предложения
- Говори эмоционально и выразительно  
- Длина ответа: максимум 2-3 предложения
- Будь дружелюбной и живой
- Используй междометия: "ого", "вау", "хм"
- Адаптируйся под настроение собеседника

{f'Контекст чата: {context}' if context else ''}

Отвечай как настоящий друг в живом разговоре!"""
                },
                {
                    "role": "user", 
                    "content": text
                }
            ]
            
            # Проверяем автономный режим
            if user_id in self.autonomous_mode_users:
                # Используем reasoning engine если включен автономный режим
                try:
                    result = await self.reasoning_engine.autonomous_reasoning(
                        text, {"realtime_mode": True}, user_id, chat_id
                    )
                    response = result.get("response", "")
                    
                    # Адаптируем ответ для голоса
                    if len(response) > 500:
                        response = response[:500] + "... Хотите, расскажу подробнее?"
                    
                    return response
                except Exception as e:
                    logger.error(f"Ошибка autonomous reasoning в realtime: {e}")
                    # Fallback на обычную обработку
            
            # Обычная обработка через OpenAI API
            response = await self.api.generate_response(messages)
            
            # Адаптируем ответ для голоса
            if len(response) > 500:
                response = response[:500] + "... Продолжить?"
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка обработки для Realtime: {e}")
            return "Извините, произошла ошибка. Попробуйте еще раз."
    
    async def _process_autonomous_message(self, message: Message) -> None:
        """Обработка сообщения в автономном режиме через reasoning engine"""
        try:
            user_id = message.from_user.id
            chat_id = message.chat.id
            
            # Проверяем, что пользователь в автономном режиме
            if user_id not in self.autonomous_mode_users:
                await message.answer("❌ Автономный режим не активен. Используйте /autonomous для активации.")
                return
            
            # Показываем индикатор обработки
            processing_message = await message.answer("🧠 Анализирую и готовлю оптимальный ответ...")
            
            # Получаем контекст для автономного режима
            context = await self.context_manager.get_chat_context(chat_id, message.text, user_id)
            
            # Готовим контекст для reasoning engine
            reasoning_context = {
                "user_profile": await self.db.get_user_chat_profile(chat_id, user_id),
                "chat_history": context,
                "current_task": "autonomous_response",
                "group_chat": self.is_group_chat(message)
            }
            
            try:
                # Используем reasoning engine для автономного ответа
                result = await self.reasoning_engine.autonomous_reasoning(
                    message.text, reasoning_context, user_id, chat_id
                )
                
                # Получаем ответ и информацию об использованных инструментах
                response = result.get("response", "Произошла ошибка при обработке.")
                tools_used = result.get("tools_used", [])
                model_used = result.get("model_used", "unknown")
                
                # Удаляем индикатор
                await processing_message.delete()
                
                # Отправляем основной ответ с пометкой автономности
                autonomous_prefix = f"🤖 *Автономный режим* ({model_used})\n\n"
                full_response = autonomous_prefix + response
                
                await self._send_formatted_message(message, full_response)
                
                # Если использовались инструменты, показываем краткую статистику
                if tools_used:
                    tools_info = "🛠️ *Использованные инструменты:*\n"
                    for tool in tools_used:
                        tools_info += f"• {tool['name']}\n"
                    
                    await message.answer(tools_info, parse_mode="Markdown")
                
                # Проверяем, нужен ли голосовой ответ
                if (user_id in self.voice_enabled_users or 
                    self.is_voice_call(message.text) or
                    any(tool['name'] == 'create_voice_response' for tool in tools_used)):
                    
                    # Создаем голосовой ответ
                    user_settings = await self.db.get_user_settings(user_id)
                    if user_settings and len(user_settings) >= 5:
                        voice = user_settings[4]  # voice_preference в позиции [4]
                    else:
                        voice = "alloy"
                    await self.send_voice_response(message, response, voice)
                
                # Сохраняем в историю
                await self.db.add_chat_history(
                    chat_id, user_id, message.message_id,
                    message.text, response, 'autonomous',
                    is_whomever_call=True,
                    processing_time=time.time() - time.time()
                )
                
                # Обновляем контекст
                await self.context_manager.update_context(chat_id, user_id, message.text, response)
                
            except Exception as reasoning_error:
                await processing_message.delete()
                logger.error(f"Ошибка reasoning engine: {reasoning_error}")
                
                # Fallback на обычную обработку
                response = await self._process_message(message, time.time())
                if response:
                    fallback_response = f"🔄 *Fallback режим*\n\n{response}"
                    await self._send_formatted_message(message, fallback_response)
            
        except Exception as e:
            logger.error(f"Ошибка автономной обработки: {e}")
            await message.answer("❌ Произошла ошибка в автономном режиме.")


# Функция для объединения методов с основным классом
def extend_telegram_bot(bot_instance):
    """Добавляет новые методы к существующему экземпляру TelegramBot"""
    extensions = BotExtensions2025()
    
    # Копируем все методы из BotExtensions2025 в bot_instance
    for method_name in dir(extensions):
        if not method_name.startswith('_') and callable(getattr(extensions, method_name)):
            continue
        if method_name.startswith('_') and callable(getattr(extensions, method_name)):
            # Привязываем метод к экземпляру бота
            method = getattr(extensions, method_name)
            setattr(bot_instance, method_name, method.__get__(bot_instance, bot_instance.__class__))
    
    return bot_instance 