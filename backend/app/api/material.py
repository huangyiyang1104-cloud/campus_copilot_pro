from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.material import MaterialItem
from app.services import material as material_service

router = APIRouter(prefix="/api/materials", tags=["课程资料"])


@router.get("", response_model=list[MaterialItem], summary="我的课程资料")
async def list_materials(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MaterialItem]:
    return await material_service.list_materials(session, current_user)


@router.post(
    "/upload",
    response_model=MaterialItem,
    status_code=status.HTTP_202_ACCEPTED,
    summary="上传课程资料（异步入库）",
)
async def upload_material(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    course_name: str | None = Form(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MaterialItem:
    return await material_service.upload_material(
        session, current_user, file, course_name, background_tasks
    )


@router.get("/{material_id}/download-url", summary="获取短效下载地址")
async def create_download_url(
    material_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    return await material_service.create_download_url(session, current_user, material_id)


@router.delete("/{material_id}", summary="删除课程资料")
async def delete_material(
    material_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    await material_service.delete_material(session, current_user, material_id)
    return {"message": "资料已删除"}
