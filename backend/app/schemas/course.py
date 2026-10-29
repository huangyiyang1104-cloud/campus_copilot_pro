from pydantic import BaseModel, Field


class CourseItem(BaseModel):
    """返回给前端的课程，字段和前端 Course 对齐"""

    id: int
    name: str
    teacher: str | None = None
    room: str | None = None
    day: int = Field(ge=1, le=5, description="星期几：1-周一 ... 5-周五")
    section: int = Field(ge=1, le=5, description="第几大节：1 表示第 1-2 节")
    color: str | None = None


class CourseSaveItem(BaseModel):
    """前端提交的单门课程"""

    name: str = Field(min_length=1, max_length=100)
    teacher: str | None = Field(default=None, max_length=50)
    room: str | None = Field(default=None, max_length=100)
    day: int = Field(ge=1, le=5)
    section: int = Field(ge=1, le=5)
    color: str | None = Field(default=None, max_length=64)


class CourseSaveRequest(BaseModel):
    """整表保存：前端一次提交当前课表的全部课程"""

    courses: list[CourseSaveItem] = Field(default_factory=list, max_length=50)
