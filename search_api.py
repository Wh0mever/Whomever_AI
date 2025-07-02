import aiohttp
import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
import re
from bs4 import BeautifulSoup
from config import SEARCH_SETTINGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchAPI:
    def __init__(self):
        self.timeout = SEARCH_SETTINGS.get('timeout', 10)
        self.max_results = SEARCH_SETTINGS.get('max_results', 5)
        self.user_agent = SEARCH_SETTINGS.get('user_agent', 'WHOMEVER AI Bot 2.0')
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    async def search(self, query: str, engine: str = 'duckduckgo', **kwargs) -> List[Dict]:
        """Поиск с использованием различных поисковых движков"""
        try:
            if engine == 'duckduckgo':
                return await self._duckduckgo_search(query)
            elif engine == 'google':
                return await self._google_search(query)
            else:
                logger.warning(f"Неподдерживаемый поисковый движок: {engine}")
                return await self._duckduckgo_search(query)  # Fallback
        except Exception as e:
            logger.error(f"Ошибка поиска через {engine}: {str(e)}")
            # Пробуем альтернативный движок
            if engine != 'duckduckgo':
                return await self._duckduckgo_search(query)
            return []

    async def _duckduckgo_search(self, query: str) -> List[Dict]:
        """Поиск через DuckDuckGo Instant Answer API"""
        try:
            # Сначала пробуем Instant Answer API
            instant_results = await self._duckduckgo_instant(query)
            if instant_results:
                return instant_results
            
            # Если нет мгновенных ответов, парсим веб-результаты
            return await self._duckduckgo_web_search(query)
            
        except Exception as e:
            logger.error(f"Ошибка DuckDuckGo поиска: {str(e)}")
            return []

    async def _duckduckgo_instant(self, query: str) -> List[Dict]:
        """DuckDuckGo Instant Answer API"""
        try:
            url = f"https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_redirect': '1',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout, headers=self.headers) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = []
                        
                        # Добавляем абстракт если есть
                        if data.get('Abstract'):
                            results.append({
                                'title': data.get('Heading', query),
                                'url': data.get('AbstractURL', ''),
                                'description': data.get('Abstract', ''),
                                'source': 'DuckDuckGo Instant'
                            })
                        
                        # Добавляем связанные темы
                        for topic in data.get('RelatedTopics', [])[:3]:
                            if isinstance(topic, dict) and 'Text' in topic:
                                results.append({
                                    'title': topic.get('Text', '')[:100],
                                    'url': topic.get('FirstURL', ''),
                                    'description': topic.get('Text', ''),
                                    'source': 'DuckDuckGo Related'
                                })
                        
                        return results[:self.max_results]
                        
        except Exception as e:
            logger.error(f"Ошибка DuckDuckGo Instant API: {str(e)}")
        
        return []

    async def _duckduckgo_web_search(self, query: str) -> List[Dict]:
        """Веб-поиск через DuckDuckGo (парсинг результатов)"""
        try:
            # Первый запрос для получения токена
            url = "https://html.duckduckgo.com/html/"
            params = {'q': query}
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout, headers=self.headers) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_duckduckgo_results(html)
                        
        except Exception as e:
            logger.error(f"Ошибка DuckDuckGo веб-поиска: {str(e)}")
        
        return []

    def _parse_duckduckgo_results(self, html: str) -> List[Dict]:
        """Парсинг результатов DuckDuckGo"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            results = []
            
            # Находим результаты поиска
            result_divs = soup.find_all('div', class_='result')
            
            for div in result_divs[:self.max_results]:
                try:
                    # Заголовок и ссылка
                    title_link = div.find('a', class_='result__a')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    url = title_link.get('href', '')
                    
                    # Описание
                    snippet_div = div.find('a', class_='result__snippet')
                    description = snippet_div.get_text(strip=True) if snippet_div else ''
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'description': description,
                            'source': 'DuckDuckGo Web'
                        })
                        
                except Exception as e:
                    logger.debug(f"Ошибка парсинга результата: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка парсинга DuckDuckGo: {str(e)}")
            return []

    async def _google_search(self, query: str) -> List[Dict]:
        """Простой поиск через Google (без API ключа)"""
        try:
            # Используем Google Custom Search без ключа (ограниченно)
            url = "https://www.google.com/search"
            params = {
                'q': query,
                'num': self.max_results,
                'hl': 'ru',
                'lr': 'lang_ru'
            }
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout, headers=self.headers) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_google_results(html)
                        
        except Exception as e:
            logger.error(f"Ошибка Google поиска: {str(e)}")
        
        return []

    def _parse_google_results(self, html: str) -> List[Dict]:
        """Парсинг результатов Google"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            results = []
            
            # Ищем div'ы с результатами
            search_results = soup.find_all('div', class_='g')
            
            for result in search_results[:self.max_results]:
                try:
                    # Заголовок и ссылка
                    title_elem = result.find('h3')
                    if not title_elem:
                        continue
                    
                    link_elem = result.find('a')
                    if not link_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = link_elem.get('href', '')
                    
                    # Убираем Google редирект
                    if url.startswith('/url?'):
                        url_match = re.search(r'url=([^&]+)', url)
                        if url_match:
                            url = url_match.group(1)
                    
                    # Описание
                    snippet_spans = result.find_all('span')
                    description = ''
                    for span in snippet_spans:
                        text = span.get_text(strip=True)
                        if len(text) > 50:  # Вероятно это описание
                            description = text
                            break
                    
                    if title and url and url.startswith('http'):
                        results.append({
                            'title': title,
                            'url': url,
                            'description': description,
                            'source': 'Google'
                        })
                        
                except Exception as e:
                    logger.debug(f"Ошибка парсинга Google результата: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка парсинга Google: {str(e)}")
            return []

    async def get_suggestions(self, query: str) -> List[Dict]:
        """Получение поисковых подсказок"""
        try:
            # Используем Google Suggest API
            url = "http://suggestqueries.google.com/complete/search"
            params = {
                'client': 'firefox',
                'q': query,
                'hl': 'ru'
            }
            
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        suggestions = []
                        
                        if len(data) > 1 and isinstance(data[1], list):
                            for suggestion in data[1][:5]:
                                suggestions.append({
                                    'keyword': suggestion,
                                    'source': 'Google Suggest'
                                })
                        
                        return suggestions
                        
        except Exception as e:
            logger.error(f"Ошибка получения подсказок: {str(e)}")
        
        return []

    async def get_news(self, query: str) -> List[Dict]:
        """Получение новостей по запросу"""
        try:
            # Поиск новостей через DuckDuckGo с модификатором
            news_query = f"{query} новости"
            return await self.search(news_query, engine='duckduckgo')
        except Exception as e:
            logger.error(f"Ошибка поиска новостей: {str(e)}")
            return []

    def is_available(self) -> bool:
        """Проверка доступности поискового API"""
        return True  # Всегда доступен, так как не требует API ключей 