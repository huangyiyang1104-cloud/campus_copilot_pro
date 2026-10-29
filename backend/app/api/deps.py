from fastapi import Depends, HTTPException, Request, status
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.users import resolve_status


def unauthorized(code: str, message: str) -> HTTPException:
    """统一的 401，响应体带 code，前端据此判断要不要刷新"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message},
    )


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> User:
    """全局鉴权依赖：校验 AT，并用 Redis 里的 user_status 判断是否被踢下线"""
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise unauthorized("missing_token", "未登录或登录已过期")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        payload = decode_token(token, ACCESS_TOKEN_TYPE)
    except ExpiredSignatureError as exc:
        raise unauthorized("token_expired", "访问令牌已过期") from exc
    except JWTError as exc:
        raise unauthorized("invalid_token", "访问令牌无效") from exc

    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError) as exc:
        raise unauthorized("invalid_token", "访问令牌无效") from exc

    user = await UserRepository.get_by_id(session, user_id)
    if user is None:
        raise unauthorized("invalid_token", "访问令牌无效")

    # 关键：状态以 Redis 为准，管理员一禁用，这里立刻拦住
    if await resolve_status(user) != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "account_disabled", "message": "账号已被禁用，请联系管理员"},
        )

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """管理员专用依赖"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "permission_denied", "message": "没有管理员权限"},
        )
    return current_user
