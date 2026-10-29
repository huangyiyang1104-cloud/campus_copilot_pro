from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study_plan_task import StudyPlanTask


class StudyPlanTaskRepository:
    """study_plan_tasks 表的数据访问"""

    @staticmethod
    async def list_by_plan(session: AsyncSession, plan_id: int) -> list[StudyPlanTask]:
        stmt = (
            select(StudyPlanTask)
            .where(StudyPlanTask.plan_id == plan_id, StudyPlanTask.is_deleted == 0)
            .order_by(StudyPlanTask.sort_order, StudyPlanTask.id)
        )
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def get_by_id_for_plan(
        session: AsyncSession, task_id: int, plan_id: int
    ) -> StudyPlanTask | None:
        stmt = select(StudyPlanTask).where(
            StudyPlanTask.id == task_id,
            StudyPlanTask.plan_id == plan_id,
            StudyPlanTask.is_deleted == 0,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, task: StudyPlanTask) -> StudyPlanTask:
        session.add(task)
        await session.flush()
        return task

    @staticmethod
    async def set_done(session: AsyncSession, task: StudyPlanTask, done: bool) -> StudyPlanTask:
        """勾选 / 取消勾选任务"""
        task.is_done = 1 if done else 0
        await session.flush()
        return task

    @staticmethod
    async def soft_delete(session: AsyncSession, task: StudyPlanTask) -> None:
        task.is_deleted = 1
        await session.flush()

    @staticmethod
    async def soft_delete_by_plans(session: AsyncSession, plan_ids: list[int]) -> None:
        stmt = (
            update(StudyPlanTask)
            .where(StudyPlanTask.plan_id.in_(plan_ids), StudyPlanTask.is_deleted == 0)
            .values(is_deleted=1)
        )
        await session.execute(stmt)
