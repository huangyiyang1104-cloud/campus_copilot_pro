"""Tavily 联网搜索与网页正文读取。

搜索走 LangChain 自带的 TavilySearchResults，结果只取标题、链接和摘要；
需要全文时由模型再调用 read_web_page，读取前会拦截内网地址。
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper

from app.core.config import settings

MAX_RESULTS = 5
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_PAGE_CHARS = 6000
TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
}


class WebError(RuntimeError):
    pass


def _validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise WebError("只支持 http/https 链接")
    if not parsed.hostname:
        raise WebError("链接缺少域名")

    try:
        addresses = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise WebError(f"域名解析失败：{parsed.hostname}") from exc

    for info in addresses:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise WebError("不允许访问内网或保留地址")

    return url


def search_web(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """LangChain Tavily 搜索结果，返回 title/url/snippet。"""
    query = (query or "").strip()
    if not query:
        raise WebError("搜索词为空")
    if not settings.TAVILY_API_KEY:
        raise WebError("没有配置 TAVILY_API_KEY")

    limit = max(1, min(int(max_results), 8))
    try:
        wrapper = TavilySearchAPIWrapper(tavily_api_key=settings.TAVILY_API_KEY)
        search = TavilySearchResults(
            api_wrapper=wrapper,
            max_results=limit,
            search_depth="advanced",
            include_raw_content=False,
            include_answer=False,
        )
        raw = search.invoke({"query": query})
    except Exception as exc:
        raise WebError(f"Tavily 搜索失败：{type(exc).__name__}") from exc

    if isinstance(raw, dict):
        raw = raw.get("results", [])
    if not isinstance(raw, list):
        raise WebError("Tavily 返回格式异常")

    results: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue

        url = str(item.get("url") or "").strip()
        if not url.startswith(("http://", "https://")) or url in seen:
            continue

        snippet = str(item.get("content") or item.get("snippet") or "")
        seen.add(url)
        results.append(
            {
                "title": str(item.get("title") or url)[:200],
                "url": url[:500],
                "snippet": re.sub(r"\s+", " ", snippet)[:400],
            }
        )
        if len(results) >= limit:
            break

    return results


def read_web_page(url: str) -> dict:
    """打开公开网页并提取正文，带大小、协议和 SSRF 基础防护。"""
    current = (url or "").strip()
    if not current:
        raise WebError("链接为空")

    with httpx.Client(
        headers=HEADERS,
        timeout=TIMEOUT,
        follow_redirects=False,
    ) as client:
        for _ in range(4):
            _validate_public_url(current)
            try:
                response = client.get(current)
            except Exception as exc:
                raise WebError(f"网页请求失败：{type(exc).__name__}") from exc

            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    raise WebError("网页重定向缺少地址")
                current = urljoin(current, location)
                continue
            break
        else:
            raise WebError("重定向次数过多")

    if response.status_code >= 400:
        raise WebError(f"网页返回 HTTP {response.status_code}")

    content_type = response.headers.get("content-type", "").lower()
    if content_type and not any(
        item in content_type for item in ("text/html", "text/plain", "xhtml")
    ):
        raise WebError("这个链接不是网页文本")

    if len(response.content) > MAX_PAGE_BYTES:
        raise WebError("网页内容过大，已拒绝读取")

    _validate_public_url(str(response.url))
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    for tag in soup(
        ["script", "style", "noscript", "nav", "header", "footer", "form", "svg"]
    ):
        tag.decompose()

    lines = [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]
    text = re.sub(r"\n{2,}", "\n", "\n".join(lines))

    return {
        "title": title[:200],
        "url": str(response.url),
        "text": text[:MAX_PAGE_CHARS],
        "truncated": len(text) > MAX_PAGE_CHARS,
    }
