from fastapi import APIRouter, Depends, Request, Response
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, unauthorized
from app.core.config import settings
from app.core.security import REFRESH_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, TokenResponse, UserInfo
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["认证"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    """RT 只放 httpOnly Cookie，前端 JS 读不到"""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,  # 本地 http 调试用，上线 HTTPS 后改 True
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    issued = await auth_service.login(session, payload.username, payload.password)
    _set_refresh_cookie(response, issued.refresh_token)

    return LoginResponse(
        access_token=issued.access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserInfo.model_validate(issued.user),
    )


@router.post("/refresh", response_model=TokenResponse, summary="用 RT 换一对新 Token")
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise unauthorized("missing_refresh_token", "登录已过期，请重新登录")

    try:
        payload = decode_token(token, REFRESH_TOKEN_TYPE)
    except ExpiredSignatureError as exc:
        raise unauthorized("refresh_token_expired", "登录已过期，请重新登录") from exc
    except JWTError as exc:
        raise unauthorized("invalid_refresh_token", "登录状态异常，请重新登录") from exc

    try:
        user_id = int(payload.get("sub", ""))
        jti = str(payload["jti"])
    except (KeyError, TypeError, ValueError) as exc:
        raise unauthorized("invalid_refresh_token", "登录状态异常，请重新登录") from exc

    issued = await auth_service.refresh(session, user_id, jti)
    _set_refresh_cookie(response, issued.refresh_token)

    return TokenResponse(
        access_token=issued.access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", summary="退出登录")
async def logout(request: Request, response: Response) -> dict[str, str]:
    token = request.cookies.get(REFRESH_COOKIE_NAME)

    if token:
        try:
            payload = decode_token(token, REFRESH_TOKEN_TYPE)
            await auth_service.logout(int(payload["sub"]), str(payload["jti"]))
        except (JWTError, KeyError, TypeError, ValueError):
            # 令牌本身已失效，直接清 Cookie 即可
            pass

    _clear_refresh_cookie(response)
    return {"message": "已退出登录"}


@router.get("/me", response_model=UserInfo, summary="获取当前登录用户")
async def read_me(current_user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo.model_validate(current_user)
