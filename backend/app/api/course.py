from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.course import CourseItem, CourseSaveRequest
from app.services import course as course_service

router = APIRouter(prefix="/api/courses", tags=["课表"])


@router.get("", response_model=list[CourseItem], summary="我的课表")
async def list_courses(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CourseItem]:
    return await course_service.list_courses(session, current_user)


@router.put("", response_model=list[CourseItem], summary="保存课表（整表覆盖）")
async def save_courses(
    payload: CourseSaveRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CourseItem]:
    return await course_service.save_courses(session, current_user, payload.courses)
