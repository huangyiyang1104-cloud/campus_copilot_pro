from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """一轮对话请求"""

    conversation_id: int = Field(gt=0, description="会话 ID，由 /api/conversations 创建")
    message: str = Field(min_length=1, max_length=10000, description="用户这一轮发送的内容")
