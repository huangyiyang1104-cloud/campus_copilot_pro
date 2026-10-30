from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import httpx

BASE_URL = os.getenv("LOAD_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_USERNAME = os.getenv("LOAD_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("LOAD_ADMIN_PASSWORD", "admin123")

READ_REQUESTS = int(os.getenv("LOAD_READ_REQUESTS", "100"))
READ_CONCURRENCY = int(os.getenv("LOAD_CONCURRENCY", "20"))
WRITE_REQUESTS = int(os.getenv("LOAD_WRITE_REQUESTS", "5"))
WRITE_CONCURRENCY = int(os.getenv("LOAD_WRITE_CONCURRENCY", "5"))


@dataclass
class Scenario:
    name: str
    latencies: list[float] = field(default_factory=list)
    codes: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    wall: float = 0.0

    @property
    def success(self) -> int:
        return sum(1 for code in self.codes if 200 <= code < 300)

    @property
    def failed(self) -> int:
        return len(self.latencies) - self.success


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * ratio))
    return ordered[index]


def headers_for(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(client: httpx.AsyncClient, username: str, password: str) -> str:
    response = await client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def create_temp_user(
    client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    prefix: str,
) -> tuple[int, str, str]:
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "load-test-123"
    response = await client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "username": username,
            "password": password,
            "name": "压测账号",
            "role": "student",
            "status": 1,
        },
    )
    response.raise_for_status()
    return response.json()["id"], username, password


async def delete_temp_user(
    client: httpx.AsyncClient,
    admin_headers: dict[str, str],
    user_id: int,
) -> None:
    try:
        await client.delete(f"/api/users/{user_id}", headers=admin_headers)
    except Exception:
        pass


async def run_scenario(
    name: str,
    count: int,
    concurrency: int,
    call: Callable[[int], Awaitable[int]],
) -> Scenario:
    """并发执行 count 个请求，记录状态码和端到端耗时"""
    scenario = Scenario(name)
    semaphore = asyncio.Semaphore(concurrency)

    async def one(index: int) -> None:
        async with semaphore:
            started = time.perf_counter()
            try:
                scenario.codes.append(await call(index))
            except Exception as exc:
                scenario.errors.append(f"{type(exc).__name__}: {exc}"[:200])
            finally:
                scenario.latencies.append(time.perf_counter() - started)

    wall_started = time.perf_counter()
    await asyncio.gather(*(one(index) for index in range(count)))
    scenario.wall = time.perf_counter() - wall_started
    return scenario


def print_report(scenarios: list[Scenario]) -> int:
    header = f"{'scenario':<26} {'n':>5} {'ok':>5} {'err':>5} {'rps':>7} {'p50(ms)':>9} {'p95(ms)':>9} {'p99(ms)':>9}"
    print(header)
    print("-" * len(header))

    total_errors = 0
    for scenario in scenarios:
        total_errors += scenario.failed
        rps = len(scenario.latencies) / scenario.wall if scenario.wall else 0
        print(
            f"{scenario.name:<26} {len(scenario.latencies):>5} {scenario.success:>5} "
            f"{scenario.failed:>5} {rps:>7.1f} "
            f"{percentile(scenario.latencies, 0.50) * 1000:>9.1f} "
            f"{percentile(scenario.latencies, 0.95) * 1000:>9.1f} "
            f"{percentile(scenario.latencies, 0.99) * 1000:>9.1f}"
        )
        if scenario.errors:
            print(f"  first error: {scenario.errors[0]}")

    return total_errors
