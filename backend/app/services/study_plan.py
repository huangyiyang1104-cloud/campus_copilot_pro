from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.study_plan import StudyPlan
from app.models.study_plan_task import StudyPlanTask
from app.repositories.study_plan import StudyPlanRepository
from app.repositories.study_plan_task import StudyPlanTaskRepository
from app.schemas.study_plan import StudyPlanItem, StudyPlanTaskItem


def _to_item(plan: StudyPlan, tasks: list[StudyPlanTask]) -> StudyPlanItem:
    return StudyPlanItem(
        id=plan.id,
        title=plan.title,
        course=plan.course_name,
        deadline=plan.deadline,
        tasks=[
            StudyPlanTaskItem(id=task.id, name=task.task_name, done=bool(task.is_done))
            for task in tasks
        ],
    )


async def _purge_expired(session: AsyncSession, user_id: int) -> None:
    """截止日期过了的计划自动软删，当天仍然保留"""
    expired_ids = await StudyPlanRepository.list_expired_ids(session, user_id, date.today())
    if not expired_ids:
        return

    await StudyPlanTaskRepository.soft_delete_by_plans(session, expired_ids)
    await StudyPlanRepository.soft_delete_many(session, expired_ids)
    await session.commit()


async def list_plans(session: AsyncSession, user_id: int) -> list[StudyPlanItem]:
    await _purge_expired(session, user_id)

    plans = await StudyPlanRepository.list_by_user(session, user_id)
    result: list[StudyPlanItem] = []
    for plan in plans:
        tasks = await StudyPlanTaskRepository.list_by_plan(session, plan.id)
        result.append(_to_item(plan, tasks))
    return result


async def set_task_done(
    session: AsyncSession, user_id: int, plan_id: int, task_id: int, done: bool
) -> StudyPlanTaskItem:
    plan = await StudyPlanRepository.get_by_id_for_user(session, plan_id, user_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "plan_not_found", "message": "学习计划不存在"},
        )

    task = await StudyPlanTaskRepository.get_by_id_for_plan(session, task_id, plan_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": "任务不存在或已删除"},
        )

    await StudyPlanTaskRepository.set_done(session, task, done)
    await session.commit()
    return StudyPlanTaskItem(id=task.id, name=task.task_name, done=bool(task.is_done))


async def delete_plan(session: AsyncSession, user_id: int, plan_id: int) -> None:
    plan = await StudyPlanRepository.get_by_id_for_user(session, plan_id, user_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "plan_not_found", "message": "学习计划不存在"},
        )

    await StudyPlanTaskRepository.soft_delete_by_plans(session, [plan.id])
    await StudyPlanRepository.soft_delete(session, plan)
    await session.commit()


async def create_plan(
    session: AsyncSession,
    user_id: int,
    title: str,
    course_name: str,
    deadline: date,
    tasks: list[str],
) -> StudyPlanItem:
    """给 Agent 用：确认过信息后一次性写入计划和任务"""
    plan = StudyPlan(
        user_id=user_id,
        title=title,
        course_name=course_name,
        deadline=deadline,
    )
    await StudyPlanRepository.create(session, plan)

    for index, name in enumerate(tasks):
        await StudyPlanTaskRepository.create(
            session,
            StudyPlanTask(plan_id=plan.id, task_name=name, sort_order=index),
        )

    await session.commit()

    saved_tasks = await StudyPlanTaskRepository.list_by_plan(session, plan.id)
    return _to_item(plan, saved_tasks)
