import oss2

from app.core.config import settings

_bucket: oss2.Bucket | None = None


def get_bucket() -> oss2.Bucket:
    global _bucket
    if _bucket is None:
        auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
        _bucket = oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)
    return _bucket


def upload_object(object_name: str, file_obj) -> None:
    get_bucket().put_object(object_name, file_obj)


def download_object(object_name: str) -> bytes:
    return get_bucket().get_object(object_name).read()


def delete_object(object_name: str) -> None:
    get_bucket().delete_object(object_name)


def presign_url(object_name: str, expires: int = 3600) -> str:
    """生成短效下载地址，前端拿到后直接访问"""
    return get_bucket().sign_url("GET", object_name, expires)
