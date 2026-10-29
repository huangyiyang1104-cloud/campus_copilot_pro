from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置，从 backend/.env 读取"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 数据库（异步驱动 aiomysql）
    DATABASE_URL: str = "mysql+aiomysql://root:root@127.0.0.1:3306/campus_agent?charset=utf8mb4"
    SQL_ECHO: bool = False

    # Redis（本地开发走 SSH 隧道，16379 -> 云上 6379）
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 16379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # DeepSeek（OpenAI 兼容接口）
    DEEPSEEK_APIKEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-flash"

    # 阿里云 OSS
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = ""
    OSS_ENDPOINT: str = ""

    @field_validator("OSS_ENDPOINT", mode="before")
    @classmethod
    def _strip_comment(cls, value: object) -> object:
        # 允许在 .env 的值后面写行内注释
        if isinstance(value, str):
            return value.split("#")[0].strip()
        return value

    # DashScope Embedding（OpenAI 兼容接口）
    DASHSCOPE_APIKEY: str = ""
    EMBEDDING_MODEL: str = "qwen3.7-text-embedding-flash"
    EMBEDDING_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_DIM: int = 1024

    # MinerU 文档解析
    MINERU_API_TOKEN: str = ""
    MINERU_BASE_URL: str = "https://mineru.net/api/v4"
    MINERU_MODEL_VERSION: str = "vlm"

    # Milvus：本地 Lite 填文件路径，云上 Standalone 填 http://ip:19530
    # 注意不要叫 MILVUS_URI，pymilvus 自己会读同名环境变量，容易冲突
    MILVUS_ENDPOINT: str = "./data/milvus_lite.db"
    MILVUS_COLLECTION: str = "course_material_chunks"

    # 资料处理方式：auto-本地 Lite 用 inline，远程 Milvus 用 celery
    MATERIAL_TASK_MODE: str = "auto"

    @property
    def material_task_mode(self) -> str:
        mode = self.MATERIAL_TASK_MODE.lower()
        if mode in ("inline", "celery"):
            return mode
        return "inline" if not self.MILVUS_ENDPOINT.startswith("http") else "celery"

    # Celery：和登录缓存分开用 Redis 的 1 号库
    CELERY_BROKER_DB: int = 1

    @property
    def CELERY_BROKER_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.CELERY_BROKER_DB}"

    # JWT
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def REFRESH_TOKEN_EXPIRE_SECONDS(self) -> int:
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
