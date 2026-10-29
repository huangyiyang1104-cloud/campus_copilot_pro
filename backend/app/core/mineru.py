import io
import time
import zipfile

import httpx
from pypdf import PdfReader, PdfWriter

from app.core.config import settings

POLL_INTERVAL = 3
POLL_TIMEOUT = 600
MINERU_MAX_PAGES = 200


class MinerUError(RuntimeError):
    """MinerU 解析失败，错误信息直接写进资料表的 error_msg"""


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.MINERU_API_TOKEN}",
    }


def _check(resp: httpx.Response) -> dict:
    try:
        payload = resp.json()
    except ValueError:
        raise MinerUError(f"MinerU 返回了非 JSON 内容（HTTP {resp.status_code}）") from None

    if resp.status_code != 200 or payload.get("code") != 0:
        raise MinerUError(payload.get("msg") or f"MinerU 请求失败（HTTP {resp.status_code}）")

    return payload


def _download_markdown(zip_url: str) -> str:
    resp = httpx.get(zip_url, timeout=120)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        names = archive.namelist()
        target = next((name for name in names if name.endswith("full.md")), None)
        if target is None:
            target = next((name for name in names if name.endswith(".md")), None)
        if target is None:
            raise MinerUError("MinerU 结果包里没有 Markdown 文件")

        return archive.read(target).decode("utf-8", errors="ignore")


def _split_pdf(file_bytes: bytes, file_name: str) -> list[tuple[bytes, str]]:
    """MinerU 单文件最多 200 页，超过就按 200 页拆成多个 PDF"""
    reader = PdfReader(io.BytesIO(file_bytes), strict=False)
    total_pages = len(reader.pages)
    if total_pages <= MINERU_MAX_PAGES:
        return [(file_bytes, file_name)]

    stem = file_name.rsplit(".", 1)[0]
    parts: list[tuple[bytes, str]] = []

    for start in range(0, total_pages, MINERU_MAX_PAGES):
        writer = PdfWriter()
        for page in reader.pages[start : start + MINERU_MAX_PAGES]:
            writer.add_page(page)

        buffer = io.BytesIO()
        writer.write(buffer)
        index = len(parts) + 1
        parts.append((buffer.getvalue(), f"{stem}_part{index}.pdf"))

    return parts


def convert_to_markdown(file_bytes: bytes, file_name: str) -> str:
    """把 PDF / Word / PPT / Excel 交给 MinerU 转成 Markdown"""
    if not settings.MINERU_API_TOKEN:
        raise MinerUError("没有配置 MINERU_API_TOKEN")

    suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if suffix == "pdf":
        try:
            parts = _split_pdf(file_bytes, file_name)
        except Exception:
            # 读不了页数就按原文件提交，让 MinerU 返回它自己的错误
            parts = [(file_bytes, file_name)]

        if len(parts) > 1:
            results: list[str] = []
            for index, (part_bytes, part_name) in enumerate(parts, start=1):
                try:
                    results.append(_convert_single(part_bytes, part_name))
                except MinerUError as exc:
                    raise MinerUError(
                        f"PDF 第 {index}/{len(parts)} 部分解析失败：{exc}"
                    ) from exc
            return "\n\n".join(results)

    return _convert_single(file_bytes, file_name)


def _convert_single(file_bytes: bytes, file_name: str) -> str:
    base = settings.MINERU_BASE_URL.rstrip("/")

    # 1. 申请上传链接
    with httpx.Client(timeout=60) as client:
        created = client.post(
            f"{base}/file-urls/batch",
            headers=_headers(),
            json={
                "files": [{"name": file_name}],
                "model_version": settings.MINERU_MODEL_VERSION,
                "language": "ch",
            },
        )
        payload = _check(created)

        batch_id = payload["data"]["batch_id"]
        upload_url = payload["data"]["file_urls"][0]

        # 2. PUT 上传，不能设置 Content-Type
        uploaded = client.put(upload_url, content=file_bytes, timeout=180)
        if uploaded.status_code != 200:
            raise MinerUError(f"文件上传到 MinerU 失败（HTTP {uploaded.status_code}）")

        # 3. 轮询结果
        deadline = time.monotonic() + POLL_TIMEOUT
        while time.monotonic() < deadline:
            result = _check(
                client.get(f"{base}/extract-results/batch/{batch_id}", headers=_headers())
            )

            items = result["data"].get("extract_result") or []
            item = next(
                (row for row in items if row.get("file_name") == file_name),
                items[0] if items else None,
            )
            if item is None:
                time.sleep(POLL_INTERVAL)
                continue

            state = item.get("state")
            if state == "done":
                zip_url = item.get("full_zip_url")
                if not zip_url:
                    raise MinerUError("MinerU 解析完成但没有返回结果包地址")
                return _download_markdown(zip_url)

            if state == "failed":
                raise MinerUError(item.get("err_msg") or "MinerU 解析失败")

            time.sleep(POLL_INTERVAL)

    raise MinerUError("MinerU 解析超时，请稍后重试")
