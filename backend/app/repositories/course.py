from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course


class CourseRepository:
    """courses 表的数据访问"""

    @staticmethod
    async def get_by_id(session: AsyncSession, course_id: int) -> Course | None:
        stmt = select(Course).where(Course.id == course_id, Course.is_deleted == 0)
        return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_by_user(
        session: AsyncSession, user_id: int, semester: str | None = None
    ) -> list[Course]:
        """查某个学生的课表，按星期和节次排好序"""
        stmt = select(Course).where(Course.user_id == user_id, Course.is_deleted == 0)
        if semester:
            stmt = stmt.where(Course.semester == semester)
        stmt = stmt.order_by(Course.day_of_week, Course.start_section)
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def create(session: AsyncSession, course: Course) -> Course:
        session.add(course)
        await session.flush()
        return course

    @staticmethod
    async def delete_by_user(session: AsyncSession, user_id: int, semester: str) -> None:
        """整表覆盖前清掉旧数据，避免每次保存都堆一批已删除记录"""
        stmt = delete(Course).where(
            Course.user_id == user_id,
            Course.semester == semester,
        )
        await session.execute(stmt)
        await session.flush()

    @staticmethod
    async def soft_delete(session: AsyncSession, course: Course) -> None:
        course.is_deleted = 1
        await session.flush()
