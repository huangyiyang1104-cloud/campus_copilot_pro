from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Course(Base):
    """学生课表 courses"""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), comment="所属用户ID")

    course_name: Mapped[str] = mapped_column(String(100), comment="课程名称")
    teacher: Mapped[str | None] = mapped_column(String(50), comment="任课教师")
    classroom: Mapped[str | None] = mapped_column(String(100), comment="上课地点")

    day_of_week: Mapped[int] = mapped_column(TINYINT, comment="星期几：1-周一 ... 5-周五")
    start_section: Mapped[int] = mapped_column(TINYINT, comment="开始节次")
    end_section: Mapped[int] = mapped_column(TINYINT, comment="结束节次")
    semester: Mapped[str] = mapped_column(String(50), comment="学期，如 2026-2027-1")
    color: Mapped[str | None] = mapped_column(String(64), comment="前端展示颜色")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[int] = mapped_column(TINYINT(1), default=0, comment="0-正常, 1-已删除")
