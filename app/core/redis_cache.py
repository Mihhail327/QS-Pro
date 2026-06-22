import os
import json
import redis.asyncio as aioredis
from typing import Optional, List, Any

# Берем URL из docker-compose, или дефолтный для локальной разработки
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

async def get_cached_snippets(user_id: int, category: str) -> Optional[List[Any]]:
    """Пытаемся достать данные из кэша Redis."""
    key = f"snippets:{user_id}:{category}"
    data = await redis_client.get(key)
    return json.loads(data) if data else None

async def set_snippets_cache(user_id: int, category: str, data: List[Any], expire: int = 300):
    """Кладем данные в кэш с TTL 5 минут."""
    key = f"snippets:{user_id}:{category}"
    await redis_client.setex(key, expire, json.dumps(data))

async def invalidate_user_cache(user_id: int):
    """Очищаем кэш пользователя при изменении данных."""
    async for key in redis_client.scan_iter(f"snippets:{user_id}:*"):
        await redis_client.delete(key)