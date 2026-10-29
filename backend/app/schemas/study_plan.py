from datetime import date

from pydantic import BaseModel, Field


class StudyPlanTaskItem(BaseModel):
    """前端展示的单条任务"""

    id: int
    name: str
    done: bool


class StudyPlanItem(BaseModel):
    """一个学习计划及其任务"""

    id: int
    title: str
    course: str | None = None
    deadline: date | None = None
    tasks: list[StudyPlanTaskItem]


class TaskDoneUpdate(BaseModel):
    """勾选 / 取消勾选任务，传绝对状态而不是取反"""

    done: bool = Field(description="true-已完成，false-未完成")
