from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course_material import CourseMaterial


class CourseMaterialRepository:
    """course_materials 表的数据访问"""

    @staticmethod
    async def get_by_id(session: AsyncSession, material_id: int) -> CourseMaterial | None:
        stmt = select(CourseMaterial).where(
            CourseMaterial.id == material_id, CourseMaterial.is_deleted == 0
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_by_user(session: AsyncSession, user_id: int) -> list[CourseMaterial]:
        """只查某个用户自己的资料，按上传时间倒序"""
        stmt = (
            select(CourseMaterial)
            .where(CourseMaterial.user_id == user_id, CourseMaterial.is_deleted == 0)
            .order_by(CourseMaterial.created_at.desc())
        )
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def create(session: AsyncSession, material: CourseMaterial) -> CourseMaterial:
        session.add(material)
        await session.flush()
        return material

    @staticmethod
    async def update_status(
        session: AsyncSession,
        material: CourseMaterial,
        status: int,
        chunk_count: int | None = None,
        error_msg: str | None = None,
    ) -> CourseMaterial:
        """异步解析任务里更新状态：0-待处理, 1-解析中, 2-已索引, 3-失败"""
        material.status = status
        if chunk_count is not None:
            material.chunk_count = chunk_count
        if error_msg is not None:
            material.error_msg = error_msg
        await session.flush()
        return material

    @staticmethod
    async def soft_delete(session: AsyncSession, material: CourseMaterial) -> None:
        material.is_deleted = 1
        await session.flush()
