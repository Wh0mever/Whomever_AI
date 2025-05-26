import aiohttp
import asyncio
import logging
import backoff
from typing import List, Dict, Any, Optional
from config import FETCHSERP_API_KEY, FETCHSERP_SETTINGS, SEARCH_SETTINGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchAPI:
    def __init__(self):
        self.api_key = FETCHSERP_API_KEY
        self.base_url = FETCHSERP_SETTINGS['base_url']
        self.headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}"
        }
        self.semaphore = asyncio.Semaphore(FETCHSERP_SETTINGS['rate_limit']['max_concurrent'])

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=FETCHSERP_SETTINGS['max_retries']
    )
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """Выполнение запроса к API с повторными попытками"""
        async with self.semaphore:
            timeout = aiohttp.ClientTimeout(total=FETCHSERP_SETTINGS['timeout'])
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}{endpoint}"
                async with session.get(url, params=params, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка API: {response.status} - {error_text}")
                        raise aiohttp.ClientError(f"Ошибка API: {response.status}")

    async def search(
        self,
        query: str,
        engine: str = SEARCH_SETTINGS['default_engine'],
        country: str = SEARCH_SETTINGS['default_country'],
        pages: int = 1
    ) -> List[Dict]:
        """Поиск по запросу"""
        params = {
            "search_engine": engine,
            "country": country,
            "pages_number": min(pages, SEARCH_SETTINGS['max_pages']),
            "query": query
        }
        
        try:
            data = await self._make_request(FETCHSERP_SETTINGS['endpoints']['search'], params)
            return self._format_search_results(data)
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")
            return []

    async def get_ranking(
        self,
        domain: str,
        query: str,
        engine: str = SEARCH_SETTINGS['default_engine'],
        country: str = SEARCH_SETTINGS['default_country']
    ) -> Optional[int]:
        """Получение позиции домена в выдаче"""
        params = {
            "search_engine": engine,
            "country": country,
            "domain": domain,
            "query": query
        }
        
        try:
            data = await self._make_request(FETCHSERP_SETTINGS['endpoints']['ranking'], params)
            return data.get('ranking')
        except Exception as e:
            logger.error(f"Ошибка при получении позиции: {str(e)}")
            return None

    async def get_web_pages(
        self,
        query: str,
        engine: str = SEARCH_SETTINGS['default_engine'],
        country: str = SEARCH_SETTINGS['default_country'],
        pages: int = 1
    ) -> List[Dict]:
        """Получение полного содержимого страниц из результатов поиска"""
        params = {
            "search_engine": engine,
            "country": country,
            "pages_number": min(pages, SEARCH_SETTINGS['max_pages']),
            "query": query
        }
        
        try:
            data = await self._make_request(FETCHSERP_SETTINGS['endpoints']['web_pages'], params)
            return data.get('results', [])
        except Exception as e:
            logger.error(f"Ошибка при получении страниц: {str(e)}")
            return []

    async def get_suggestions(
        self,
        query: str,
        country: str = SEARCH_SETTINGS['default_country'],
        url: Optional[str] = None
    ) -> List[Dict]:
        """Получение поисковых подсказок"""
        params = {
            "country": country,
            "keywords": [query]
        }
        if url:
            params["url"] = url
            
        try:
            data = await self._make_request(FETCHSERP_SETTINGS['endpoints']['suggestions'], params)
            return data.get('keywords_suggestions', [])
        except Exception as e:
            logger.error(f"Ошибка при получении подсказок: {str(e)}")
            return []

    def _format_search_results(self, data: Dict) -> List[Dict]:
        """Форматирование результатов поиска"""
        results = []
        for item in data:
            result = {
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'description': item.get('description', ''),
                'position': item.get('ranking', 0)
            }
            results.append(result)
        return results

    def _format_web_page_results(self, data: Dict) -> List[Dict]:
        """Форматирование результатов с содержимым страниц"""
        results = []
        for item in data.get('results', []):
            result = {
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'description': item.get('description', ''),
                'content': item.get('content', ''),
                'position': item.get('ranking', 0)
            }
            results.append(result)
        return results 