"""资料上传压测：并发上传 Markdown、等待 OSS + 切片 + Milvus 入库完成。

运行：
    cd backend
    python -m tests.load.material_load

可用环境变量：
    LOAD_BASE_URL / LOAD_ADMIN_USERNAME / LOAD_ADMIN_PASSWORD
    MATERIAL_UPLOADS（默认 3）/ MATERIAL_CONCURRENCY（默认 3）
    MATERIAL_TIMEOUT（默认 120 秒）
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid

import httpx

from .common import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    BASE_URL,
    create_temp_user,
    delete_temp_user,
    headers_for,
    login,
    percentile,
)

UPLOADS = int(os.getenv("MATERIAL_UPLOADS", "3"))
CONCURRENCY = int(os.getenv("MATERIAL_CONCURRENCY", "3"))
TIMEOUT = float(os.getenv("MATERIAL_TIMEOUT", "120"))


def sample_content(index: int) -> tuple[bytes, str]:
    code = f"LOAD-{index}-{uuid.uuid4().hex[:6]}"
    text = (
        f"# 压测资料 {index}\n\n"
        f"这是一份并发上传测试资料，专属暗号是 {code}。\n\n"
        "## 测试说明\n\n用于验证 OSS、切片、Embedding 和 Milvus 写入链路。\n"
    )
    return text.encode("utf-8"), code


async def main() -> int:
    print(f"target: {BASE_URL}")
    print(f"uploads: {UPLOADS} / concurrency {CONCURRENCY}")

    limits = httpx.Limits(max_connections=CONCURRENCY * 2)
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=httpx.Timeout(60),
        limits=limits,
    ) as client:
        admin_token = await login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
        admin_headers = headers_for(admin_token)
        user_id, username, password = await create_temp_user(
            client, admin_headers, "load_material"
        )

        uploaded: list[tuple[int, float, float]] = []  # (id, upload_latency, started_at)
        headers: dict[str, str] = {}
        try:
            token = await login(client, username, password)
            headers = headers_for(token)
            semaphore = asyncio.Semaphore(CONCURRENCY)

            async def upload(index: int) -> tuple[int, float, float]:
                async with semaphore:
                    content, _code = sample_content(index)
                    started = time.perf_counter()
                    response = await client.post(
                        "/api/materials/upload",
                        headers=headers,
                        files={
                            "file": (
                                f"load_{index}.md",
                                content,
                                "text/markdown",
                            )
                        },
                    )
                    latency = time.perf_counter() - started
                    response.raise_for_status()
                    return response.json()["id"], latency, started

            outcomes = await asyncio.gather(
                *(upload(index) for index in range(UPLOADS)),
                return_exceptions=True,
            )

            upload_errors = 0
            for outcome in outcomes:
                if isinstance(outcome, Exception):
                    upload_errors += 1
                    print("upload error:", f"{type(outcome).__name__}: {outcome}"[:200])
                else:
                    uploaded.append(outcome)

            pending = {material_id for material_id, _, _ in uploaded}
            completed: dict[int, float] = {}
            statuses: dict[int, int] = {}
            chunks: dict[int, int] = {}
            deadline = time.monotonic() + TIMEOUT

            while pending and time.monotonic() < deadline:
                response = await client.get("/api/materials", headers=headers)
                response.raise_for_status()
                rows = {row["id"]: row for row in response.json()}

                for material_id in list(pending):
                    row = rows.get(material_id)
                    if row is None:
                        continue
                    statuses[material_id] = row["status"]
                    chunks[material_id] = row["chunk_count"]
                    if row["status"] in (2, 3):
                        completed[material_id] = time.perf_counter()
                        pending.remove(material_id)

                if pending:
                    await asyncio.sleep(1)

            upload_latencies = [latency for _, latency, _ in uploaded]
            ingest_latencies = [
                completed[material_id] - started
                for material_id, _, started in uploaded
                if material_id in completed
            ]

            print("-" * 64)
            print(
                f"uploaded: {len(uploaded)}/{UPLOADS}  upload errors: {upload_errors}  "
                f"timed out: {len(pending)}"
            )
            if upload_latencies:
                print(
                    "upload latency: "
                    f"p50={percentile(upload_latencies, 0.50) * 1000:.0f}ms "
                    f"p95={percentile(upload_latencies, 0.95) * 1000:.0f}ms"
                )
            if ingest_latencies:
                print(
                    "ingest latency: "
                    f"p50={percentile(ingest_latencies, 0.50) * 1000:.0f}ms "
                    f"p95={percentile(ingest_latencies, 0.95) * 1000:.0f}ms"
                )
            print(
                "final states:",
                [(material_id, statuses.get(material_id), chunks.get(material_id)) for material_id, _, _ in uploaded],
            )

            failed = upload_errors + len(pending)
            failed += sum(1 for material_id in statuses if statuses[material_id] == 3)
            return 1 if failed else 0
        finally:
            for material_id, _, _ in uploaded:
                try:
                    await client.delete(f"/api/materials/{material_id}", headers=headers)
                except Exception:
                    pass
            await delete_temp_user(client, admin_headers, user_id)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
