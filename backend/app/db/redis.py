from redis.asyncio import Redis, from_url

from app.core.config import settings

_client: Redis | None = None


def get_redis() -> Redis:
    """Redis 连接是懒加载的，进程内复用同一个客户端"""
    global _client
    if _client is None:
        _client = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
