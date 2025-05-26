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
                "model": "gpt-4o",
                "messages": validated_messages,
                "temperature": 0.7,
                "max_tokens": 2000,
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
                        return data['choices'][0]['message']['content']
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка API: {response.status} - {error_text}")
                        raise aiohttp.ClientError(f"Ошибка API: {response.status}")

    async def generate_response(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> str:
        try:
            return await self._make_request(messages, tools)
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
        # Здесь будет код для обработки PDF файлов
        return ["Обработка PDF файлов будет добавлена в следующем обновлении."]

    async def _process_doc_file(self, file_path: str, prompt_template: str) -> List[str]:
        # Здесь будет код для обработки DOC/DOCX файлов
        return ["Обработка DOC/DOCX файлов будет добавлена в следующем обновлении."]

    async def _process_image_file(self, file_path: str, prompt_template: str) -> List[str]:
        try:
            # Отправляем изображение в API для анализа
            with open(file_path, 'rb') as image_file:
                files = {'image': image_file}
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(
                    f"{self.base_url}/vision/analyze",
                    headers=headers,
                    files=files
                )
                
                if response.status_code == 200:
                    analysis = response.json()
                    messages = [
                        {"role": "system", "content": "Вы - помощник для анализа изображений."},
                        {"role": "user", "content": f"{prompt_template}\n\nАнализ изображения: {json.dumps(analysis, ensure_ascii=False)}"}
                    ]
                    return [await self.generate_response(messages)]
                else:
                    return ["Произошла ошибка при анализе изображения."]
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

    async def vision_analysis(self, image_path: str, prompt: str) -> str:
        """Анализ изображения через GPT-4 Vision"""
        try:
            # Конвертируем изображение в base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": "gpt-4-vision-preview",
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
                    "max_tokens": 500
                }
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                logger.error(f"Ошибка Vision API: {response.status_code} - {response.text}")
                return "Произошла ошибка при анализе изображения."
        except Exception as e:
            logger.error(f"Ошибка при анализе изображения: {str(e)}")
            return "Произошла ошибка при анализе изображения." 