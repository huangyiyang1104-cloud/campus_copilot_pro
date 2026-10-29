import re

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.core.mineru import convert_to_markdown

SUPPORTED_SUFFIXES = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "md"}

_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_TABLE_PATTERN = re.compile(r"<table[^>]*>.*?</table>", re.DOTALL | re.IGNORECASE)
_ROW_PATTERN = re.compile(r"<tr[^>]*>.*?</tr>", re.DOTALL | re.IGNORECASE)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
MIN_CHUNK_SIZE = 120
TABLE_MAX_SIZE = 900

_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]

_header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=_HEADERS, strip_headers=True)

_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
)


def extract_text(data: bytes, file_name: str) -> str:
    """Markdown 直接读，其它格式交给 MinerU 转成 Markdown"""
    suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"不支持的文件类型：{suffix}")

    if suffix == "md":
        return data.decode("utf-8", errors="ignore")

    markdown = convert_to_markdown(data, file_name)
    # 去掉指向本地图片的引用，切片时只保留文字和表格
    return _IMAGE_PATTERN.sub("", markdown)


def _section_path(metadata: dict) -> str:
    titles = [metadata.get(key, "").replace("**", "").strip() for key in ("h1", "h2", "h3")]
    return " > ".join(title for title in titles if title)


def _merge_small_chunks(chunks: list[str]) -> list[str]:
    """同一小节里的短块合并，避免出现一堆几十字的碎片"""
    merged: list[str] = []
    buffer = ""

    for chunk in chunks:
        if not buffer:
            buffer = chunk
        elif len(buffer) < MIN_CHUNK_SIZE or len(buffer) + len(chunk) <= CHUNK_SIZE:
            buffer = f"{buffer}\n{chunk}"
        else:
            merged.append(buffer)
            buffer = chunk

    if buffer:
        merged.append(buffer)
    return merged


def _split_table(table: str) -> list[str]:
    """表格整块保留；太长时按行拆，并且每块都重复表头"""
    if len(table) <= TABLE_MAX_SIZE:
        return [table]

    rows = _ROW_PATTERN.findall(table)
    if len(rows) <= 2:
        return [table]

    header = rows[0]
    groups: list[list[str]] = []
    current: list[str] = []
    current_size = 0

    for row in rows[1:]:
        if current and current_size + len(row) > TABLE_MAX_SIZE:
            groups.append(current)
            current = []
            current_size = 0
        current.append(row)
        current_size += len(row)

    if current:
        groups.append(current)

    return [f"<table>{header}{''.join(group)}</table>" for group in groups]


def _split_section(content: str, path: str) -> list[str]:
    chunks: list[str] = []
    last_end = 0

    def flush_text(raw: str) -> None:
        if not raw.strip():
            return
        pieces = _text_splitter.split_text(raw)
        for piece in _merge_small_chunks([piece for piece in pieces if piece.strip()]):
            body = piece.strip()
            chunks.append(f"【{path}】\n{body}" if path else body)

    for match in _TABLE_PATTERN.finditer(content):
        flush_text(content[last_end : match.start()])
        for table in _split_table(match.group(0)):
            table_body = table.strip()
            chunks.append(f"【{path}】（表格）\n{table_body}" if path else f"（表格）\n{table_body}")
        last_end = match.end()

    flush_text(content[last_end:])
    return chunks


def split_text(text: str) -> list[str]:
    """按 Markdown 标题切小节，节内按长度二次切；表格不跨块切断"""
    if not text.strip():
        return []

    sections = _header_splitter.split_text(text)
    if not sections:
        return []

    chunks: list[str] = []
    for section in sections:
        path = _section_path(section.metadata)
        chunks.extend(_split_section(section.page_content, path))

    return [chunk.strip() for chunk in chunks if chunk.strip()]
