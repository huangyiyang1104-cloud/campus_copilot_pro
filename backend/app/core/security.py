from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt

from app.core.config import settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _create_token(payload_extra: dict, expires: timedelta) -> str:
    """载荷统一带 sub / type / iat / exp，type 用来区分 AT 和 RT"""
    now = datetime.now(timezone.utc)
    payload = {
        **payload_extra,
        "iat": now,
        "exp": now + expires,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(
        {"sub": str(user_id), "type": ACCESS_TOKEN_TYPE},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int, jti: str | None = None) -> tuple[str, str]:
    """返回 (token, jti)。jti 是这次 RT 的唯一标识，Redis 用它做索引"""
    token_id = jti or str(uuid4())
    token = _create_token(
        {"sub": str(user_id), "type": REFRESH_TOKEN_TYPE, "jti": token_id},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return token, token_id


def decode_token(token: str, expected_type: str) -> dict:
    """验签 + 验过期 + 验类型，任何一项不通过都会抛 JWTError"""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != expected_type:
        raise JWTError(f"token type mismatch, expected {expected_type}")
    return payload
