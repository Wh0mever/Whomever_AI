import asyncio
import logging
import backoff
from typing import List, Dict, Any, Optional, Union
import aiohttp
import json
import os
from config import OPENAI_API_KEY
import mimetypes
import aiofiles
import requests
from bs4 import BeautifulSoup
import subprocess
import tempfile
import base64
from io import BytesIO
from PIL import Image
import websockets
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIAPI:
    def __init__(self, max_workers: int = 50):
        self.api_key = OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.supported_file_types = {
            'text/plain': self._process_text_file,
            'application/pdf': self._process_pdf_file,
            'application/msword': self._process_doc_file,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._process_doc_file,
            'image/jpeg': self._process_image_file,
            'image/png': self._process_image_file,
            'audio/ogg': self._process_audio_file,
            'audio/mpeg': self._process_audio_file,
            'audio/wav': self._process_audio_file,
            'video/mp4': self._process_video_file
        }
        
    def _validate_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Проверяет и очищает сообщения перед отправкой в API"""
        validated_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if 'role' not in msg or 'content' not in msg:
                continue
            if msg['content'] is None:
                continue
            validated_messages.append({
                'role': str(msg['role']),
                'content': str(msg['content'])
            })
        return validated_messages or [{'role': 'user', 'content': 'Привет'}]

    @backoff.on_exception(backoff.expo, 
                         (aiohttp.ClientError, asyncio.TimeoutError), 
                         max_tries=3)
    async def _make_request(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> str:
        async with self.semaphore:
            validated_messages = self._validate_messages(messages)
            
            request_data = {
                "model": "gpt-4.1-2025-04-14",  # Обновлено до GPT-4.1
                "messages": validated_messages,
                "temperature": 0.7,
                "max_tokens": 4000,  # Увеличено для GPT-4.1
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            if tools:
                request_data["tools"] = tools
                request_data["tool_choice"] = "auto"
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=request_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data['choices'][0]['message']['content']
                        return content if content is not None else "Извините, не удалось сгенерировать ответ."
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка API: {response.status} - {error_text}")
                        raise aiohttp.ClientError(f"Ошибка API: {response.status}")

    def _analyze_if_search_needed(self, messages: List[Dict[str, str]]) -> bool:
        """Анализ, нужен ли автоматический поиск в интернете"""
        try:
            if not messages:
                return False
            
            # Получаем последнее сообщение пользователя
            user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = (msg.get("content") or "").lower()
                    break
            
            if not user_message:
                return False
            
            # Ключевые слова, указывающие на необходимость поиска актуальной информации
            search_indicators = [
                "сейчас", "сегодня", "вчера", "завтра", "актуально", "последние",
                "новости", "текущий", "свежий", "недавно", "этот год", "2025",
                "что происходит", "что случилось", "цена", "курс", "стоимость",
                "погода", "время", "расписание", "когда", "где", "как добраться",
                "найди информацию", "поищи", "узнай", "проверь", "какая ситуация"
            ]
            
            # Темы, требующие актуальной информации
            search_topics = [
                "коронавирус", "covid", "политика", "экономика", "биржа", "акции",
                "криптовалют", "bitcoin", "эфир", "ethereum", "курс доллара", "евро",
                "выборы", "война", "санкции", "инфляция", "процентная ставка"
            ]
            
            # Проверяем индикаторы поиска
            has_search_indicator = any(indicator in user_message for indicator in search_indicators)
            has_search_topic = any(topic in user_message for topic in search_topics)
            
            # Вопросительные слова + актуальность
            question_words = ["что", "где", "когда", "как", "почему", "сколько", "какой", "какая", "какие"]
            has_question = any(word in user_message for word in question_words)
            
            return has_search_indicator or has_search_topic or (has_question and len(user_message) > 10)
            
        except Exception as e:
            logger.error(f"Ошибка анализа необходимости поиска: {e}")
            return False

    async def _handle_search_response(self, response: str, original_messages: List[Dict[str, str]]) -> str:
        """Обработка ответа с функцией поиска"""
        try:
            import json
            from search_api import SearchAPI
            
            # Ищем вызов функции в ответе
            if "search_internet" in response:
                # Извлекаем поисковый запрос (это упрощенная логика)
                user_message = ""
                for msg in reversed(original_messages):
                    if msg.get("role") == "user":
                        user_message = msg.get("content", "")
                        break
                
                # Создаем поисковый запрос на основе сообщения пользователя
                search_query = self._extract_search_query(user_message)
                
                if search_query:
                    # Выполняем поиск
                    search_api = SearchAPI()
                    search_results = await search_api.search(search_query, engine='duckduckgo')
                    
                    if search_results:
                        # Формируем контекст для ИИ с результатами поиска
                        search_context = self._format_search_results(search_results)
                        
                        # Делаем новый запрос с контекстом
                        enhanced_messages = original_messages.copy()
                        enhanced_messages.append({
                            "role": "system",
                            "content": f"Актуальная информация из интернета:\n{search_context}\n\nИспользуй эту информацию для ответа на вопрос пользователя."
                        })
                        
                        # Генерируем финальный ответ с учетом найденной информации
                        final_response = await self._make_request(enhanced_messages)
                        return f"🔍 *Информация обновлена из интернета*\n\n{final_response}"
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка обработки поискового ответа: {e}")
            return response

    def _extract_search_query(self, user_message: str) -> str:
        """Извлечение поискового запроса из сообщения пользователя"""
        try:
            # Убираем лишние слова и оставляем ключевые
            stop_words = ["пожалуйста", "можешь", "можете", "скажи", "расскажи", "объясни", "покажи"]
            words = user_message.lower().split()
            
            # Фильтруем стоп-слова
            filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
            
            # Ограничиваем длину запроса
            search_query = " ".join(filtered_words[:8])  # Максимум 8 слов
            
            return search_query
            
        except Exception as e:
            logger.error(f"Ошибка извлечения поискового запроса: {e}")
            return user_message[:100]  # Fallback

    def _format_search_results(self, search_results: List[Dict]) -> str:
        """Форматирование результатов поиска для контекста ИИ"""
        try:
            formatted_results = []
            
            for i, result in enumerate(search_results[:3], 1):  # Берем только первые 3 результата
                title = result.get('title', 'Без названия')
                description = result.get('description', '')
                url = result.get('url', '')
                
                formatted_result = f"{i}. {title}\n"
                if description:
                    formatted_result += f"   {description[:200]}...\n"
                if url:
                    formatted_result += f"   Источник: {url}\n"
                
                formatted_results.append(formatted_result)
            
            return "\n".join(formatted_results)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования результатов поиска: {e}")
            return "Результаты поиска недоступны"

    async def generate_response(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> str:
        try:
            # Определяем, нужен ли поиск
            needs_search = self._analyze_if_search_needed(messages)
            
            if needs_search:
                # Добавляем tool для автоматического поиска
                search_tool = {
                    "type": "function",
                    "function": {
                        "name": "search_internet",
                        "description": "Поиск актуальной информации в интернете",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Поисковый запрос для получения актуальной информации"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
                
                if tools:
                    tools.append(search_tool)
                else:
                    tools = [search_tool]
            
            response = await self._make_request(messages, tools)
            
            # Если бот решил использовать поиск, выполняем его
            if needs_search and "search_internet" in str(response):
                return await self._handle_search_response(response, messages)
            
            return response
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}")
            return "Произошла ошибка при обработке вашего запроса."

    async def process_file(self, file_path: str, prompt_template: str) -> List[str]:
        """Обработка файла с использованием GPT-4o"""
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type in self.supported_file_types:
                processor = self.supported_file_types[mime_type]
                return await processor(file_path, prompt_template)
            else:
                return ["Извините, этот тип файла не поддерживается."]
                
        except Exception as e:
            logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
            return []

    async def _process_text_file(self, file_path: str, prompt_template: str) -> List[str]:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            content = await file.read()
            chunks = self._split_text(content, max_chunk_size=4000)
            
            tasks = []
            for chunk in chunks:
                messages = [
                    {"role": "system", "content": "Вы - помощник для анализа текста."},
                    {"role": "user", "content": prompt_template.format(text=chunk)}
                ]
                tasks.append(self.generate_response(messages))
            
            results = await asyncio.gather(*tasks)
            return results

    async def _process_pdf_file(self, file_path: str, prompt_template: str) -> List[str]:
        """Обработка PDF файлов с использованием современных методов"""
        try:
            import fitz  # PyMuPDF
            from PyPDF2 import PdfReader
            import io
            
            # Сначала пробуем PyMuPDF (быстрый и надежный)
            try:
                doc = fitz.open(file_path)
                text_content = ""
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text_content += page.get_text()
                    
                    # Извлекаем таблицы если есть
                    tables = page.find_tables()
                    for table in tables:
                        try:
                            table_data = table.extract()
                            table_text = "\n".join(["\t".join(row) for row in table_data if row])
                            text_content += f"\n\nТаблица:\n{table_text}\n"
                        except:
                            continue
                
                doc.close()
                
                if text_content.strip():
                    # Разбиваем на чанки для обработки
                    chunks = self._split_text(text_content, max_chunk_size=3000)
                    
                    tasks = []
                    for chunk in chunks:
                        if chunk.strip():
                            messages = [
                                {"role": "system", "content": "Ты эксперт по анализу документов. Проанализируй содержание и выдели ключевые моменты."},
                                {"role": "user", "content": f"Документ:\n{chunk}\n\nЗапрос: {prompt_template or 'Проанализируй и выдели основные моменты из этого документа'}"}
                            ]
                            tasks.append(self.generate_response(messages))
                    
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        valid_results = [r for r in results if isinstance(r, str)]
                        return valid_results if valid_results else ["Не удалось извлечь осмысленное содержание из PDF."]
                        
            except Exception as pymupdf_error:
                logger.warning(f"PyMuPDF failed: {pymupdf_error}, trying PyPDF2...")
            
            # Fallback на PyPDF2
            try:
                reader = PdfReader(file_path)
                text_content = ""
                
                for page in reader.pages:
                    text_content += page.extract_text() + "\n"
                
                if text_content.strip():
                    chunks = self._split_text(text_content, max_chunk_size=3000)
                    
                    tasks = []
                    for chunk in chunks:
                        if chunk.strip():
                            messages = [
                                {"role": "system", "content": "Ты эксперт по анализу документов."},
                                {"role": "user", "content": f"Документ:\n{chunk}\n\nЗапрос: {prompt_template or 'Проанализируй этот документ'}"}
                            ]
                            tasks.append(self.generate_response(messages))
                    
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        valid_results = [r for r in results if isinstance(r, str)]
                        return valid_results if valid_results else ["Содержание PDF извлечено, но анализ не удался."]
                        
            except Exception as pypdf2_error:
                logger.error(f"PyPDF2 also failed: {pypdf2_error}")
            
            return ["❌ Не удалось прочитать PDF файл. Возможно, файл поврежден или защищен паролем."]
            
        except Exception as e:
            logger.error(f"Ошибка при обработке PDF файла: {str(e)}")
            return [f"❌ Ошибка обработки PDF: {str(e)}"]

    async def _process_doc_file(self, file_path: str, prompt_template: str) -> List[str]:
        """Обработка DOC/DOCX файлов"""
        try:
            import docx
            from docx import Document
            
            # Открываем документ
            doc = Document(file_path)
            text_content = ""
            
            # Извлекаем текст из параграфов
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            
            # Извлекаем текст из таблиц
            for table in doc.tables:
                table_text = "\n\nТаблица:\n"
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        row_text.append(cell.text.strip())
                    table_text += "\t".join(row_text) + "\n"
                text_content += table_text
            
            if not text_content.strip():
                return ["❌ Документ не содержит текста или не удалось его извлечь."]
            
            # Разбиваем на чанки для обработки
            chunks = self._split_text(text_content, max_chunk_size=3000)
            
            tasks = []
            for chunk in chunks:
                if chunk.strip():
                    messages = [
                        {"role": "system", "content": "Ты эксперт по анализу документов. Проанализируй содержание и выдели ключевые моменты."},
                        {"role": "user", "content": f"Документ:\n{chunk}\n\nЗапрос: {prompt_template or 'Проанализируй и выдели основные моменты из этого документа'}"}
                    ]
                    tasks.append(self.generate_response(messages))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                valid_results = [r for r in results if isinstance(r, str)]
                return valid_results if valid_results else ["Не удалось извлечь осмысленное содержание из документа."]
            else:
                return ["Документ пуст или не содержит анализируемого текста."]
                
        except ImportError:
            return ["❌ Для обработки DOC/DOCX файлов требуется установить библиотеку python-docx: pip install python-docx"]
        except Exception as e:
            logger.error(f"Ошибка при обработке DOC/DOCX файла: {str(e)}")
            return [f"❌ Ошибка обработки документа: {str(e)}"]

    async def _process_image_file(self, file_path: str, prompt_template: str) -> List[str]:
        """Обработка изображений через GPT-4.1 Vision"""
        try:
            # Используем GPT-4.1 Vision для анализа изображения
            analysis_result = await self.vision_analysis(
                file_path, 
                prompt_template or "Опишите подробно что изображено на этой картинке, включая детали, объекты, цвета, настроение и контекст."
            )
            return [analysis_result]
        except Exception as e:
            logger.error(f"Ошибка при обработке изображения: {str(e)}")
            return ["Произошла ошибка при обработке изображения."]

    async def search_web(self, query: str, num_results: int = 5) -> str:
        """Поиск информации в интернете"""
        try:
            search_url = f"https://api.bing.microsoft.com/v7.0/search"
            headers = {
                "Ocp-Apim-Subscription-Key": "YOUR_BING_API_KEY"  # Нужно будет добавить ключ в config.py
            }
            params = {
                "q": query,
                "count": num_results,
                "mkt": "ru-RU"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        for item in data.get("webPages", {}).get("value", []):
                            results.append({
                                "title": item["name"],
                                "snippet": item["snippet"],
                                "url": item["url"]
                            })
                        
                        # Форматируем результаты для ответа
                        formatted_results = "\n\n".join([
                            f"📌 {r['title']}\n{r['snippet']}\n🔗 {r['url']}"
                            for r in results
                        ])
                        
                        return formatted_results
                    else:
                        return "Извините, не удалось выполнить поиск."
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")
            return "Произошла ошибка при выполнении поиска."

    def _split_text(self, text: str, max_chunk_size: int) -> List[str]:
        """Разделение текста на части подходящего размера"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 для пробела
            if current_size + word_size > max_chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks 

    async def transcribe_audio(self, file_path: str, language: str = "ru") -> str:
        """Транскрибация аудио через Whisper API"""
        try:
            with open(file_path, 'rb') as audio:
                response = requests.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"file": audio},
                    data={
                        "model": "whisper-1",
                        "language": language,
                        "response_format": "text"
                    }
                )
                
                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f"Ошибка Whisper API: {response.status_code} - {response.text}")
                    return "Произошла ошибка при транскрибации аудио."
        except Exception as e:
            logger.error(f"Ошибка при транскрибации аудио: {str(e)}")
            return "Произошла ошибка при обработке аудио файла."

    async def _process_audio_file(self, file_path: str, prompt_template: str = None) -> List[str]:
        """Обработка аудио файлов"""
        try:
            # Транскрибируем аудио
            transcription = await self.transcribe_audio(file_path)
            
            # Генерируем ответ на основе транскрипции
            messages = [
                {"role": "system", "content": "Вы - помощник для анализа аудио транскрипций."},
                {"role": "user", "content": f"Вот транскрипция аудио:\n\n{transcription}\n\nПожалуйста, проанализируйте содержание и предоставьте краткое резюме."}
            ]
            
            response = await self.generate_response(messages)
            return [f"📝 Транскрипция:\n{transcription}\n\n📋 Анализ:\n{response}"]
            
        except Exception as e:
            logger.error(f"Ошибка при обработке аудио файла: {str(e)}")
            return ["Произошла ошибка при обработке аудио файла."]

    async def _process_video_file(self, file_path: str, prompt_template: str = None) -> List[str]:
        """Обработка видео файлов - извлечение аудио и транскрибация"""
        try:
            # Создаем временный файл для аудио
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name
            
            # Извлекаем аудио из видео с помощью ffmpeg
            command = [
                'ffmpeg', '-i', file_path,
                '-q:a', '0', '-map', 'a', temp_audio_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                # Транскрибируем извлеченное аудио
                result = await self._process_audio_file(temp_audio_path)
                
                # Удаляем временный файл
                os.remove(temp_audio_path)
                
                return result
            else:
                return ["Произошла ошибка при извлечении аудио из видео."]
                
        except Exception as e:
            logger.error(f"Ошибка при обработке видео файла: {str(e)}")
            return ["Произошла ошибка при обработке видео файла."]

    async def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "standard", n: int = 1) -> List[str]:
        """Генерация изображений через DALL-E"""
        try:
            response = requests.post(
                f"{self.base_url}/images/generations",
                headers=self.headers,
                json={
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": n,
                    "size": size,
                    "quality": quality,
                    "response_format": "url"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return [image["url"] for image in data["data"]]
            else:
                logger.error(f"Ошибка DALL-E API: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {str(e)}")
            return []

    async def edit_image(self, image_path: str, mask_path: str, prompt: str, size: str = "1024x1024", n: int = 1) -> List[str]:
        """Редактирование изображений через DALL-E"""
        try:
            with open(image_path, 'rb') as image, open(mask_path, 'rb') as mask:
                response = requests.post(
                    f"{self.base_url}/images/edits",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={
                        "image": ("image.png", image, "image/png"),
                        "mask": ("mask.png", mask, "image/png")
                    },
                    data={
                        "prompt": prompt,
                        "n": n,
                        "size": size,
                        "response_format": "url"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [image["url"] for image in data["data"]]
                else:
                    logger.error(f"Ошибка DALL-E API: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Ошибка при редактировании изображения: {str(e)}")
            return []

    async def create_image_variation(self, image_path: str, size: str = "1024x1024", n: int = 1) -> List[str]:
        """Создание вариаций изображения через DALL-E"""
        try:
            with open(image_path, 'rb') as image:
                response = requests.post(
                    f"{self.base_url}/images/variations",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"image": ("image.png", image, "image/png")},
                    data={
                        "n": n,
                        "size": size,
                        "response_format": "url"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [image["url"] for image in data["data"]]
                else:
                    logger.error(f"Ошибка DALL-E API: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Ошибка при создании вариации изображения: {str(e)}")
            return []

    async def text_to_speech(self, text: str, voice: str = "alloy", format: str = "mp3") -> bytes:
        """Генерация речи из текста через TTS API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/audio/speech",
                    headers=self.headers,
                    json={
                        "model": "tts-1-hd",  # Высокое качество
                        "input": text[:4096],  # Ограничение TTS API
                        "voice": voice,
                        "response_format": format,
                        "speed": 1.0
                    }
                ) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка TTS API: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при генерации речи: {str(e)}")
            return None

    async def realtime_voice_chat(self, text: str, voice: str = "alloy") -> bytes:
        """Real-time голосовой чат через WebSocket"""
        try:
            url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            async with websockets.connect(url, extra_headers=headers) as ws:
                # Настройка сессии
                event_id = str(uuid.uuid4())
                session_event = {
                    "type": "session.update",
                    "session": {
                        "modalities": ["audio", "text"],
                        "instructions": "Вы - дружелюбный помощник WHOMEVER. Отвечайте естественно и выразительно.",
                        "voice": voice,
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "input_audio_transcription": {
                            "model": "whisper-1"
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 200
                        }
                    }
                }
                await ws.send(json.dumps(session_event))
                
                # Отправляем текстовое сообщение
                async for response in ws:
                    res = json.loads(response)
                    if res["type"] == "session.updated":
                        text_message = {
                            "event_id": str(uuid.uuid4()),
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": text}]
                            }
                        }
                        await ws.send(json.dumps(text_message))
                        
                        # Запрашиваем ответ
                        async for response2 in ws:
                            res2 = json.loads(response2)
                            
                            if res2['type'] == 'conversation.item.created':
                                response_message = {
                                    "event_id": str(uuid.uuid4()),
                                    "type": "response.create",
                                    "response": {
                                        "modalities": ["audio", "text"],
                                        "voice": voice,
                                        "output_audio_format": "pcm16"
                                    }
                                }
                                await ws.send(json.dumps(response_message))
                                
                                # Собираем аудио данные
                                audio_chunks = []
                                async for response3 in ws:
                                    res3 = json.loads(response3)
                                    
                                    if res3['type'] == "response.audio.delta":
                                        audio_data = base64.b64decode(res3["delta"])
                                        audio_chunks.append(audio_data)
                                    
                                    elif res3['type'] == 'response.done':
                                        # Объединяем все аудио чанки
                                        if audio_chunks:
                                            return b''.join(audio_chunks)
                                        return None
                                        
                return None
                
        except Exception as e:
            logger.error(f"Ошибка в realtime voice chat: {str(e)}")
            return None

    def get_available_voices(self) -> list:
        """Получение списка доступных голосов"""
        return [
            "alloy",    # Нейтральный
            "echo",     # Мужской  
            "fable",    # Британский акцент
            "onyx",     # Глубокий мужской
            "nova",     # Женский
            "shimmer"   # Мягкий женский
        ]

    def convert_pcm_to_ogg(self, pcm_data: bytes, sample_rate: int = 24000) -> bytes:
        """Конвертация PCM в OGG для Telegram"""
        try:
            import io
            import wave
            import subprocess
            
            # Создаем временный WAV файл в памяти
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Моно
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_data)
            
            wav_io.seek(0)
            
            # Конвертируем в OGG через FFmpeg
            process = subprocess.Popen([
                'ffmpeg', '-f', 'wav', '-i', 'pipe:0', 
                '-c:a', 'libopus', '-b:a', '64k', 
                '-f', 'ogg', 'pipe:1'
            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            ogg_data, _ = process.communicate(input=wav_io.read())
            return ogg_data
            
        except Exception as e:
            logger.error(f"Ошибка конвертации аудио: {str(e)}")
            return None

    async def vision_analysis(self, image_path: str, prompt: str) -> str:
        """Анализ изображения через GPT-4.1 Vision"""
        try:
            # Конвертируем изображение в base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": "gpt-4.1-2025-04-14",  # Обновлено до GPT-4.1
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 1000  # Увеличено для более детального анализа
                    }
                ) as response:
            
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка Vision API: {response.status} - {error_text}")
                        return "Произошла ошибка при анализе изображения."
        except Exception as e:
            logger.error(f"Ошибка при анализе изображения: {str(e)}")
            return "Произошла ошибка при анализе изображения." 