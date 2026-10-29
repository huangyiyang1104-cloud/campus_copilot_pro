import asyncio

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.token import TokenRepository
from app.repositories.user import UserRepository
from app.schemas.users import UserCreate, UserUpdate


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def resolve_status(user: User) -> int:
    """鉴权以 Redis 为准；Redis 里没有（新用户 / Redis 重启）就回源 MySQL 并回填"""
    cached = await TokenRepository.get_user_status(user.id)
    if cached is not None:
        return cached

    await TokenRepository.set_user_status(user.id, user.status)
    return user.status


async def list_users(session: AsyncSession) -> list[User]:
    return await UserRepository.list_all(session)


async def get_user(session: AsyncSession, user_id: int) -> User:
    user = await UserRepository.get_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "user_not_found", "message": "用户不存在"},
        )
    return user


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    if await UserRepository.get_by_username(session, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "username_exists", "message": "账号已存在"},
        )

    user = User(
        username=payload.username,
        password=await asyncio.to_thread(hash_password, payload.password),
        name=payload.name,
        role=payload.role,
        email=payload.email,
        phone=payload.phone,
        avatar=payload.avatar,
        status=payload.status,
    )
    try:
        await UserRepository.create(session, user)
        await session.commit()
    except IntegrityError:
        # 并发创建同名账号时，唯一索引会在这里兜住
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "username_exists", "message": "账号已存在"},
        ) from None

    await TokenRepository.set_user_status(user.id, user.status)
    return user


async def update_user(session: AsyncSession, user: User, payload: UserUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)

    new_username = data.pop("username", None)
    if new_username and new_username != user.username:
        if await UserRepository.get_by_username(session, new_username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "username_exists", "message": "账号已存在"},
            )
        user.username = new_username

    password = data.pop("password", None)
    if password:
        user.password = await asyncio.to_thread(hash_password, password)

    new_status = data.pop("status", None)

    for field in ("name", "role", "email", "phone", "avatar"):
        if field in data:
            setattr(user, field, data[field])

    # 状态变了要走「双写 + 踢下线」的完整流程
    if new_status is not None and new_status != user.status:
        return await change_status(session, user, new_status)

    try:
        await UserRepository.save(session, user)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "username_exists", "message": "账号已存在"},
        ) from None
    return user


async def delete_user(session: AsyncSession, user: User) -> None:
    user_id = user.id
    await UserRepository.delete(session, user)
    await session.commit()

    # 数据库里删了，Redis 里的状态和 RT 也要清干净
    await TokenRepository.revoke_all_tokens(user_id)
    await TokenRepository.clear_user_status(user_id)


async def change_status(session: AsyncSession, user: User, new_status: int) -> User:
    """启用/禁用：MySQL 和 Redis 双写；禁用时顺手把该用户所有 RT 删干净"""
    user.status = new_status
    await UserRepository.save(session, user)
    await session.commit()

    await TokenRepository.set_user_status(user.id, new_status)

    if new_status != 1:
        await TokenRepository.revoke_all_tokens(user.id)

    return user
