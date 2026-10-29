from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.users import UserCreate, UserItem, UserStatusUpdate, UserUpdate
from app.services import users as users_service

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("", response_model=list[UserItem], summary="用户列表")
async def list_users(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[UserItem]:
    users = await users_service.list_users(session)
    return [UserItem.model_validate(user) for user in users]


@router.post(
    "",
    response_model=UserItem,
    status_code=status.HTTP_201_CREATED,
    summary="新增用户",
)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserItem:
    user = await users_service.create_user(session, payload)
    return UserItem.model_validate(user)


@router.put("/{user_id}", response_model=UserItem, summary="编辑用户")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserItem:
    user = await users_service.get_user(session, user_id)
    updated = await users_service.update_user(session, user, payload)
    return UserItem.model_validate(updated)


@router.patch(
    "/{user_id}/status",
    response_model=UserItem,
    summary="启用 / 禁用用户（禁用时踢下线）",
)
async def change_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserItem:
    user = await users_service.get_user(session, user_id)
    updated = await users_service.change_status(session, user, payload.status)
    return UserItem.model_validate(updated)


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, str]:
    user = await users_service.get_user(session, user_id)
    await users_service.delete_user(session, user)
    return {"message": "用户已删除"}
