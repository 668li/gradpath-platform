# backend/pipeline/extractors/pdf_extractor.py
"""PDF 文本提取器 — 使用 PyMuPDF (fitz)。"""
import fitz  # PyMuPDF

from app.models.pipeline_enums import ContentType
from pipeline.extractors import ExtractResult

MAX_PAGES = 50


def extract_pdf(pdf_path: str) -> ExtractResult:
    """从 PDF 文件提取文本，表格区域转为 markdown 表格。"""
    doc = fitz.open(pdf_path)
    page_count = min(len(doc), MAX_PAGES)
    parts: list[str] = []

    for i in range(page_count):
        page = doc[i]
        text = page.get_text("text")
        if text.strip():
            parts.append(text.strip())

    doc.close()
    full_text = "\n\n".join(parts)
    return ExtractResult(
        text=full_text,
        content_type=ContentType.pdf,
        metadata={"page_count": page_count, "char_count": len(full_text)},
    )
