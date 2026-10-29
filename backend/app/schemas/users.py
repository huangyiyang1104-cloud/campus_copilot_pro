from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserItem(BaseModel):
    """管理端用户列表 / 详情（不含密码）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    role: str
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    status: int
    create_time: datetime
    update_time: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50, description="账号，唯一")
    password: str = Field(min_length=6, max_length=64, description="明文密码，后端加密后再入库")
    name: str = Field(min_length=1, max_length=50, description="姓名")
    role: str = Field(default="student", description="student / admin")
    email: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    avatar: str | None = Field(default=None, max_length=255)
    status: int = Field(default=1, ge=0, le=1, description="0-禁用，1-正常")


class UserUpdate(BaseModel):
    """字段都不传表示不改"""

    username: str | None = Field(default=None, min_length=1, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=50)
    role: str | None = None
    email: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    avatar: str | None = Field(default=None, max_length=255)
    status: int | None = Field(default=None, ge=0, le=1)


class UserStatusUpdate(BaseModel):
    """管理员启用/禁用用户"""

    status: int = Field(ge=0, le=1, description="0-禁用（同时踢下线），1-正常")
