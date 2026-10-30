"""SSE 对话压测：并发建会话、流式对话、统计首包和总耗时。

运行：
    cd backend
    python -m tests.load.chat_load

可用环境变量：
    LOAD_BASE_URL / LOAD_ADMIN_USERNAME / LOAD_ADMIN_PASSWORD
    CHAT_REQUESTS（默认 3）/ CHAT_CONCURRENCY（默认 3）
    CHAT_PROMPT（默认“只回复两个字：收到”）
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

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

CHAT_REQUESTS = int(os.getenv("CHAT_REQUESTS", "3"))
CHAT_CONCURRENCY = int(os.getenv("CHAT_CONCURRENCY", "3"))
CHAT_PROMPT = os.getenv("CHAT_PROMPT", "只回复两个字：收到")


async def ask(client: httpx.AsyncClient, headers: dict[str, str], conversation_id: int) -> tuple[float, float]:
    """返回（首包耗时, 总耗时）"""
    first_delta: float | None = None
    started = time.perf_counter()

    async with client.stream(
        "POST",
        "/api/chat/stream",
        headers=headers,
        json={"conversation_id": conversation_id, "message": CHAT_PROMPT},
        timeout=120,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue

            event = json.loads(line[6:])
            if event["type"] == "delta":
                if first_delta is None:
                    first_delta = time.perf_counter() - started
            elif event["type"] == "error":
                raise RuntimeError(event.get("message") or "stream error")
            elif event["type"] == "done":
                break

    if first_delta is None:
        raise RuntimeError("stream finished without delta")

    return first_delta, time.perf_counter() - started


async def one_chat(client: httpx.AsyncClient, headers: dict[str, str]) -> tuple[float, float]:
    conversation_id: int | None = None
    try:
        created = await client.post("/api/conversations", headers=headers)
        created.raise_for_status()
        conversation_id = created.json()["id"]
        return await ask(client, headers, conversation_id)
    finally:
        if conversation_id is not None:
            try:
                await client.delete(f"/api/conversations/{conversation_id}", headers=headers)
            except Exception:
                pass


async def main() -> int:
    print(f"target: {BASE_URL}")
    print(f"chat: {CHAT_REQUESTS} requests / concurrency {CHAT_CONCURRENCY}")
    print(f"prompt: {CHAT_PROMPT}")

    limits = httpx.Limits(max_connections=CHAT_CONCURRENCY * 2)
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=httpx.Timeout(120),
        limits=limits,
    ) as client:
        admin_token = await login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
        admin_headers = headers_for(admin_token)
        user_id, username, password = await create_temp_user(
            client, admin_headers, "load_chat"
        )

        try:
            token = await login(client, username, password)
            headers = headers_for(token)
            semaphore = asyncio.Semaphore(CHAT_CONCURRENCY)

            async def wrapped() -> tuple[float, float]:
                async with semaphore:
                    return await one_chat(client, headers)

            started = time.perf_counter()
            outcomes = await asyncio.gather(
                *(wrapped() for _ in range(CHAT_REQUESTS)),
                return_exceptions=True,
            )
            wall = time.perf_counter() - started

            firsts: list[float] = []
            totals: list[float] = []
            errors: list[str] = []
            for outcome in outcomes:
                if isinstance(outcome, Exception):
                    errors.append(f"{type(outcome).__name__}: {outcome}"[:200])
                else:
                    firsts.append(outcome[0])
                    totals.append(outcome[1])

            print("-" * 64)
            print(f"success: {len(totals)}/{CHAT_REQUESTS}  errors: {len(errors)}  wall: {wall:.2f}s")
            if firsts:
                print(
                    "first token: "
                    f"p50={percentile(firsts, 0.50) * 1000:.0f}ms "
                    f"p95={percentile(firsts, 0.95) * 1000:.0f}ms"
                )
            if totals:
                print(
                    "total:       "
                    f"p50={percentile(totals, 0.50) * 1000:.0f}ms "
                    f"p95={percentile(totals, 0.95) * 1000:.0f}ms"
                )
            if errors:
                print("first error:", errors[0])

            return 1 if errors else 0
        finally:
            await delete_temp_user(client, admin_headers, user_id)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
