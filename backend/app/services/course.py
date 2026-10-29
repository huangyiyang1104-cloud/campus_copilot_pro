from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.user import User
from app.repositories.course import CourseRepository
from app.schemas.course import CourseItem, CourseSaveItem

# 当前只做这一个学期，等多学期时再改成配置或请求参数
SEMESTER = "2026-2027-1"


def _to_item(course: Course) -> CourseItem:
    """数据库字段 -> 前端字段；1-2 节、3-4 节这种区间换算回“第几大节”"""
    return CourseItem(
        id=course.id,
        name=course.course_name,
        teacher=course.teacher,
        room=course.classroom,
        day=course.day_of_week,
        section=(course.start_section + 1) // 2,
        color=course.color,
    )


async def list_courses(session: AsyncSession, user: User) -> list[CourseItem]:
    courses = await CourseRepository.list_by_user(session, user.id, SEMESTER)
    return [_to_item(course) for course in courses]


async def save_courses(
    session: AsyncSession, user: User, items: list[CourseSaveItem]
) -> list[CourseItem]:
    """整表覆盖：先删掉该用户本学期的课，再按提交的顺序重新插入"""
    slots: set[tuple[int, int]] = set()
    for item in items:
        slot = (item.day, item.section)
        if slot in slots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "course_conflict", "message": "同一时段存在重复课程"},
            )
        slots.add(slot)

    await CourseRepository.delete_by_user(session, user.id, SEMESTER)

    for item in items:
        session.add(
            Course(
                user_id=user.id,
                course_name=item.name,
                teacher=item.teacher,
                classroom=item.room,
                day_of_week=item.day,
                start_section=item.section * 2 - 1,
                end_section=item.section * 2,
                semester=SEMESTER,
                color=item.color,
            )
        )

    await session.commit()

    courses = await CourseRepository.list_by_user(session, user.id, SEMESTER)
    return [_to_item(course) for course in courses]
