from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Conversation(Base):
    """会话 conversations"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), comment="归属用户")

    title: Mapped[str] = mapped_column(String(100), default="新对话", comment="会话标题")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="早期消息摘要")
    summary_upto_message_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True), nullable=True, comment="摘要覆盖到哪条消息"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[int] = mapped_column(TINYINT(1), default=0, comment="0-正常, 1-已删除")
