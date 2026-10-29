import asyncio
import logging
import uuid

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import oss
from app.core.config import settings
from app.core.document import SUPPORTED_SUFFIXES
from app.db.milvus import delete_material as delete_material_vectors
from app.models.course_material import CourseMaterial
from app.models.user import User
from app.repositories.course_material import CourseMaterialRepository
from app.schemas.material import MaterialItem

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024


def _to_item(material: CourseMaterial) -> MaterialItem:
    return MaterialItem(
        id=material.id,
        name=material.file_name,
        file_type=material.file_type,
        size=material.file_size,
        course=material.course_name,
        chunk_count=material.chunk_count,
        status=material.status,
        error_msg=material.error_msg,
        created_at=material.created_at,
    )


async def list_materials(session: AsyncSession, user: User) -> list[MaterialItem]:
    materials = await CourseMaterialRepository.list_by_user(session, user.id)
    return [_to_item(material) for material in materials]


async def upload_material(
    session: AsyncSession,
    user: User,
    file: UploadFile,
    course_name: str | None,
    background_tasks: BackgroundTasks,
) -> MaterialItem:
    filename = file.filename or "未命名文件"
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "unsupported_file",
                "message": "只支持 PDF / Word / PPT / Excel / Markdown",
            },
        )

    size = file.size
    if size is None:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "file_too_large", "message": "单个文件不能超过 20 MB"},
        )

    object_name = f"materials/{user.id}/{uuid.uuid4().hex}.{suffix}"

    try:
        await asyncio.to_thread(oss.upload_object, object_name, file.file)
    except Exception:
        logger.exception("上传 OSS 失败")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "oss_upload_failed", "message": "文件上传失败，请稍后重试"},
        ) from None

    material = CourseMaterial(
        user_id=user.id,
        file_name=filename[:255],
        file_type=suffix,
        file_size=size,
        course_name=course_name,
        oss_object_name=object_name,
        chunk_count=0,
        status=0,
    )

    try:
        await CourseMaterialRepository.create(session, material)
        await session.commit()
        # created_at 是数据库默认值，刷新后才能拿去序列化
        await session.refresh(material)
    except Exception:
        await session.rollback()
        await asyncio.to_thread(oss.delete_object, object_name)
        raise

    # Lite 单进程：交给 FastAPI 的 BackgroundTasks 跑；远程 Milvus 才走 Celery
    try:
        if settings.material_task_mode == "inline":
            from app.tasks.material import run_material_task

            background_tasks.add_task(run_material_task, material.id)
        else:
            from app.tasks.material import process_material

            await asyncio.to_thread(process_material.delay, material.id)
    except Exception as exc:
        logger.exception("投递解析任务失败 material_id=%s", material.id)
        material.status = 3
        material.error_msg = f"任务投递失败：{exc}"[:500]
        await session.commit()

    return _to_item(material)


async def delete_material(session: AsyncSession, user: User, material_id: int) -> None:
    material = await CourseMaterialRepository.get_by_id(session, material_id)
    if material is None or material.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "material_not_found", "message": "资料不存在"},
        )

    # 先删向量，避免出现「列表里没了但 AI 还能引用」
    try:
        await asyncio.to_thread(delete_material_vectors, material.id)
    except Exception:
        logger.exception("删除 Milvus 向量失败 material_id=%s", material.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "vector_store_unavailable", "message": "向量库暂时不可用，请稍后重试"},
        ) from None

    await CourseMaterialRepository.soft_delete(session, material)
    await session.commit()

    try:
        await asyncio.to_thread(oss.delete_object, material.oss_object_name)
    except Exception:
        logger.warning("删除 OSS 对象失败 object=%s", material.oss_object_name)


async def create_download_url(
    session: AsyncSession, user: User, material_id: int
) -> dict[str, str]:
    material = await CourseMaterialRepository.get_by_id(session, material_id)
    if material is None or material.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "material_not_found", "message": "资料不存在"},
        )

    url = await asyncio.to_thread(oss.presign_url, material.oss_object_name, 3600)
    return {"url": url, "file_name": material.file_name}
