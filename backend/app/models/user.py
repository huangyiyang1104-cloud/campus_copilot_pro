from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """用户表 users"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, comment="账号")
    password: Mapped[str] = mapped_column(String(255), comment="密码")
    name: Mapped[str] = mapped_column(String(50), comment="名称")
    role: Mapped[str] = mapped_column(String(50), comment="角色：student-学生，admin-管理员")
    email: Mapped[str | None] = mapped_column(String(50), comment="邮箱")
    phone: Mapped[str | None] = mapped_column(String(50), comment="手机号")
    avatar: Mapped[str | None] = mapped_column(String(255), comment="头像")
    status: Mapped[int] = mapped_column(TINYINT, comment="状态：0-禁用，1-正常")

    # 这张表的两个时间字段没有数据库默认值，插入时必须由代码给出
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
