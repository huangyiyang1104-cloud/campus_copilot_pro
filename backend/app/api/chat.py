from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest
from app.services import chat as chat_service

router = APIRouter(prefix="/api/chat", tags=["AI 对话"])


@router.post("/stream", summary="流式对话")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    return StreamingResponse(
        chat_service.stream_answer(current_user, payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
