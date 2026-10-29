import re

import jieba
from rank_bm25 import BM25Okapi

from app.db.milvus import dense_search, query_user_chunks

RRF_K = 60
CANDIDATE_SIZE = 20

_STOPWORDS = {
    "的",
    "了",
    "是",
    "在",
    "和",
    "与",
    "及",
    "有",
    "我",
    "你",
    "他",
    "她",
    "这",
    "那",
    "就",
    "也",
    "都",
    "要",
    "会",
    "对",
    "中",
    "一个",
    "什么",
}


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text.lower())
    return [
        token
        for token in jieba.lcut(cleaned)
        if token.strip() and token not in _STOPWORDS
    ]


def _rrf_merge(ranked_lists: list[list[dict]]) -> list[dict]:
    """Reciprocal Rank Fusion：只看名次，不关心两路分数不在同一量纲"""
    scores: dict[int, float] = {}
    items: dict[int, dict] = {}

    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            key = item["id"]
            items.setdefault(key, item)
            scores[key] = scores.get(key, 0.0) + 1 / (RRF_K + rank)

    for key, item in items.items():
        item["rrf_score"] = round(scores[key], 6)

    return sorted(items.values(), key=lambda item: item["rrf_score"], reverse=True)


def hybrid_search(
    user_id: int,
    query: str,
    query_vector: list[float],
    top_k: int = 5,
    course_name: str | None = None,
) -> list[dict]:
    dense_hits = dense_search(user_id, query_vector, CANDIDATE_SIZE, course_name)

    corpus = query_user_chunks(user_id, course_name)
    lexical_hits: list[dict] = []
    query_tokens = _tokenize(query)

    if corpus and query_tokens:
        rows = [(row, _tokenize(row["content"])) for row in corpus]
        rows = [(row, tokens) for row, tokens in rows if tokens]

        if rows:
            bm25 = BM25Okapi([tokens for _, tokens in rows])
            scores = bm25.get_scores(query_tokens)
            order = sorted(range(len(rows)), key=lambda i: scores[i], reverse=True)

            for index in order[:CANDIDATE_SIZE]:
                if scores[index] <= 0:
                    continue
                row = rows[index][0]
                lexical_hits.append({**row, "bm25_score": round(float(scores[index]), 4)})

    return _rrf_merge([dense_hits, lexical_hits])[:top_k]
