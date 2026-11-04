"""基于 Redis 的轻量互斥锁，用于同一用户/资源的串行写操作。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import HTTPException, status

from app.db.redis import get_redis

logger = logging.getLogger(__name__)

_RELEASE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


@asynccontextmanager
async def redis_lock(
    key: str,
    *,
    ttl_seconds: int = 15,
    wait_seconds: float = 5.0,
) -> AsyncIterator[None]:
    """获取锁后执行临界区；超时返回 409，避免无限排队。"""
    redis = get_redis()
    token = uuid.uuid4().hex
    loop = asyncio.get_running_loop()
    deadline = loop.time() + wait_seconds

    while True:
        try:
            acquired = await redis.set(key, token, nx=True, ex=ttl_seconds)
        except Exception as exc:
            logger.exception("Redis 锁不可用 key=%s", key)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "lock_unavailable", "message": "服务繁忙，请稍后重试"},
            ) from exc

        if acquired:
            break
        if loop.time() >= deadline:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "busy", "message": "正在保存课表，请稍后重试"},
            )
        await asyncio.sleep(0.05)

    try:
        yield
    finally:
        try:
            await redis.eval(_RELEASE_SCRIPT, 1, key, token)
        except Exception:
            logger.exception("释放 Redis 锁失败 key=%s", key)
