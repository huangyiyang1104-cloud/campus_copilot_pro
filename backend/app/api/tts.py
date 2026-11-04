import asyncio

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_current_user
from app.core.tts import SpeechError, synthesize_speech
from app.models.user import User
from app.schemas.tts import SpeechRequest

router = APIRouter(prefix="/api/tts", tags=["语音"])


@router.post("/speech", summary="一句文本合成语音")
async def speech(
    payload: SpeechRequest,
    _current_user: User = Depends(get_current_user),
) -> Response:
    try:
        audio, used_rvc = await asyncio.to_thread(
            synthesize_speech, payload.text, payload.tag
        )
    except SpeechError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "tts_failed", "message": str(exc)},
        ) from exc

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store",
            "X-RVC-Used": "1" if used_rvc else "0",
        },
    )
