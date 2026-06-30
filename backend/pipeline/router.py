# backend/pipeline/router.py
"""智能路由 — 确定性规则优先，LLM 兜底。"""
import logging
from pathlib import Path

import httpx

from app.config import settings
from app.models.pipeline_enums import ContentType

logger = logging.getLogger(__name__)

# 扩展名 → ContentType 映射
EXTENSION_MAP: dict[str, ContentType] = {
    ".pdf": ContentType.pdf,
    ".xlsx": ContentType.excel,
    ".xls": ContentType.excel,
    ".csv": ContentType.csv,
    ".json": ContentType.json,
    ".html": ContentType.html,
    ".htm": ContentType.html,
}

# MIME type → ContentType 映射
MIME_MAP: dict[str, ContentType] = {
    "application/pdf": ContentType.pdf,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ContentType.excel,
    "application/vnd.ms-excel": ContentType.excel,
    "text/csv": ContentType.csv,
    "application/json": ContentType.json,
    "text/html": ContentType.html,
}


def route_by_filename(filename: str) -> ContentType | None:
    """根据文件扩展名判断类型。"""
    ext = Path(filename).suffix.lower()
    return EXTENSION_MAP.get(ext)


def route_by_mime(mime_type: str) -> ContentType | None:
    """根据 MIME type 判断类型。"""
    return MIME_MAP.get(mime_type.lower())


def route_by_url(url: str) -> ContentType | None:
    """根据 URL 后缀判断类型，无后缀返回 html（爬虫默认）。"""
    from urllib.parse import urlparse
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext:
        return EXTENSION_MAP.get(ext)
    # 无文件后缀的 URL 默认按 HTML 处理
    return ContentType.html


def route_by_llm(content_preview: str) -> ContentType:
    """LLM 兜底路由 — 取内容前 500 字符调用轻量 LLM。"""
    prompt = (
        "判断以下内容的文件类型，只返回一个词：html / pdf / excel / csv / json\n"
        f"内容片段：\n{content_preview[:500]}"
    )
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    try:
        resp = httpx.post(
            f"{settings.LLM_BASE_URL}chat/completions",
            headers=headers,
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        answer = result["choices"][0]["message"]["content"].strip().lower()
        for ct in ContentType:
            if ct.value in answer:
                return ct
    except Exception as e:
        logger.warning("LLM 路由失败，默认 html: %s", e)
    return ContentType.html


def route_content(
    filename: str | None = None,
    mime_type: str | None = None,
    url: str | None = None,
    content_preview: str | None = None,
) -> ContentType:
    """智能路由主入口 — 确定性规则优先，LLM 兜底。

    优先级：filename > mime_type > url > LLM（仅当有 content_preview 时）> 默认 html
    """
    if filename:
        ct = route_by_filename(filename)
        if ct:
            return ct
    if mime_type:
        ct = route_by_mime(mime_type)
        if ct:
            return ct
    if url:
        ct = route_by_url(url)
        if ct:
            return ct
    if content_preview and settings.LLM_API_KEY:
        return route_by_llm(content_preview)
    return ContentType.html
