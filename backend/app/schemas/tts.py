from pydantic import BaseModel, Field


class SpeechRequest(BaseModel):
    """一句待朗读文本；tag 可以由前端单独传，也可以写在 text 开头"""

    text: str = Field(min_length=1, max_length=1000)
    tag: str | None = Field(default=None, max_length=100)
