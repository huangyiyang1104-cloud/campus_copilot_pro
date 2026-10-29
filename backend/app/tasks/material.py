import asyncio
import logging

from app.core import oss
from app.core.celery_app import celery_app
from app.core.document import extract_text, split_text
from app.core.embedding import embed_texts
from app.db.milvus import delete_material as delete_material_vectors
from app.db.milvus import insert_chunks
from app.db.session import AsyncSessionLocal, engine
from app.repositories.course_material import CourseMaterialRepository

logger = logging.getLogger(__name__)


@celery_app.task(name="materials.process")
def process_material(material_id: int) -> None:
    """Celery 入口是同步函数，异步逻辑放到独立事件循环里跑"""
    asyncio.run(_process(material_id))


async def run_material_task(material_id: int) -> None:
    """Milvus Lite 只允许一个进程打开，本地由 FastAPI 直接跑，不经过 Celery"""
    await _process_material(material_id)


async def _process(material_id: int) -> None:
    """每个 Celery 任务都会新建一个事件循环，跑完必须清掉连接池里的连接"""
    try:
        await _process_material(material_id)
    finally:
        await engine.dispose()


async def _process_material(material_id: int) -> None:
    async with AsyncSessionLocal() as session:
        material = await CourseMaterialRepository.get_by_id(session, material_id)
        if material is None or material.status == 2:
            return

        await CourseMaterialRepository.update_status(session, material, 1)
        await session.commit()

        info = {
            "user_id": material.user_id,
            "oss_object_name": material.oss_object_name,
            "file_type": material.file_type,
            "file_name": material.file_name,
            "course_name": material.course_name or "",
        }

    try:
        raw = await asyncio.to_thread(oss.download_object, info["oss_object_name"])
        text = await asyncio.to_thread(extract_text, raw, info["file_name"])
        chunks = await asyncio.to_thread(split_text, text)
        if not chunks:
            raise ValueError("没有解析到文本，可能是扫描版 PDF 或空文档")

        vectors = await asyncio.to_thread(embed_texts, chunks)

        # 处理期间资料可能被删掉，插入前再确认一次
        async with AsyncSessionLocal() as session:
            if await CourseMaterialRepository.get_by_id(session, material_id) is None:
                return

        # 重试时先清掉旧向量，保证幂等
        await asyncio.to_thread(delete_material_vectors, material_id)
        await asyncio.to_thread(
            insert_chunks,
            info["user_id"],
            material_id,
            info["course_name"],
            info["file_name"],
            chunks,
            vectors,
        )
    except Exception as exc:
        logger.exception("资料处理失败 material_id=%s", material_id)
        async with AsyncSessionLocal() as session:
            material = await CourseMaterialRepository.get_by_id(session, material_id)
            if material is not None:
                await CourseMaterialRepository.update_status(
                    session, material, 3, error_msg=str(exc)[:500]
                )
                await session.commit()
        return

    async with AsyncSessionLocal() as session:
        material = await CourseMaterialRepository.get_by_id(session, material_id)
        if material is None:
            # 插入向量之后资料才被删掉，补一次清理，避免留下孤儿向量
            await asyncio.to_thread(delete_material_vectors, material_id)
            return

        await CourseMaterialRepository.update_status(
            session, material, 2, chunk_count=len(chunks)
        )
        material.error_msg = None
        await session.commit()
