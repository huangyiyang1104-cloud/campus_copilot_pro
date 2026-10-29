from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation


class ConversationRepository:
    """conversations 表的数据访问"""

    @staticmethod
    async def get_by_id_for_user(
        session: AsyncSession, conversation_id: int, user_id: int
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.is_deleted == 0,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_by_user(session: AsyncSession, user_id: int) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.is_deleted == 0)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        )
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def create(session: AsyncSession, conversation: Conversation) -> Conversation:
        session.add(conversation)
        await session.flush()
        return conversation
