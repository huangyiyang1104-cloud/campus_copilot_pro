from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

_embeddings: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.DASHSCOPE_APIKEY,
            base_url=settings.EMBEDDING_BASE_URL,
            # 不要用 tiktoken 自己切分，直接把原文交给 DashScope
            check_embedding_ctx_length=False,
            chunk_size=10,
        )
    return _embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    return get_embeddings().embed_documents(texts)


def embed_query(text: str) -> list[float]:
    return get_embeddings().embed_query(text)
