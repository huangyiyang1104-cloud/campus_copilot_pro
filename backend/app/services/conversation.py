from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.schemas.conversation import ConversationItem, MessageItem


def _to_item(conversation: Conversation) -> ConversationItem:
    return ConversationItem(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


async def list_conversations(session: AsyncSession, user: User) -> list[ConversationItem]:
    conversations = await ConversationRepository.list_by_user(session, user.id)
    return [_to_item(conversation) for conversation in conversations]


async def create_conversation(session: AsyncSession, user: User) -> ConversationItem:
    conversation = Conversation(user_id=user.id, title="新对话")
    await ConversationRepository.create(session, conversation)
    await session.commit()
    await session.refresh(conversation)
    return _to_item(conversation)


async def list_messages(
    session: AsyncSession, user: User, conversation_id: int
) -> list[MessageItem]:
    conversation = await ConversationRepository.get_by_id_for_user(
        session, conversation_id, user.id
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "conversation_not_found", "message": "会话不存在"},
        )

    messages = await MessageRepository.list_by_conversation(session, conversation_id)
    return [
        MessageItem(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )
        for message in messages
    ]


async def delete_conversation(
    session: AsyncSession, user: User, conversation_id: int
) -> None:
    conversation = await ConversationRepository.get_by_id_for_user(
        session, conversation_id, user.id
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "conversation_not_found", "message": "会话不存在"},
        )

    await MessageRepository.delete_by_conversation(session, conversation_id)
    conversation.is_deleted = 1
    await session.commit()
