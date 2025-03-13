import requests
import logging
from config import DEEPSEEKCHAT_API_KEY

logger = logging.getLogger(__name__)

class DeepseekAPI:
    def __init__(self):
        self.api_key = DEEPSEEKCHAT_API_KEY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegram-bot.com",  # Замените на ваш URL
            "X-Title": "Telegram AI Assistant"  # Название вашего приложения
        }
        logger.info("DeepseekAPI инициализирован")

    def generate_response(self, message: str, character: str = None, style: str = None, depth: str = None):
        # Формируем системный промпт на основе настроек
        system_prompt = self._create_system_prompt(character, style, depth)
        
        logger.info(f"Отправка запроса к API с промптом: {system_prompt[:50]}...")
        
        try:
            payload = {
                "model": "deepseek/deepseek-r1:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            }
            
            logger.info(f"Отправка запроса к {self.base_url}")
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60  # Увеличиваем таймаут до 60 секунд
            )
            
            logger.info(f"Получен ответ от API: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info("Успешно получен ответ от API")
                return result['choices'][0]['message']['content']
            else:
                error_msg = f"Ошибка API: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"Произошла ошибка: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _create_system_prompt(self, character: str = None, style: str = None, depth: str = None):
        prompt_parts = []
        
        # Базовый промпт
        prompt_parts.append("Вы - интеллектуальный ассистент, который помогает пользователям.")
        
        # Добавляем характер персонажа
        if character:
            prompt_parts.append(f"Вы выступаете в роли специалиста: {character}.")
            prompt_parts.append("Используйте соответствующую терминологию и профессиональный подход.")
        
        # Добавляем стиль общения
        if style == 'formal':
            prompt_parts.append("Общайтесь формально и профессионально.")
        elif style == 'informal':
            prompt_parts.append("Общайтесь неформально и дружелюбно.")
        elif style == 'friendly':
            prompt_parts.append("Будьте максимально дружелюбны и открыты.")
        
        # Добавляем глубину анализа
        if depth == 'brief':
            prompt_parts.append("Давайте краткие, но информативные ответы.")
        elif depth == 'detailed':
            prompt_parts.append("Предоставляйте подробные объяснения с примерами.")
        elif depth == 'expert':
            prompt_parts.append("Давайте экспертный анализ с техническими деталями.")
        
        # Добавляем указание отвечать на русском языке
        prompt_parts.append("Всегда отвечайте на русском языке.")
        
        return " ".join(prompt_parts) 