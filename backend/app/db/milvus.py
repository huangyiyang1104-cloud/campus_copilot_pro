import os
import threading

from pymilvus import DataType, MilvusClient

from app.core.config import settings

_lock = threading.Lock()
_client: MilvusClient | None = None


def _collection_name() -> str:
    return settings.MILVUS_COLLECTION


def _get_client() -> MilvusClient:
    """本地 Lite 传文件路径，云上 Standalone 传 http://ip:19530"""
    global _client
    if _client is not None:
        return _client

    uri = settings.MILVUS_ENDPOINT
    if not uri.startswith(("http://", "https://")):
        os.makedirs(os.path.dirname(os.path.abspath(uri)), exist_ok=True)

    client = MilvusClient(uri=uri)

    if not client.has_collection(_collection_name()):
        schema = client.create_schema(auto_id=True, enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("user_id", DataType.INT64)
        schema.add_field("material_id", DataType.INT64)
        schema.add_field("course_name", DataType.VARCHAR, max_length=100)
        schema.add_field("file_name", DataType.VARCHAR, max_length=255)
        schema.add_field("chunk_index", DataType.INT32)
        schema.add_field("content", DataType.VARCHAR, max_length=65535)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIM)

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )
        client.create_collection(
            collection_name=_collection_name(),
            schema=schema,
            index_params=index_params,
        )

    _client = client
    return client


def _get_loaded_client() -> MilvusClient:
    """Lite 在 delete/flush 后会把 collection 置为 released，操作前确保已加载"""
    client = _get_client()
    try:
        client.load_collection(_collection_name())
    except Exception:
        # 已经加载时会直接返回，这里不吞掉真正的失败，后面的操作会抛出
        pass
    return client


def _user_filter(user_id: int, course_name: str | None) -> str:
    expr = f"user_id == {user_id}"
    if course_name:
        safe_name = course_name.replace('"', '\\"')
        expr += f' and course_name == "{safe_name}"'
    return expr


def insert_chunks(
    user_id: int,
    material_id: int,
    course_name: str,
    file_name: str,
    chunks: list[str],
    vectors: list[list[float]],
) -> None:
    rows = [
        {
            "user_id": user_id,
            "material_id": material_id,
            "course_name": (course_name or "")[:100],
            "file_name": file_name[:255],
            "chunk_index": index,
            "content": chunk[:2000],
            "vector": vectors[index],
        }
        for index, chunk in enumerate(chunks)
    ]

    with _lock:
        client = _get_loaded_client()
        client.insert(collection_name=_collection_name(), data=rows)
        client.flush(_collection_name())


def delete_material(material_id: int) -> None:
    with _lock:
        client = _get_loaded_client()
        client.delete(
            collection_name=_collection_name(),
            filter=f"material_id == {material_id}",
        )
        client.flush(_collection_name())
        client.load_collection(_collection_name())


def dense_search(
    user_id: int,
    vector: list[float],
    limit: int,
    course_name: str | None = None,
) -> list[dict]:
    with _lock:
        results = _get_loaded_client().search(
            collection_name=_collection_name(),
            data=[vector],
            limit=limit,
            filter=_user_filter(user_id, course_name),
            output_fields=["content", "file_name", "course_name", "chunk_index"],
        )

    hits: list[dict] = []
    for hit in results[0]:
        entity = hit.get("entity", {})
        hits.append(
            {
                "id": hit["id"],
                "content": entity.get("content"),
                "file_name": entity.get("file_name"),
                "course_name": entity.get("course_name"),
                "chunk_index": entity.get("chunk_index"),
                "dense_score": round(float(hit["distance"]), 4),
            }
        )
    return hits


def query_user_chunks(
    user_id: int,
    course_name: str | None = None,
    limit: int = 16384,
) -> list[dict]:
    """BM25 需要完整语料，这里按用户把切片捞出来（课程项目量级够用）"""
    with _lock:
        rows = _get_loaded_client().query(
            collection_name=_collection_name(),
            filter=_user_filter(user_id, course_name),
            output_fields=["content", "file_name", "course_name", "chunk_index"],
            limit=limit,
        )

    return [
        {
            "id": row["id"],
            "content": row.get("content", ""),
            "file_name": row.get("file_name"),
            "course_name": row.get("course_name"),
            "chunk_index": row.get("chunk_index"),
        }
        for row in rows
    ]
