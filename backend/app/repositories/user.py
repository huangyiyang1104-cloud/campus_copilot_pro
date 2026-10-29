from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """users 表的数据访问。

    这里只负责 SQL，事务的 commit / rollback 交给调用方（service 或接口层）。
    """

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
        return await session.get(User, user_id)

    @staticmethod
    async def get_by_username(session: AsyncSession, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_all(session: AsyncSession) -> list[User]:
        stmt = select(User).order_by(User.id)
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def create(session: AsyncSession, user: User) -> User:
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def save(session: AsyncSession, user: User) -> User:
        """字段改完后调用，把变更刷到数据库"""
        await session.flush()
        return user

    @staticmethod
    async def delete(session: AsyncSession, user: User) -> None:
        await session.delete(user)
        await session.flush()
