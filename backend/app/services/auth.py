import asyncio
from dataclasses import dataclass

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from app.repositories.token import TokenRepository
from app.repositories.user import UserRepository


@dataclass
class IssuedTokens:
    """登录 / 刷新成功后拿到的用户和双 Token"""

    user: User
    access_token: str
    refresh_token: str


async def issue_tokens(user: User) -> IssuedTokens:
    """签发 AT + RT，并把 RT 的 jti 写进 Redis"""
    access_token = create_access_token(user.id)
    refresh_token, jti = create_refresh_token(user.id)

    await TokenRepository.save_refresh_token(
        user.id, jti, settings.REFRESH_TOKEN_EXPIRE_SECONDS
    )
    await TokenRepository.set_user_status(user.id, user.status)

    return IssuedTokens(user=user, access_token=access_token, refresh_token=refresh_token)


async def login(session: AsyncSession, username: str, password: str) -> IssuedTokens:
    """校验账号密码和状态，通过后签发 AT / RT"""
    user = await UserRepository.get_by_username(session, username)

    # 用户不存在和密码错误返回同一句提示，避免账号枚举
    # bcrypt 是同步且耗 CPU 的，丢到线程池，避免阻塞事件循环
    matched = user is not None and await asyncio.to_thread(
        bcrypt.checkpw,
        password.encode("utf-8"),
        user.password.encode("utf-8"),
    )
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 密码正确后再判断是否被管理员禁用，避免外人借此判断账号状态
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "account_disabled", "message": "账号已被禁用，请联系管理员"},
        )

    return await issue_tokens(user)


async def refresh(session: AsyncSession, user_id: int, jti: str) -> IssuedTokens:
    """RT 轮换：旧 jti 用过即作废，换一对新 Token"""
    owner = await TokenRepository.consume_refresh_token(jti)

    # Redis 里查不到这条 RT：已被踢下线 / 是伪造的 / 是过期的重复使用
    if owner is None or owner != user_id:
        # 刚被并发请求消费掉的，只拒绝这一次，不要把别人刚换到的新 RT 一起踢掉
        if owner is not None or not await TokenRepository.was_refresh_token_used(jti):
            await TokenRepository.revoke_all_tokens(user_id)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "refresh_token_reused", "message": "登录状态已失效，请重新登录"},
        )

    user = await UserRepository.get_by_id(session, user_id)
    if user is None:
        await TokenRepository.revoke_all_tokens(user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_refresh_token", "message": "登录状态异常，请重新登录"},
        )

    if user.status != 1:
        await TokenRepository.set_user_status(user.id, 0)
        await TokenRepository.revoke_all_tokens(user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "account_disabled", "message": "账号已被禁用，请联系管理员"},
        )

    # consume_refresh_token 已经原子删除旧 RT，这里直接签发新的
    return await issue_tokens(user)


async def logout(user_id: int, jti: str) -> None:
    """退出登录：只作废当前设备这一个 RT"""
    await TokenRepository.revoke_refresh_token(user_id, jti)
