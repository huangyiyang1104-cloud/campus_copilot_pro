from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseMaterial(Base):
    """课程资料元数据 course_materials"""

    __tablename__ = "course_materials"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), comment="上传者用户ID")

    file_name: Mapped[str] = mapped_column(String(255), comment="原始文件名")
    file_type: Mapped[str] = mapped_column(String(50), comment="文件扩展名，如 pdf/docx/md")
    file_size: Mapped[int] = mapped_column(BigInteger, comment="文件大小（字节）")
    course_name: Mapped[str | None] = mapped_column(String(100), comment="所属课程名")

    oss_object_name: Mapped[str] = mapped_column(String(512), comment="OSS 中的唯一路径")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="切分后的片段总数")

    status: Mapped[int] = mapped_column(
        TINYINT, default=0, comment="0-待处理, 1-解析中, 2-已索引, 3-处理失败"
    )
    error_msg: Mapped[str | None] = mapped_column(String(512), comment="失败原因")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[int] = mapped_column(TINYINT(1), default=0, comment="0-正常, 1-已删除")
