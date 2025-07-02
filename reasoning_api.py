"""
OpenAI O3/O4-mini Reasoning Models with Agentic Tool Use
Модуль для автономного принятия решений ИИ и использования инструментов
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
import aiohttp
from config import OPENAI_API_KEY, REASONING_MODELS_SETTINGS, AGENTIC_TOOLS
from search_api import SearchAPI
from openai_api import OpenAIAPI

logger = logging.getLogger(__name__)

class AgenticReasoningEngine:
    """Движок автономного рассуждения с инструментами"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Инициализируем API для инструментов
        self.openai_api = OpenAIAPI()
        self.search_api = SearchAPI()
        
        # Доступные инструменты
        self.available_tools = self._initialize_tools()
        
        # Статистика использования
        self.reasoning_sessions = {}
        self.tool_usage_stats = {}
        
    def _initialize_tools(self) -> Dict[str, Dict]:
        """Инициализация доступных инструментов"""
        tools = {
            "search_internet": {
                "type": "function",
                "function": {
                    "name": "search_internet",
                    "description": "Поиск актуальной информации в интернете. Используй когда нужна свежая, актуальная информация, новости, цены, курсы валют и т.д.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Поисковый запрос. Должен быть конкретным и содержать ключевые слова"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Количество результатов поиска (1-10)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                },
                "handler": self._handle_search
            },
            
            "generate_image": {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "Создание изображения по описанию. Используй когда пользователь просит создать, нарисовать или сгенерировать картинку",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Детальное описание изображения на английском языке"
                            },
                            "size": {
                                "type": "string",
                                "enum": ["1024x1024", "1024x1792", "1792x1024"],
                                "default": "1024x1024"
                            },
                            "quality": {
                                "type": "string",
                                "enum": ["standard", "hd"],
                                "default": "standard"
                            }
                        },
                        "required": ["prompt"]
                    }
                },
                "handler": self._handle_image_generation
            },
            
            "analyze_image": {
                "type": "function", 
                "function": {
                    "name": "analyze_image",
                    "description": "Анализ изображения с помощью GPT-4.1 Vision. Используй когда нужно проанализировать, описать или понять содержимое картинки",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_path": {
                                "type": "string",
                                "description": "Путь к файлу изображения"
                            },
                            "analysis_prompt": {
                                "type": "string",
                                "description": "Что именно нужно проанализировать в изображении"
                            }
                        },
                        "required": ["image_path", "analysis_prompt"]
                    }
                },
                "handler": self._handle_image_analysis
            },
            
            "process_document": {
                "type": "function",
                "function": {
                    "name": "process_document",
                    "description": "Обработка и анализ документов (PDF, DOC, TXT). Используй когда нужно проанализировать содержимое документа",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Путь к файлу документа"
                            },
                            "analysis_type": {
                                "type": "string",
                                "enum": ["summary", "detailed", "specific", "extraction"],
                                "description": "Тип анализа документа"
                            },
                            "specific_query": {
                                "type": "string",
                                "description": "Конкретный вопрос или задача для анализа документа"
                            }
                        },
                        "required": ["file_path", "analysis_type"]
                    }
                },
                "handler": self._handle_document_processing
            },
            
            "create_voice_response": {
                "type": "function",
                "function": {
                    "name": "create_voice_response", 
                    "description": "Создание голосового ответа. Используй когда пользователь просит ответить голосом или в голосовом режиме",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Текст для озвучивания"
                            },
                            "voice": {
                                "type": "string",
                                "enum": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                                "default": "alloy"
                            },
                            "emotion": {
                                "type": "string",
                                "enum": ["neutral", "excited", "calm", "serious", "friendly"],
                                "default": "neutral"
                            }
                        },
                        "required": ["text"]
                    }
                },
                "handler": self._handle_voice_response
            },
            
            "multi_step_analysis": {
                "type": "function",
                "function": {
                    "name": "multi_step_analysis",
                    "description": "Многошаговый анализ сложной задачи. Используй для разбиения сложных вопросов на этапы",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_description": {
                                "type": "string",
                                "description": "Описание сложной задачи"
                            },
                            "steps": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Список шагов для выполнения"
                            },
                            "expected_outcome": {
                                "type": "string", 
                                "description": "Ожидаемый результат"
                            }
                        },
                        "required": ["task_description"]
                    }
                },
                "handler": self._handle_multi_step_analysis
            }
        }
        
        return tools
    
    async def autonomous_reasoning(self, user_query: str, context: Dict = None, 
                                 user_id: int = None, chat_id: int = None) -> Dict[str, Any]:
        """Автономное рассуждение с принятием решений о использовании инструментов"""
        try:
            session_id = f"{user_id}_{chat_id}_{datetime.now().timestamp()}"
            
            # Анализируем сложность запроса для выбора модели
            model = await self._select_optimal_model(user_query, context)
            
            # Создаем системный промпт для автономного агента
            system_prompt = self._create_agentic_system_prompt()
            
            # Подготавливаем сообщения
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            
            # Добавляем контекст если есть
            if context:
                context_str = self._format_context(context)
                messages.append({"role": "system", "content": f"Контекст: {context_str}"})
            
            # Добавляем запрос пользователя
            messages.append({"role": "user", "content": user_query})
            
            # Список доступных инструментов для модели
            tools = [tool_config["type"] for tool_config in self.available_tools.values()]
            
            # Инициализируем сессию рассуждения
            reasoning_session = {
                "session_id": session_id,
                "start_time": datetime.now(),
                "model": model,
                "user_query": user_query,
                "steps": [],
                "tools_used": [],
                "final_response": None
            }
            
            self.reasoning_sessions[session_id] = reasoning_session
            
            # Выполняем рассуждение с возможностью использования инструментов
            result = await self._execute_reasoning_with_tools(
                messages, tools, model, session_id, max_steps=10
            )
            
            # Обновляем сессию
            reasoning_session["end_time"] = datetime.now()
            reasoning_session["final_response"] = result
            
            return {
                "response": result["content"],
                "tools_used": result.get("tools_used", []),
                "reasoning_steps": result.get("reasoning_steps", []),
                "model_used": model,
                "session_id": session_id,
                "autonomy_level": result.get("autonomy_level", "standard")
            }
            
        except Exception as e:
            logger.error(f"Ошибка автономного рассуждения: {e}")
            return {
                "response": "Произошла ошибка при обработке запроса.",
                "error": str(e),
                "tools_used": [],
                "reasoning_steps": []
            }
    
    async def _select_optimal_model(self, query: str, context: Dict = None) -> str:
        """Автоматический выбор оптимальной модели в зависимости от сложности задачи"""
        if not REASONING_MODELS_SETTINGS.get("auto_model_selection", True):
            return "o4-mini-2025-04-16"  # Дефолтная модель
        
        # Анализируем сложность запроса
        complexity_indicators = {
            "high": ["сложный", "анализ", "исследование", "многошаговый", "детальный", "глубокий"],
            "math": ["математика", "формула", "расчет", "вычисли", "задача", "уравнение"],
            "code": ["код", "программа", "алгоритм", "функция", "скрипт", "разработка"],
            "reasoning": ["почему", "объясни", "рассуждение", "логика", "доказательство", "обоснование"],
            "visual": ["изображение", "картинка", "визуальный", "диаграмма", "схема", "график"]
        }
        
        query_lower = query.lower()
        complexity_score = 0
        
        # Подсчитываем показатели сложности
        for category, indicators in complexity_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in query_lower)
            if category == "high":
                complexity_score += matches * 3
            elif category in ["math", "code", "reasoning"]:
                complexity_score += matches * 2
            else:
                complexity_score += matches
        
        # Учитываем длину запроса
        if len(query) > 500:
            complexity_score += 2
        elif len(query) > 200:
            complexity_score += 1
        
        # Учитываем контекст
        if context and len(str(context)) > 1000:
            complexity_score += 1
        
        # Выбираем модель на основе сложности
        if complexity_score >= 5 and REASONING_MODELS_SETTINGS.get("o3_enabled", True):
            return "o3-2025-04-16"  # O3 для сложных задач
        else:
            return "o4-mini-2025-04-16"  # O4-mini для стандартных задач
    
    def _create_agentic_system_prompt(self) -> str:
        """Создание системного промпта для автономного агента"""
        return """Ты - автономный ИИ-агент WHOMEVER с возможностью самостоятельно принимать решения о использовании инструментов.

ТВОИ СПОСОБНОСТИ:
🧠 Автономное рассуждение - ты можешь планировать многошаговые задачи
🔧 Умные инструменты - ты САМА решаешь когда и какие инструменты использовать
🎯 Проактивность - предлагай дополнительные действия когда это полезно
🔍 Глубокий анализ - разбивай сложные задачи на понятные этапы

ДОСТУПНЫЕ ИНСТРУМЕНТЫ:
- search_internet: Поиск актуальной информации (используй для новостей, цен, курсов, etc.)
- generate_image: Создание изображений (используй когда нужно что-то нарисовать)
- analyze_image: Анализ изображений (описание, понимание содержимого)
- process_document: Обработка документов (PDF, DOC анализ)
- create_voice_response: Голосовые ответы (когда просят ответить голосом)
- multi_step_analysis: Многошаговый анализ (для сложных задач)

ПРИНЦИПЫ АВТОНОМНОЙ РАБОТЫ:
1. САМА оценивай что нужно для ответа - если нужна свежая информация, САМА ищи
2. САМА решай какие инструменты использовать - не спрашивай разрешения
3. Если можешь улучшить ответ дополнительными действиями - ДЕЛАЙ это
4. Планируй последовательность действий для сложных задач
5. Объясняй ЧТО ты делаешь и ПОЧЕМУ

СТИЛЬ ОТВЕТОВ:
- Будь дружелюбной, но профессиональной
- Показывай процесс мышления
- Предлагай дополнительную помощь
- Используй эмодзи для наглядности

Помни: ты не просто отвечаешь на вопросы, ты АКТИВНО помогаешь пользователю достичь цели!"""
    
    def _format_context(self, context: Dict) -> str:
        """Форматирование контекста для передачи в модель"""
        try:
            context_parts = []
            
            if "user_profile" in context:
                profile = context["user_profile"]
                context_parts.append(f"Профиль пользователя: {profile}")
            
            if "chat_history" in context:
                history = context["chat_history"]
                context_parts.append(f"История чата: {history}")
            
            if "current_task" in context:
                task = context["current_task"]
                context_parts.append(f"Текущая задача: {task}")
            
            if "available_files" in context:
                files = context["available_files"]
                context_parts.append(f"Доступные файлы: {files}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Ошибка форматирования контекста: {e}")
            return str(context)
    
    async def _execute_reasoning_with_tools(self, messages: List[Dict], tools: List[Dict], 
                                          model: str, session_id: str, max_steps: int = 10) -> Dict:
        """Выполнение рассуждения с возможностью использования инструментов"""
        try:
            current_messages = messages.copy()
            tools_used = []
            reasoning_steps = []
            step_count = 0
            
            while step_count < max_steps:
                step_count += 1
                
                # Запрос к модели с инструментами
                request_data = {
                    "model": model,
                    "messages": current_messages,
                    "tools": tools,
                    "tool_choice": "auto",  # Модель сама решает
                    "temperature": 0.7,
                    "max_tokens": 4000
                }
                
                # Отправляем запрос
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=request_data
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Ошибка API: {response.status} - {error_text}")
                            break
                        
                        data = await response.json()
                        message = data["choices"][0]["message"]
                        
                        # Добавляем ответ модели в историю
                        current_messages.append(message)
                        
                        # Проверяем, хочет ли модель использовать инструменты
                        tool_calls = message.get("tool_calls", [])
                        
                        if not tool_calls:
                            # Модель дала финальный ответ без инструментов
                            return {
                                "content": message.get("content", ""),
                                "tools_used": tools_used,
                                "reasoning_steps": reasoning_steps,
                                "autonomy_level": "autonomous" if tools_used else "standard"
                            }
                        
                        # Выполняем вызовы инструментов
                        for tool_call in tool_calls:
                            function_name = tool_call["function"]["name"]
                            function_args = json.loads(tool_call["function"]["arguments"])
                            call_id = tool_call["id"]
                            
                            # Логируем использование инструмента
                            reasoning_steps.append({
                                "step": step_count,
                                "action": f"Использую инструмент {function_name}",
                                "arguments": function_args,
                                "timestamp": datetime.now().isoformat()
                            })
                            
                            # Выполняем инструмент
                            if function_name in self.available_tools:
                                handler = self.available_tools[function_name]["handler"]
                                result = await handler(**function_args)
                                
                                tools_used.append({
                                    "name": function_name,
                                    "arguments": function_args,
                                    "result": result
                                })
                                
                                # Добавляем результат в сообщения
                                current_messages.append({
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "content": json.dumps(result, ensure_ascii=False)
                                })
                                
                                # Обновляем статистику
                                self.tool_usage_stats[function_name] = self.tool_usage_stats.get(function_name, 0) + 1
                            
                            else:
                                # Неизвестный инструмент
                                current_messages.append({
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "content": json.dumps({"error": f"Unknown tool: {function_name}"})
                                })
            
            # Если достигли максимума шагов, возвращаем последний ответ
            last_message = current_messages[-1] if current_messages else {"content": "Превышено максимальное количество шагов"}
            
            return {
                "content": last_message.get("content", "Процесс рассуждения прерван"),
                "tools_used": tools_used,
                "reasoning_steps": reasoning_steps,
                "autonomy_level": "complex_autonomous"
            }
            
        except Exception as e:
            logger.error(f"Ошибка выполнения рассуждения: {e}")
            return {
                "content": f"Ошибка выполнения: {e}",
                "tools_used": tools_used,
                "reasoning_steps": reasoning_steps
            }
    
    # Обработчики инструментов
    async def _handle_search(self, query: str, num_results: int = 5) -> Dict:
        """Обработчик поиска в интернете"""
        try:
            results = await self.search_api.search(query, max_results=num_results)
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result.get("title", ""),
                    "description": result.get("description", ""),
                    "url": result.get("url", "")
                })
            
            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "total_found": len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return {"success": False, "error": str(e), "results": []}
    
    async def _handle_image_generation(self, prompt: str, size: str = "1024x1024", 
                                     quality: str = "standard") -> Dict:
        """Обработчик генерации изображений"""
        try:
            image_urls = await self.openai_api.generate_image(prompt, size=size, quality=quality)
            
            return {
                "success": True,
                "prompt": prompt,
                "image_urls": image_urls,
                "size": size,
                "quality": quality
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации изображения: {e}")
            return {"success": False, "error": str(e), "image_urls": []}
    
    async def _handle_image_analysis(self, image_path: str, analysis_prompt: str) -> Dict:
        """Обработчик анализа изображений"""
        try:
            analysis_result = await self.openai_api.vision_analysis(image_path, analysis_prompt)
            
            return {
                "success": True,
                "image_path": image_path,
                "analysis_prompt": analysis_prompt,
                "analysis": analysis_result
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа изображения: {e}")
            return {"success": False, "error": str(e), "analysis": ""}
    
    async def _handle_document_processing(self, file_path: str, analysis_type: str, 
                                        specific_query: str = None) -> Dict:
        """Обработчик обработки документов"""
        try:
            prompt_template = self._get_document_analysis_prompt(analysis_type, specific_query)
            results = await self.openai_api.process_file(file_path, prompt_template)
            
            return {
                "success": True,
                "file_path": file_path,
                "analysis_type": analysis_type,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Ошибка обработки документа: {e}")
            return {"success": False, "error": str(e), "results": []}
    
    def _get_document_analysis_prompt(self, analysis_type: str, specific_query: str = None) -> str:
        """Создание промпта для анализа документа"""
        prompts = {
            "summary": "Создай краткое резюме основных моментов этого документа.",
            "detailed": "Проведи детальный анализ документа, выдели ключевые моменты, структуру и важные детали.",
            "specific": specific_query or "Ответь на конкретный вопрос о документе.",
            "extraction": "Извлеки все важные данные, факты, цифры и ключевую информацию."
        }
        return prompts.get(analysis_type, prompts["summary"])
    
    async def _handle_voice_response(self, text: str, voice: str = "alloy", 
                                   emotion: str = "neutral") -> Dict:
        """Обработчик создания голосового ответа"""
        try:
            # Адаптируем текст под эмоцию
            adapted_text = self._adapt_text_for_emotion(text, emotion)
            
            audio_data = await self.openai_api.text_to_speech(adapted_text, voice=voice)
            
            return {
                "success": True,
                "text": adapted_text,
                "voice": voice,
                "emotion": emotion,
                "audio_size": len(audio_data)
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания голосового ответа: {e}")
            return {"success": False, "error": str(e), "audio_size": 0}
    
    def _adapt_text_for_emotion(self, text: str, emotion: str) -> str:
        """Адаптация текста под эмоцию"""
        emotion_adaptations = {
            "excited": lambda t: f"О, {t}! Это же здорово!",
            "calm": lambda t: f"Позвольте спокойно объяснить: {t}",
            "serious": lambda t: f"Важно понимать: {t}",
            "friendly": lambda t: f"Дружески отвечу: {t} 😊"
        }
        
        adapter = emotion_adaptations.get(emotion)
        return adapter(text) if adapter else text
    
    async def _handle_multi_step_analysis(self, task_description: str, steps: List[str] = None, 
                                        expected_outcome: str = None) -> Dict:
        """Обработчик многошагового анализа"""
        try:
            if not steps:
                # Автоматически разбиваем задачу на шаги
                steps = await self._generate_task_steps(task_description)
            
            step_results = []
            for i, step in enumerate(steps, 1):
                step_result = {
                    "step_number": i,
                    "step_description": step,
                    "status": "planned",
                    "result": None
                }
                step_results.append(step_result)
            
            return {
                "success": True,
                "task_description": task_description,
                "total_steps": len(steps),
                "steps": step_results,
                "expected_outcome": expected_outcome,
                "status": "planned"
            }
            
        except Exception as e:
            logger.error(f"Ошибка многошагового анализа: {e}")
            return {"success": False, "error": str(e), "steps": []}
    
    async def _generate_task_steps(self, task_description: str) -> List[str]:
        """Автоматическая генерация шагов для задачи"""
        try:
            prompt = f"""Разбей следующую задачу на логические шаги:
            
Задача: {task_description}

Создай пронумерованный список конкретных шагов для выполнения этой задачи.
Каждый шаг должен быть конкретным и выполнимым."""

            messages = [
                {"role": "system", "content": "Ты эксперт по планированию задач."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.openai_api.generate_response(messages)
            
            # Извлекаем шаги из ответа
            steps = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith(('-', '*'))):
                    # Очищаем от нумерации
                    clean_step = line.split('.', 1)[-1].strip()
                    if clean_step.startswith(('-', '*')):
                        clean_step = clean_step[1:].strip()
                    steps.append(clean_step)
            
            return steps[:10]  # Максимум 10 шагов
            
        except Exception as e:
            logger.error(f"Ошибка генерации шагов: {e}")
            return [task_description]  # Fallback
    
    def get_reasoning_stats(self) -> Dict:
        """Получение статистики рассуждений"""
        total_sessions = len(self.reasoning_sessions)
        active_sessions = sum(1 for s in self.reasoning_sessions.values() 
                            if "end_time" not in s)
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "tool_usage": self.tool_usage_stats.copy(),
            "models_used": {
                "o3": sum(1 for s in self.reasoning_sessions.values() 
                         if s.get("model") == "o3-2025-04-16"),
                "o4_mini": sum(1 for s in self.reasoning_sessions.values() 
                              if s.get("model") == "o4-mini-2025-04-16")
            }
        }
    
    async def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Очистка старых сессий"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        old_sessions = [
            session_id for session_id, session in self.reasoning_sessions.items()
            if session["start_time"].timestamp() < cutoff_time
        ]
        
        for session_id in old_sessions:
            del self.reasoning_sessions[session_id]
        
        logger.info(f"Очищено {len(old_sessions)} старых сессий рассуждения")


# Глобальный экземпляр движка рассуждений
reasoning_engine = AgenticReasoningEngine(OPENAI_API_KEY) 