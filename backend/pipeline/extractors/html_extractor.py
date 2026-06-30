# backend/pipeline/extractors/html_extractor.py
"""HTML 文本提取器 — 从现有 extractor.py 的 _clean_html 提取为独立模块。"""
from bs4 import BeautifulSoup

from app.models.pipeline_enums import ContentType
from pipeline.extractors import ExtractResult


def extract_html(html_content: str) -> ExtractResult:
    """将 HTML 清洗为纯文本，保留表格结构。"""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return ExtractResult(
        text="\n".join(lines),
        content_type=ContentType.html,
        metadata={"char_count": len(text)},
    )
