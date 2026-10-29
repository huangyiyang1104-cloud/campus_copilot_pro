from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudyPlan(Base):
    """学习计划 study_plans"""

    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), comment="所属用户ID")

    title: Mapped[str] = mapped_column(String(100), comment="计划标题")
    course_name: Mapped[str | None] = mapped_column(String(100), comment="关联课程名称")
    deadline: Mapped[date | None] = mapped_column(Date, comment="截止日期")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[int] = mapped_column(TINYINT(1), default=0, comment="0-正常, 1-已删除")
