import aiohttp
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Union
import json
import logging
from datetime import datetime
import time
from sklearn.metrics.pairwise import cosine_similarity
from config import OPENAI_API_KEY
import re
import hashlib

logger = logging.getLogger(__name__)

class SemanticSearchAPI:
    """
    Продвинутый семантический поиск с embeddings как у Perplexity AI
    
    Особенности:
    - text-embedding-3-large для максимальной точности
    - Семантическое понимание контекста
    - Ранжирование по релевантности  
    - Кэширование embeddings
    - Автоматический выбор лучших источников
    """
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Настройки embeddings
        self.embedding_model = "text-embedding-3-large"  # Максимальная точность
        self.embedding_dimensions = 3072  # Полная размерность
        self.max_tokens_per_chunk = 8000  # Оптимальный размер чанка
        
        # Кэш для embeddings
        self.embedding_cache = {}
        self.cache_max_size = 1000
        
        # Источники для поиска
        self.search_sources = {
            'web_general': {
                'url': 'https://duckduckgo.com/html/',
                'weight': 1.0,
                'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            },
            'news': {
                'url': 'https://duckduckgo.com/html/',
                'params': {'iar': 'news'},
                'weight': 1.2,  # Новости важнее для актуальных запросов
                'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            }
        }
        
        logger.info("🧠 Semantic Search API инициализирован с text-embedding-3-large")

    async def get_embedding(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        """Получение embedding для текста с кэшированием"""
        try:
            if use_cache:
                text_hash = hashlib.md5(text.encode()).hexdigest()
                if text_hash in self.embedding_cache:
                    return self.embedding_cache[text_hash]
            
            clean_text = self._clean_text_for_embedding(text)
            if not clean_text.strip():
                return None
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json={
                        "model": self.embedding_model,
                        "input": clean_text,
                        "dimensions": self.embedding_dimensions
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        embedding = data['data'][0]['embedding']
                        
                        if use_cache:
                            self._add_to_cache(text_hash, embedding)
                        
                        return embedding
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка получения embedding: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка при получении embedding: {e}")
            return None

    def _clean_text_for_embedding(self, text: str) -> str:
        """Очистка текста для embedding"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\-.,!?:;()\"\'`]', '', text)
        text = text.strip()
        
        max_chars = self.max_tokens_per_chunk * 4
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        return text

    def _add_to_cache(self, key: str, embedding: List[float]):
        """Добавление embedding в кэш с ограничением размера"""
        if len(self.embedding_cache) >= self.cache_max_size:
            oldest_key = next(iter(self.embedding_cache))
            del self.embedding_cache[oldest_key]
        
        self.embedding_cache[key] = embedding

    async def semantic_search(self, query: str, max_results: int = 8, include_news: bool = True) -> List[Dict[str, Any]]:
        """Семантический поиск в реальном времени"""
        try:
            logger.info(f"🔍 Начинаю семантический поиск: '{query}'")
            
            query_embedding = await self.get_embedding(query)
            if not query_embedding:
                logger.error("Не удалось получить embedding для запроса")
                return []
            
            search_strategy = self._analyze_query_type(query)
            
            search_tasks = []
            search_tasks.append(self._search_web_source('web_general', query, max_results))
            
            if include_news and search_strategy.get('needs_current_info', False):
                search_tasks.append(self._search_web_source('news', query, max_results // 2))
            
            all_search_results = []
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            for results in search_results:
                if isinstance(results, list):
                    all_search_results.extend(results)
                elif isinstance(results, Exception):
                    logger.warning(f"Ошибка в одном из источников: {results}")
            
            if not all_search_results:
                logger.warning("Не получено результатов поиска")
                return []
            
            enhanced_results = await self._calculate_semantic_relevance(
                all_search_results, query_embedding, query
            )
            
            enhanced_results.sort(key=lambda x: x.get('semantic_score', 0), reverse=True)
            
            unique_results = []
            seen_urls = set()
            for result in enhanced_results:
                url = result.get('url', '')
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
                
                if len(unique_results) >= max_results:
                    break
            
            logger.info(f"✅ Найдено {len(unique_results)} семантически релевантных результатов")
            return unique_results
            
        except Exception as e:
            logger.error(f"Ошибка семантического поиска: {e}")
            return []

    def _analyze_query_type(self, query: str) -> Dict[str, Any]:
        """Анализ типа запроса для определения стратегии поиска"""
        query_lower = query.lower()
        
        current_indicators = [
            'сейчас', 'сегодня', 'вчера', 'завтра', 'актуально', 'последние',
            'новости', 'текущий', 'свежий', 'недавно', 'этот год', '2025',
            'что происходит', 'что случилось', 'цена', 'курс', 'стоимость'
        ]
        
        return {
            'needs_current_info': any(indicator in query_lower for indicator in current_indicators),
            'query_type': 'current_info' if any(indicator in query_lower for indicator in current_indicators) else 'general'
        }

    async def _search_web_source(self, source_name: str, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Поиск в конкретном веб-источнике"""
        try:
            source_config = self.search_sources.get(source_name, self.search_sources['web_general'])
            
            params = {
                'q': query,
                'kl': 'wt-wt',
                'safe': 'moderate'
            }
            
            if 'params' in source_config:
                params.update(source_config['params'])
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    source_config['url'],
                    params=params,
                    headers=source_config.get('headers', {}),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        html = await response.text()
                        results = self._parse_search_results(html, source_name)
                        
                        for result in results:
                            result['source_weight'] = source_config.get('weight', 1.0)
                            result['source_type'] = source_name
                        
                        return results[:max_results]
                    else:
                        logger.warning(f"Источник {source_name} вернул код {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Ошибка поиска в источнике {source_name}: {e}")
            return []

    def _parse_search_results(self, html: str, source_type: str) -> List[Dict[str, Any]]:
        """Парсинг результатов поиска из HTML"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            results = []
            
            result_divs = soup.find_all('div', class_='result')
            
            for div in result_divs:
                try:
                    title_link = div.find('a', class_='result__a')
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    url = title_link.get('href', '')
                    
                    snippet_div = div.find('a', class_='result__snippet')
                    description = snippet_div.get_text(strip=True) if snippet_div else ''
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'description': description,
                            'source': f'DuckDuckGo {source_type.title()}',
                            'timestamp': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.debug(f"Ошибка парсинга результата: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка парсинга HTML: {e}")
            return []

    async def _calculate_semantic_relevance(self, search_results: List[Dict], 
                                          query_embedding: List[float], query: str) -> List[Dict]:
        """Вычисление семантической релевантности результатов"""
        try:
            enhanced_results = []
            
            embedding_tasks = []
            for result in search_results:
                combined_text = f"{result.get('title', '')} {result.get('description', '')}"
                embedding_tasks.append(self.get_embedding(combined_text))
            
            result_embeddings = await asyncio.gather(*embedding_tasks, return_exceptions=True)
            
            for i, (result, embedding) in enumerate(zip(search_results, result_embeddings)):
                if isinstance(embedding, list) and len(embedding) > 0:
                    similarity = cosine_similarity(
                        [query_embedding], 
                        [embedding]
                    )[0][0]
                    
                    source_weight = result.get('source_weight', 1.0)
                    semantic_score = similarity * source_weight
                    
                    result['semantic_score'] = float(semantic_score)
                    result['cosine_similarity'] = float(similarity)
                    enhanced_results.append(result)
                    
                else:
                    result['semantic_score'] = 0.1
                    result['cosine_similarity'] = 0.0
                    enhanced_results.append(result)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Ошибка вычисления семантической релевантности: {e}")
            for result in search_results:
                result['semantic_score'] = 0.5
                result['cosine_similarity'] = 0.0
            return search_results

    async def get_search_suggestions(self, query: str) -> List[str]:
        """Получение поисковых предложений на основе семантического анализа"""
        try:
            # Анализируем запрос и предлагаем улучшения
            query_analysis = self._analyze_query_type(query)
            
            suggestions = []
            
            # Базовые улучшения
            if len(query.split()) < 3:
                suggestions.append(f"{query} подробно")
                suggestions.append(f"{query} как работает")
            
            # Контекстные предложения
            if query_analysis['query_type'] == 'current_info':
                suggestions.extend([
                    f"{query} последние новости",
                    f"{query} актуальная информация 2025",
                    f"{query} что происходит сейчас"
                ])
            
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Ошибка получения предложений: {e}")
            return []

    def get_cache_stats(self) -> Dict[str, Any]:
        """Статистика использования кэша embeddings"""
        return {
            'cache_size': len(self.embedding_cache),
            'cache_max_size': self.cache_max_size,
            'cache_usage_percent': (len(self.embedding_cache) / self.cache_max_size) * 100
        }

    async def clear_cache(self):
        """Очистка кэша embeddings"""
        self.embedding_cache.clear()
        logger.info("🧹 Кэш embeddings очищен")

# Глобальный экземпляр для использования в боте
semantic_search_api = SemanticSearchAPI() 