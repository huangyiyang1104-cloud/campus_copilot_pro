from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.study_plan import StudyPlanItem, StudyPlanTaskItem, TaskDoneUpdate
from app.services import study_plan as study_plan_service

router = APIRouter(prefix="/api/study-plans", tags=["学习计划"])


@router.get("", response_model=list[StudyPlanItem], summary="我的学习计划")
async def list_plans(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudyPlanItem]:
    return await study_plan_service.list_plans(session, current_user.id)


@router.patch(
    "/{plan_id}/tasks/{task_id}",
    response_model=StudyPlanTaskItem,
    summary="勾选 / 取消勾选任务",
)
async def set_task_done(
    plan_id: int,
    task_id: int,
    payload: TaskDoneUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyPlanTaskItem:
    return await study_plan_service.set_task_done(
        session, current_user.id, plan_id, task_id, payload.done
    )


@router.delete("/{plan_id}", summary="删除学习计划")
async def delete_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    await study_plan_service.delete_plan(session, current_user.id, plan_id)
    return {"message": "学习计划已删除"}
