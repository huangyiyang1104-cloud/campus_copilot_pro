from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    """messages 表的数据访问"""

    @staticmethod
    async def list_recent(
        session: AsyncSession, conversation_id: int, limit: int = 40
    ) -> list[Message]:
        """取最近 N 条，再按时间正序返回，避免长会话无限塞进上下文"""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        rows = list((await session.execute(stmt)).scalars().all())
        return list(reversed(rows))

    @staticmethod
    async def list_by_conversation(
        session: AsyncSession, conversation_id: int
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def create(session: AsyncSession, message: Message) -> Message:
        session.add(message)
        await session.flush()
        return message

    @staticmethod
    async def delete_by_conversation(session: AsyncSession, conversation_id: int) -> None:
        await session.execute(
            delete(Message).where(Message.conversation_id == conversation_id)
        )
