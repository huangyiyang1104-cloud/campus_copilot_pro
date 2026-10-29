from datetime import datetime

from pydantic import BaseModel


class MaterialItem(BaseModel):
    """返回给前端的课程资料"""

    id: int
    name: str
    file_type: str
    size: int
    course: str | None = None
    chunk_count: int
    status: int
    error_msg: str | None = None
    created_at: datetime
