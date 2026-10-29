from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.conversation import ConversationItem, MessageItem
from app.services import conversation as conversation_service

router = APIRouter(prefix="/api/conversations", tags=["会话"])


@router.get("", response_model=list[ConversationItem], summary="我的会话列表")
async def list_conversations(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationItem]:
    return await conversation_service.list_conversations(session, current_user)


@router.post(
    "",
    response_model=ConversationItem,
    status_code=status.HTTP_201_CREATED,
    summary="新建会话",
)
async def create_conversation(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationItem:
    return await conversation_service.create_conversation(session, current_user)


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageItem],
    summary="会话消息",
)
async def list_messages(
    conversation_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageItem]:
    return await conversation_service.list_messages(session, current_user, conversation_id)


@router.delete("/{conversation_id}", summary="删除会话")
async def delete_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    await conversation_service.delete_conversation(session, current_user, conversation_id)
    return {"message": "会话已删除"}
