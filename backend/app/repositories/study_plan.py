from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study_plan import StudyPlan


class StudyPlanRepository:
    """study_plans 表的数据访问"""

    @staticmethod
    async def get_by_id(session: AsyncSession, plan_id: int) -> StudyPlan | None:
        stmt = select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.is_deleted == 0)
        return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_by_user(session: AsyncSession, user_id: int) -> list[StudyPlan]:
        stmt = (
            select(StudyPlan)
            .where(StudyPlan.user_id == user_id, StudyPlan.is_deleted == 0)
            .order_by(StudyPlan.deadline, StudyPlan.id)
        )
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def get_by_id_for_user(
        session: AsyncSession, plan_id: int, user_id: int
    ) -> StudyPlan | None:
        stmt = select(StudyPlan).where(
            StudyPlan.id == plan_id,
            StudyPlan.user_id == user_id,
            StudyPlan.is_deleted == 0,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def list_expired_ids(session: AsyncSession, user_id: int, today: date) -> list[int]:
        """截止日期已经过了的计划（当天仍然保留）"""
        stmt = select(StudyPlan.id).where(
            StudyPlan.user_id == user_id,
            StudyPlan.is_deleted == 0,
            StudyPlan.deadline.is_not(None),
            StudyPlan.deadline < today,
        )
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def create(session: AsyncSession, plan: StudyPlan) -> StudyPlan:
        session.add(plan)
        await session.flush()
        return plan

    @staticmethod
    async def soft_delete(session: AsyncSession, plan: StudyPlan) -> None:
        plan.is_deleted = 1
        await session.flush()

    @staticmethod
    async def soft_delete_many(session: AsyncSession, plan_ids: list[int]) -> None:
        stmt = update(StudyPlan).where(StudyPlan.id.in_(plan_ids)).values(is_deleted=1)
        await session.execute(stmt)
