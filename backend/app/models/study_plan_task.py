from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudyPlanTask(Base):
    """学习计划任务明细 study_plan_tasks"""

    __tablename__ = "study_plan_tasks"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), comment="所属学习计划ID")

    task_name: Mapped[str] = mapped_column(String(255), comment="任务内容")
    is_done: Mapped[int] = mapped_column(TINYINT(1), default=0, comment="0-未完成, 1-已完成")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="展示顺序")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    is_deleted: Mapped[int] = mapped_column(TINYINT(1), default=0, comment="0-正常, 1-已删除")
