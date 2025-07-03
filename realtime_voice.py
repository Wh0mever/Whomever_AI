"""
OpenAI Realtime Voice API Integration
Модуль для интеграции speech-to-speech общения с OpenAI Realtime API
"""

import asyncio
import json
import logging
import base64
import io
import wave
import tempfile
import os
import uuid
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from datetime import datetime
import websockets
import aiohttp
from config import OPENAI_API_KEY
import sounddevice as sd
import numpy as np

# Временная совместимость с Python 3.13 (audioop удален)
try:
    from pydub import AudioSegment
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False
    print("⚠️ Аудио обработка pydub недоступна в Python 3.13. Используется базовый функционал.")

from aiogram.types import Message, FSInputFile

logger = logging.getLogger(__name__)

class RealtimeVoiceSession:
    """Класс для управления голосовой сессией в реальном времени"""
    
    def __init__(self, user_id: int, chat_id: int, api_key: str):
        self.user_id = user_id
        self.chat_id = chat_id
        self.api_key = api_key
        self.session_id = str(uuid.uuid4())
        self.websocket = None
        self.is_connected = False
        self.is_recording = False
        self.audio_buffer = b""
        self.response_buffer = b""
        
        # Настройки аудио
        self.sample_rate = 24000
        self.audio_format = "pcm16"
        self.channels = 1
        
        # Колбэки для обработки событий
        self.on_audio_response: Optional[Callable] = None
        self.on_text_response: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_session_end: Optional[Callable] = None
        
        # Статистика сессии
        self.start_time = None
        self.messages_count = 0
        self.audio_duration = 0
        
    async def connect(self, instructions: str = None, voice: str = "alloy"):
        """Подключение к OpenAI Realtime API"""
        try:
            self.start_time = datetime.now()
            
            # URL для WebSocket подключения
            url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
            
            # Заголовки для аутентификации
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            # Подключаемся к WebSocket
            self.websocket = await websockets.connect(url, extra_headers=headers)
            self.is_connected = True
            
            logger.info(f"Подключение к Realtime API установлено для пользователя {self.user_id}")
            
            # Настройка сессии
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": instructions or "Ты дружелюбный голосовой помощник WHOMEVER. Отвечай естественно и эмоционально.",
                    "voice": voice,
                    "input_audio_format": self.audio_format,
                    "output_audio_format": self.audio_format,
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 200
                    },
                    "tools": self._get_available_tools()
                }
            }
            
            await self._send_event(session_config)
            
            # Запускаем обработчик входящих сообщений
            asyncio.create_task(self._handle_incoming_messages())
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к Realtime API: {e}")
            self.is_connected = False
            if self.on_error:
                await self.on_error(f"Ошибка подключения: {e}")
            return False
    
    def _get_available_tools(self) -> List[Dict]:
        """Получение доступных инструментов для голосового ассистента"""
        return [
            {
                "type": "function",
                "name": "search_internet",
                "description": "Поиск актуальной информации в интернете",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Поисковый запрос"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "type": "function", 
                "name": "generate_image",
                "description": "Создание изображения по описанию",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Описание изображения для генерации"
                        },
                        "size": {
                            "type": "string",
                            "enum": ["1024x1024", "1024x1792", "1792x1024"],
                            "default": "1024x1024",
                            "description": "Размер изображения"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "type": "function",
                "name": "analyze_image",
                "description": "Анализ изображения с помощью vision модели",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_description": {
                            "type": "string",
                            "description": "Описание изображения для анализа"
                        }
                    },
                    "required": ["image_description"]
                }
            }
        ]
    
    async def _send_event(self, event: Dict):
        """Отправка события в WebSocket"""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.send(json.dumps(event))
            except Exception as e:
                logger.error(f"Ошибка отправки события: {e}")
                await self._handle_connection_error(e)
    
    async def _handle_incoming_messages(self):
        """Обработка входящих сообщений от OpenAI"""
        try:
            async for message in self.websocket:
                try:
                    event = json.loads(message)
                    await self._process_event(event)
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка декодирования JSON: {e}")
                except Exception as e:
                    logger.error(f"Ошибка обработки события: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket соединение закрыто")
            await self._handle_disconnect()
        except Exception as e:
            logger.error(f"Ошибка в обработчике сообщений: {e}")
            await self._handle_connection_error(e)
    
    async def _process_event(self, event: Dict):
        """Обработка различных типов событий от API"""
        event_type = event.get("type")
        
        if event_type == "session.created":
            logger.info(f"Сессия создана: {event.get('session', {}).get('id')}")
            
        elif event_type == "session.updated":
            logger.info("Настройки сессии обновлены")
            
        elif event_type == "input_audio_buffer.speech_started":
            logger.debug("Начало речи пользователя")
            
        elif event_type == "input_audio_buffer.speech_stopped":
            logger.debug("Конец речи пользователя")
            
        elif event_type == "input_audio_buffer.committed":
            logger.debug("Аудио буфер зафиксирован")
            
        elif event_type == "conversation.item.created":
            item = event.get("item", {})
            if item.get("role") == "assistant":
                self.messages_count += 1
                
        elif event_type == "response.created":
            logger.debug("Начало генерации ответа")
            
        elif event_type == "response.audio.delta":
            # Получаем чанк аудио ответа
            audio_delta = event.get("delta")
            if audio_delta and self.on_audio_response:
                audio_data = base64.b64decode(audio_delta)
                await self.on_audio_response(audio_data)
                
        elif event_type == "response.audio_transcript.delta":
            # Получаем текст ответа
            text_delta = event.get("delta")
            if text_delta and self.on_text_response:
                await self.on_text_response(text_delta)
                
        elif event_type == "response.text.delta":
            # Альтернативный текстовый ответ
            text_delta = event.get("delta")
            if text_delta and self.on_text_response:
                await self.on_text_response(text_delta)
                
        elif event_type == "response.done":
            logger.debug("Ответ завершен")
            
        elif event_type == "response.function_call_arguments.delta":
            # Обработка вызова функций
            await self._handle_function_call(event)
            
        elif event_type == "error":
            error_msg = event.get("error", {}).get("message", "Неизвестная ошибка")
            logger.error(f"Ошибка API: {error_msg}")
            if self.on_error:
                await self.on_error(error_msg)
                
        else:
            logger.debug(f"Необработанный тип события: {event_type}")
    
    async def _handle_function_call(self, event: Dict):
        """Обработка вызова функций"""
        try:
            # Здесь можно добавить логику для обработки функций
            # Например, поиск в интернете или генерация изображений
            function_name = event.get("function_call", {}).get("name")
            arguments = event.get("function_call", {}).get("arguments", {})
            
            if function_name == "search_internet":
                # Выполняем поиск и отправляем результат обратно
                query = arguments.get("query", "")
                search_result = await self._perform_search(query)
                await self._send_function_result(event.get("call_id"), search_result)
                
            elif function_name == "generate_image":
                # Генерируем изображение
                prompt = arguments.get("prompt", "")
                size = arguments.get("size", "1024x1024")
                image_result = await self._generate_image(prompt, size)
                await self._send_function_result(event.get("call_id"), image_result)
                
        except Exception as e:
            logger.error(f"Ошибка обработки вызова функции: {e}")
    
    async def _perform_search(self, query: str) -> str:
        """Выполнение поиска в интернете"""
        try:
            from search_api import SearchAPI
            search_api = SearchAPI()
            results = await search_api.search(query, engine='duckduckgo', max_results=3)
            
            if results:
                formatted_results = []
                for result in results:
                    formatted_results.append(
                        f"• {result.get('title', 'Без названия')}\n"
                        f"  {result.get('description', '')[:150]}...\n"
                        f"  {result.get('url', '')}"
                    )
                return "Результаты поиска:\n" + "\n\n".join(formatted_results)
            else:
                return "По вашему запросу ничего не найдено."
                
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return "Извините, произошла ошибка при поиске информации."
    
    async def _generate_image(self, prompt: str, size: str) -> str:
        """Генерация изображения"""
        try:
            from openai_api import OpenAIAPI
            openai_api = OpenAIAPI()
            image_urls = await openai_api.generate_image(prompt, size=size)
            
            if image_urls:
                return f"Изображение создано по запросу '{prompt}'. URL: {image_urls[0]}"
            else:
                return "Извините, не удалось создать изображение."
                
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            return "Произошла ошибка при создании изображения."
    
    async def _send_function_result(self, call_id: str, result: str):
        """Отправка результата вызова функции"""
        function_result_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result
            }
        }
        await self._send_event(function_result_event)
        
        # Запрашиваем новый ответ с учетом результата функции
        await self._send_event({"type": "response.create"})
    
    async def send_audio(self, audio_data: bytes):
        """Отправка аудио данных в API"""
        if not self.is_connected:
            return False
            
        try:
            # Кодируем аудио в base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Отправляем аудио событие
            audio_event = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            
            await self._send_event(audio_event)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки аудио: {e}")
            return False
    
    async def send_text(self, text: str):
        """Отправка текстового сообщения"""
        if not self.is_connected:
            return False
            
        try:
            # Создаем текстовое сообщение
            text_event = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text
                        }
                    ]
                }
            }
            
            await self._send_event(text_event)
            
            # Запрашиваем ответ
            await self._send_event({"type": "response.create"})
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки текста: {e}")
            return False
    
    async def commit_audio(self):
        """Фиксация аудио буфера для обработки"""
        if self.is_connected:
            await self._send_event({"type": "input_audio_buffer.commit"})
    
    async def cancel_response(self):
        """Отмена текущего ответа (для прерываний)"""
        if self.is_connected:
            await self._send_event({"type": "response.cancel"})
    
    async def _handle_connection_error(self, error):
        """Обработка ошибок соединения"""
        self.is_connected = False
        if self.on_error:
            await self.on_error(f"Ошибка соединения: {error}")
    
    async def _handle_disconnect(self):
        """Обработка отключения"""
        self.is_connected = False
        if self.on_session_end:
            await self.on_session_end(self.get_session_stats())
    
    def get_session_stats(self) -> Dict:
        """Получение статистики сессии"""
        duration = 0
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "duration_seconds": duration,
            "messages_count": self.messages_count,
            "audio_duration": self.audio_duration
        }
    
    async def disconnect(self):
        """Закрытие соединения"""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.close()
            except:
                pass
            finally:
                self.is_connected = False
                logger.info(f"Сессия {self.session_id} завершена")


class RealtimeVoiceManager:
    """Менеджер для управления голосовыми сессиями"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.active_sessions: Dict[int, RealtimeVoiceSession] = {}  # user_id -> session
        self.max_sessions = 50  # Максимум одновременных сессий
        
    async def start_voice_session(self, user_id: int, chat_id: int, 
                                instructions: str = None, voice: str = "alloy") -> RealtimeVoiceSession:
        """Запуск новой голосовой сессии"""
        try:
            # Проверяем лимиты
            if len(self.active_sessions) >= self.max_sessions:
                # Закрываем самую старую сессию
                oldest_session = min(self.active_sessions.values(), 
                                   key=lambda s: s.start_time or datetime.now())
                await oldest_session.disconnect()
                del self.active_sessions[oldest_session.user_id]
            
            # Если у пользователя уже есть активная сессия, закрываем её
            if user_id in self.active_sessions:
                await self.active_sessions[user_id].disconnect()
                del self.active_sessions[user_id]
            
            # Создаем новую сессию
            session = RealtimeVoiceSession(user_id, chat_id, self.api_key)
            
            # Подключаемся
            if await session.connect(instructions, voice):
                self.active_sessions[user_id] = session
                logger.info(f"Голосовая сессия запущена для пользователя {user_id}")
                return session
            else:
                return None
                
        except Exception as e:
            logger.error(f"Ошибка запуска голосовой сессии: {e}")
            return None
    
    def get_session(self, user_id: int) -> Optional[RealtimeVoiceSession]:
        """Получение активной сессии пользователя"""
        return self.active_sessions.get(user_id)
    
    async def end_session(self, user_id: int) -> bool:
        """Завершение голосовой сессии"""
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            await session.disconnect()
            del self.active_sessions[user_id]
            logger.info(f"Сессия пользователя {user_id} завершена")
            return True
        return False
    
    async def end_all_sessions(self):
        """Завершение всех активных сессий"""
        for session in list(self.active_sessions.values()):
            await session.disconnect()
        self.active_sessions.clear()
        logger.info("Все голосовые сессии завершены")
    
    def get_active_sessions_count(self) -> int:
        """Количество активных сессий"""
        return len(self.active_sessions)
    
    def get_sessions_stats(self) -> List[Dict]:
        """Статистика всех активных сессий"""
        return [session.get_session_stats() for session in self.active_sessions.values()]


# Утилиты для работы с аудио
class AudioUtils:
    """Утилиты для обработки аудио данных"""
    
    @staticmethod
    def ogg_to_pcm16(ogg_data: bytes, target_sample_rate: int = 24000) -> bytes:
        """Конвертация OGG в PCM16 формат для Realtime API"""
        try:
            if AUDIO_PROCESSING_AVAILABLE:
                # Используем pydub для конвертации
                audio = AudioSegment.from_ogg(io.BytesIO(ogg_data))
                
                # Конвертируем в нужный формат
                audio = audio.set_frame_rate(target_sample_rate)
                audio = audio.set_channels(1)  # Mono
                audio = audio.set_sample_width(2)  # 16-bit
                
                return audio.raw_data
            else:
                # Базовое решение без pydub
                logger.warning("Конвертация OGG->PCM16 недоступна без pydub")
                return ogg_data  # Возвращаем как есть
            
        except Exception as e:
            logger.error(f"Ошибка конвертации OGG в PCM16: {e}")
            return b""
    
    @staticmethod
    def pcm16_to_ogg(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
        """Конвертация PCM16 в OGG для отправки в Telegram"""
        try:
            if AUDIO_PROCESSING_AVAILABLE:
                # Создаем AudioSegment из PCM данных
                audio = AudioSegment(
                    data=pcm_data,
                    sample_width=2,  # 16-bit
                    frame_rate=sample_rate,
                    channels=1  # Mono
                )
                
                # Экспортируем в OGG
                ogg_buffer = io.BytesIO()
                audio.export(ogg_buffer, format="ogg", codec="libopus")
                return ogg_buffer.getvalue()
            else:
                # Базовое решение без pydub
                logger.warning("Конвертация PCM16->OGG недоступна без pydub")
                return pcm_data  # Возвращаем как есть
            
        except Exception as e:
            logger.error(f"Ошибка конвертации PCM16 в OGG: {e}")
            return b""
    
    @staticmethod
    async def save_audio_to_file(audio_data: bytes, file_format: str = "ogg") -> str:
        """Сохранение аудио данных во временный файл"""
        try:
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=f".{file_format}"
            )
            temp_file.write(audio_data)
            temp_file.close()
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Ошибка сохранения аудио файла: {e}")
            return ""


# Глобальный менеджер голосовых сессий
voice_manager = RealtimeVoiceManager(OPENAI_API_KEY) 