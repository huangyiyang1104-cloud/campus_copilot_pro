from datetime import datetime

from pydantic import BaseModel


class ConversationItem(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class MessageItem(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
