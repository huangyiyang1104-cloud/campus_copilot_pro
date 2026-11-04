"""腾讯云 TTS + 本地 RVC 的语音合成适配器。

输入是带语气标签的句子，例如：

    [紧张地] 那个……我、我查一下。

处理流程：
  标签解析 -> 文本清洗 -> 腾讯云 TTS -> RVC 变声 -> WAV

标签不会进入 TTS 正文；RVC 不可用时降级返回 TTS 原声。
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import uuid
import wave
from dataclasses import dataclass

import httpx
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tts.v20190823 import models as tts_models
from tencentcloud.tts.v20190823 import tts_client

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_TTS_CHARS = 140


class SpeechError(RuntimeError):
    """TTS 合成失败，接口层转成 502"""


@dataclass(frozen=True)
class SpeechStyle:
    emotion: str = "neutral"
    intensity: int = 100
    speed: float = 0.0
    volume: float = 0.0


# 601009 / 601010 支持这些情感；其他音色可能需要退回 neutral
TAG_STYLES: dict[str, SpeechStyle] = {
    "小声": SpeechStyle("neutral", 90, -0.2, -4),
    "紧张": SpeechStyle("fear", 75, 0.1, 0),
    "紧张地": SpeechStyle("fear", 75, 0.1, 0),
    "害怕": SpeechStyle("fear", 85, 0.1, 0),
    "鼓起勇气": SpeechStyle("neutral", 110, -0.1, 1),
    "认真": SpeechStyle("peaceful", 100, -0.1, 0),
    "认真地": SpeechStyle("peaceful", 100, -0.1, 0),
    "难过": SpeechStyle("sad", 100, -0.1, 0),
    "开心": SpeechStyle("happy", 100, 0.1, 0),
    "害羞": SpeechStyle("sajiao", 100, -0.1, -2),
    "平静": SpeechStyle("peaceful", 100, 0, 0),
    "生气": SpeechStyle("angry", 100, 0.1, 1),
}

# 模型偶尔会加“地/地说”，统一成固定标签
_TAG_ALIASES = {
    "小声地": "小声",
    "紧张地说": "紧张地",
    "害怕地": "害怕",
    "认真地说": "认真地",
    "平静地": "平静",
    "开心地": "开心",
    "难过地": "难过",
    "害羞地": "害羞",
    "鼓起勇气说": "鼓起勇气",
}
for _alias, _target in _TAG_ALIASES.items():
    TAG_STYLES.setdefault(_alias, TAG_STYLES[_target])

_TAG_RE = re.compile(r"^\s*\[([^\]]+)\]\s*")
_ANY_TAG_RE = re.compile(r"\[[^\]]+\]")
_ACTION_RE = re.compile(r"（[^）]*）|\([^)]*\)")
_URL_RE = re.compile(r"https?://\S+")
_MARKDOWN_RE = re.compile(r"```.*?```|[*_#>~`]", re.DOTALL)
_SENTENCE_RE = re.compile(r"[^。！？!?；;…\n]+[。！？!?；;…]*")
_TAG_WORD_RE = re.compile(
    "(?:[\\[【])?(?:" + "|".join(map(re.escape, TAG_STYLES)) + ")[\\]】]"
)


def _style_for(tag: str | None, text: str) -> SpeechStyle:
    if tag:
        normalized = tag.strip()
        if normalized in TAG_STYLES:
            return TAG_STYLES[normalized]
    for name, style in TAG_STYLES.items():
        if f"[{name}]" in text:
            return style
    return TAG_STYLES["平静"]


def clean_text(text: str) -> str:
    """去掉动作括号、Markdown 标记、链接和标签，只留可朗读正文"""
    text = _ACTION_RE.sub("", text)
    text = _ANY_TAG_RE.sub("", text)
    text = _TAG_WORD_RE.sub("", text)
    text = _URL_RE.sub("", text)
    text = _MARKDOWN_RE.sub("", text)
    text = text.replace("**", "").replace("__", "")
    text = text.lstrip("[]【】 ")
    return re.sub(r"\s+", " ", text).strip()


def split_for_tts(text: str, limit: int = MAX_TTS_CHARS) -> list[str]:
    """按句号优先切到 <= limit 字，避免腾讯云 150 字上限"""
    sentences = [item.strip() for item in _SENTENCE_RE.findall(text) if item.strip()]
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > limit:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(sentence), limit):
                chunks.append(sentence[start : start + limit])
            continue

        if len(current) + len(sentence) <= limit:
            current += sentence
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)
    return chunks


def _client():
    if not settings.TENCENT_SECRET_ID or not settings.TENCENT_SECRET_KEY:
        raise SpeechError("没有配置腾讯云 TTS 密钥")

    http_profile = HttpProfile()
    http_profile.endpoint = "tts.tencentcloudapi.com"
    http_profile.reqTimeout = 30

    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    return tts_client.TtsClient(
        credential.Credential(settings.TENCENT_SECRET_ID, settings.TENCENT_SECRET_KEY),
        settings.TENCENT_TTS_REGION,
        client_profile,
    )


def _synthesize_chunk(text: str, style: SpeechStyle) -> bytes:
    payload = {
        "Text": text,
        "SessionId": uuid.uuid4().hex,
        "VoiceType": settings.TENCENT_TTS_VOICE_TYPE,
        "Codec": settings.TENCENT_TTS_CODEC,
        "SampleRate": settings.TENCENT_TTS_SAMPLE_RATE,
        "Speed": style.speed,
        "Volume": style.volume,
        "EmotionCategory": style.emotion,
        "EmotionIntensity": style.intensity,
    }

    def call(body: dict) -> bytes:
        request = tts_models.TextToVoiceRequest()
        request.from_json_string(json.dumps(body, ensure_ascii=False))
        response = _client().TextToVoice(request)
        result = json.loads(response.to_json_string())
        audio = result.get("Audio")
        if not audio:
            raise SpeechError("腾讯云 TTS 返回空音频")
        return base64.b64decode(audio)

    try:
        return call(payload)
    except Exception as exc:
        # 有些音色不支持 EmotionCategory，去掉情感参数再试一次
        if style.emotion != "neutral":
            logger.warning("情感参数失败，退回 neutral：%s", str(exc)[:160])
            payload["EmotionCategory"] = "neutral"
            payload["EmotionIntensity"] = 100
            try:
                return call(payload)
            except Exception as retry_exc:
                raise SpeechError(f"TTS 合成失败：{retry_exc}") from retry_exc
        raise SpeechError(f"TTS 合成失败：{exc}") from exc


def _concat_wav(parts: list[bytes]) -> bytes:
    if len(parts) == 1:
        return parts[0]

    output = io.BytesIO()
    with wave.open(io.BytesIO(parts[0]), "rb") as first:
        params = first.getparams()

    with wave.open(output, "wb") as writer:
        writer.setparams(params)
        for part in parts:
            with wave.open(io.BytesIO(part), "rb") as reader:
                if reader.getparams()[:3] != params[:3]:
                    raise SpeechError("TTS 分段音频参数不一致，无法拼接")
                writer.writeframes(reader.readframes(reader.getnframes()))

    return output.getvalue()


def _apply_rvc(wav: bytes) -> tuple[bytes, bool]:
    if not settings.RVC_ENABLED:
        return wav, False

    url = f"{settings.RVC_SERVICE_URL.rstrip('/')}/convert"
    try:
        with httpx.Client(timeout=settings.RVC_TIMEOUT_SECONDS) as client:
            response = client.post(
                url,
                content=wav,
                headers={"Content-Type": "audio/wav"},
            )
        if response.status_code == 200 and response.content:
            return response.content, True
        logger.warning("RVC 返回异常：HTTP %s", response.status_code)
    except Exception as exc:
        logger.warning("RVC 服务不可用，使用 TTS 原声：%s", str(exc)[:160])

    return wav, False


def synthesize_speech(text: str, tag: str | None = None) -> tuple[bytes, bool]:
    """返回 (WAV 字节, 是否经过 RVC)。失败抛 SpeechError。"""
    if not settings.TTS_ENABLED:
        raise SpeechError("语音合成未启用")

    match = _TAG_RE.match(text or "")
    parsed_tag = match.group(1) if match else None
    body = (text or "")[match.end() :] if match else (text or "")
    body = clean_text(body)

    if not body:
        raise SpeechError("没有可朗读的文本")

    style = _style_for(tag or parsed_tag, text)
    chunks = split_for_tts(body)
    if not chunks:
        raise SpeechError("没有可朗读的文本")

    audio_parts = [_synthesize_chunk(chunk, style) for chunk in chunks]
    wav = _concat_wav(audio_parts)
    return _apply_rvc(wav)
