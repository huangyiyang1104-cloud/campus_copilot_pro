"""HTTP 读写压测：认证、课表、会话、学习计划、整表覆盖写。

运行：
    cd backend
    python -m tests.load.api_load

可用环境变量：
    LOAD_BASE_URL / LOAD_ADMIN_USERNAME / LOAD_ADMIN_PASSWORD
    LOAD_READ_REQUESTS / LOAD_CONCURRENCY
    LOAD_WRITE_REQUESTS / LOAD_WRITE_CONCURRENCY
"""

from __future__ import annotations

import asyncio
import sys

import httpx

from .common import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    BASE_URL,
    READ_CONCURRENCY,
    READ_REQUESTS,
    WRITE_CONCURRENCY,
    WRITE_REQUESTS,
    create_temp_user,
    delete_temp_user,
    headers_for,
    login,
    print_report,
    run_scenario,
)

COURSE_COUNT = 3


def course_payload(index: int) -> dict:
    return {
        "courses": [
            {
                "name": f"压测课程{slot}",
                "teacher": "压测老师",
                "room": f"教{slot}楼",
                "day": slot,
                "section": 1,
                "color": f"linear-gradient(135deg,#0000{index:02x},#1111{index:02x})",
            }
            for slot in range(1, COURSE_COUNT + 1)
        ]
    }


async def main() -> int:
    print(f"target: {BASE_URL}")
    print(f"read: {READ_REQUESTS} requests / concurrency {READ_CONCURRENCY}")
    print(f"write: {WRITE_REQUESTS} requests / concurrency {WRITE_CONCURRENCY}")

    limits = httpx.Limits(max_connections=max(READ_CONCURRENCY, WRITE_CONCURRENCY) * 2)
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=30,
        limits=limits,
    ) as client:
        admin_token = await login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
        admin_headers = headers_for(admin_token)
        user_id, username, password = await create_temp_user(
            client, admin_headers, "load_api"
        )

        try:
            token = await login(client, username, password)
            headers = headers_for(token)

            async def get_status(path: str) -> int:
                response = await client.get(path, headers=headers)
                return response.status_code

            scenarios = []
            for path in (
                "/api/auth/me",
                "/api/courses",
                "/api/conversations",
                "/api/study-plans",
            ):
                scenario = await run_scenario(
                    f"GET {path}",
                    READ_REQUESTS,
                    READ_CONCURRENCY,
                    lambda _index, path=path: get_status(path),
                )
                scenarios.append(scenario)

            payloads = [course_payload(index) for index in range(WRITE_REQUESTS)]

            async def put_courses(index: int) -> int:
                response = await client.put(
                    "/api/courses",
                    headers=headers,
                    json=payloads[index],
                )
                return response.status_code

            write_scenario = await run_scenario(
                "PUT /api/courses",
                WRITE_REQUESTS,
                WRITE_CONCURRENCY,
                put_courses,
            )
            scenarios.append(write_scenario)

            final = await client.get("/api/courses", headers=headers)
            final_rows = len(final.json()) if final.status_code == 200 else -1
            print(f"final courses: {final_rows} rows (expected {COURSE_COUNT})")

            errors = print_report(scenarios)
            if final_rows != COURSE_COUNT:
                print("FAIL: concurrent course replacement left an inconsistent row count")
                errors += 1

            return 1 if errors else 0
        finally:
            await delete_temp_user(client, admin_headers, user_id)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
