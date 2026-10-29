from app.db.redis import get_redis

# Redis 里的三类键：
#   RT:{jti}          -> user_id   （单个刷新令牌，带过期时间）
#   user_status:{id}  -> 0 / 1     （鉴权时以这里为准）
#   user_tokens:{id}  -> {jti...}  （反向索引，方便一次踢掉所有设备）


def _rt_key(jti: str) -> str:
    return f"RT:{jti}"


def _rt_used_key(jti: str) -> str:
    return f"RT_USED:{jti}"


# 原子消费：读到 owner 的同时删掉 RT，并标记「刚用过」，防止并发刷新全部通过
_CONSUME_RT_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if value then
    redis.call('DEL', KEYS[1])
    redis.call('SET', KEYS[2], '1', 'EX', ARGV[1])
end
return value
"""


def _status_key(user_id: int) -> str:
    return f"user_status:{user_id}"


def _tokens_key(user_id: int) -> str:
    return f"user_tokens:{user_id}"


class TokenRepository:
    """Redis 读写：刷新令牌、用户状态、反向索引"""

    @staticmethod
    async def save_refresh_token(user_id: int, jti: str, ttl_seconds: int) -> None:
        redis = get_redis()
        async with redis.pipeline(transaction=True) as pipe:
            pipe.set(_rt_key(jti), user_id, ex=ttl_seconds)
            pipe.sadd(_tokens_key(user_id), jti)
            pipe.expire(_tokens_key(user_id), ttl_seconds)
            await pipe.execute()

    @staticmethod
    async def get_refresh_owner(jti: str) -> int | None:
        value = await get_redis().get(_rt_key(jti))
        return int(value) if value is not None else None

    @staticmethod
    async def consume_refresh_token(jti: str, grace_seconds: int = 15) -> int | None:
        """原子地取出并删除 RT，同时留下短效「已使用」标记"""
        value = await get_redis().eval(
            _CONSUME_RT_SCRIPT,
            2,
            _rt_key(jti),
            _rt_used_key(jti),
            grace_seconds,
        )
        return int(value) if value is not None else None

    @staticmethod
    async def was_refresh_token_used(jti: str) -> bool:
        return bool(await get_redis().exists(_rt_used_key(jti)))

    @staticmethod
    async def revoke_refresh_token(user_id: int, jti: str) -> None:
        redis = get_redis()
        async with redis.pipeline(transaction=True) as pipe:
            pipe.delete(_rt_key(jti))
            pipe.srem(_tokens_key(user_id), jti)
            await pipe.execute()

    @staticmethod
    async def revoke_all_tokens(user_id: int) -> None:
        """踢人下线：把这个用户所有设备上的 RT 全部删掉"""
        redis = get_redis()
        jtis = await redis.smembers(_tokens_key(user_id))
        if jtis:
            await redis.delete(*[_rt_key(jti) for jti in jtis])
        await redis.delete(_tokens_key(user_id))

    @staticmethod
    async def set_user_status(user_id: int, status: int) -> None:
        await get_redis().set(_status_key(user_id), status)

    @staticmethod
    async def get_user_status(user_id: int) -> int | None:
        value = await get_redis().get(_status_key(user_id))
        return int(value) if value is not None else None

    @staticmethod
    async def clear_user_status(user_id: int) -> None:
        """用户被删除时清掉状态缓存"""
        await get_redis().delete(_status_key(user_id))
