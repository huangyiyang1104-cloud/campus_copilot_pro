import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.core.agent import get_agent
from app.db.session import AsyncSessionLocal
from app.models.message import Message
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)


def _sse(data: dict) -> str:
    """把一条事件包成 SSE 格式"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_answer(user: User, payload: ChatRequest) -> AsyncIterator[str]:
    """从 MySQL 取历史，调用 Agent，流式返回并落库"""
    agent = get_agent()
    title = "新对话"

    async with AsyncSessionLocal() as session:
        conversation = await ConversationRepository.get_by_id_for_user(
            session, payload.conversation_id, user.id
        )
        if conversation is None:
            yield _sse({"type": "error", "message": "会话不存在或已删除"})
            return

        history_rows = await MessageRepository.list_recent(session, conversation.id, 40)
        history: list[BaseMessage] = []
        for row in history_rows:
            if row.role == "user":
                history.append(HumanMessage(content=row.content))
            elif row.role == "assistant":
                history.append(AIMessage(content=row.content))

        await MessageRepository.create(
            session,
            Message(
                conversation_id=conversation.id,
                role="user",
                content=payload.message,
                token_count=0,
            ),
        )

        if conversation.title in ("", "新对话"):
            conversation.title = payload.message[:20]
        conversation.updated_at = datetime.now()
        title = conversation.title
        await session.commit()

    parts: list[str] = []

    try:
        async for delta in agent.astream(user.id, history, payload.message):
            parts.append(delta)
            yield _sse({"type": "delta", "content": delta})
    except Exception:
        logger.exception("Agent 流式回答失败")
        yield _sse({"type": "error", "message": "AI 服务暂时不可用，请稍后重试"})
        return

    if parts:
        try:
            async with AsyncSessionLocal() as session:
                await MessageRepository.create(
                    session,
                    Message(
                        conversation_id=payload.conversation_id,
                        role="assistant",
                        content="".join(parts),
                        token_count=0,
                    ),
                )
                conversation = await ConversationRepository.get_by_id_for_user(
                    session, payload.conversation_id, user.id
                )
                if conversation is not None:
                    conversation.updated_at = datetime.now()
                await session.commit()
        except Exception:
            # 回答已经发给用户了，落库失败只记日志，不把这次对话判成失败
            logger.exception("保存 AI 回答失败 conversation_id=%s", payload.conversation_id)

    yield _sse(
        {
            "type": "done",
            "conversation_id": payload.conversation_id,
            "title": title,
        }
    )
