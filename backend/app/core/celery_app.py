from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "campus_copilot",
    broker=settings.CELERY_BROKER_URL,
    include=["app.tasks.material"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    task_ignore_result=True,
    timezone="Asia/Shanghai",
    enable_utc=False,
    broker_connection_retry_on_startup=True,
    # Redis 不通时立即失败，由上传接口把资料状态标成失败，避免请求卡住
    task_publish_retry=False,
)
