"""PDF/EPUB 转 Markdown 服务。

使用 VikParuchuri/marker 进行高质量 PDF→Markdown 转换。
当 marker 不可用时，回退到 PyPDF2 的基础文本提取。

使用方式：
    from app.services.pdf_converter import convert_pdf_to_markdown
    markdown = convert_pdf_to_markdown("path/to/file.pdf")
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def convert_pdf_to_markdown(
    file_path: str | Path,
    *,
    use_marker: bool = True,
    max_pages: int | None = None,
) -> str:
    """将 PDF 文件转换为 Markdown 文本。

    Args:
        file_path: PDF 文件路径
        use_marker: 是否尝试使用 marker（高质量但需要 GPU/大模型）。
                    若为 True 但 marker 不可用，自动回退到 PyPDF2。
        max_pages: 最多转换的页数（None 表示全部）

    Returns:
        Markdown 格式的文本

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不支持
        RuntimeError: 转换失败
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    if path.suffix.lower() not in (".pdf",):
        raise ValueError(f"仅支持 PDF 格式，收到: {path.suffix}")

    if use_marker:
        try:
            return _convert_with_marker(path, max_pages)
        except ImportError:
            logger.info("marker-pdf 未安装，回退到 PyPDF2")
        except Exception as e:
            logger.warning("marker 转换失败，回退到 PyPDF2: %s", e)

    return _convert_with_pypdf2(path, max_pages)


def _convert_with_marker(path: Path, max_pages: int | None) -> str:
    """使用 marker-pdf 进行高质量转换。

    marker 使用深度学习模型识别文档结构（标题/段落/表格/图片），
    输出高质量的 Markdown，适合学术报告、技术文档等。

    注意：marker 需要安装 marker-pdf 包并下载模型（首次约 2GB）。
    """
    from marker.converters.pdf import PdfConverter  # type: ignore[import-not-found]
    from marker.models import create_model_dict  # type: ignore[import-not-found]

    converter = PdfConverter(artifact_dict=create_model_dict())

    # marker 的配置选项
    config = {
        "format_lines": True,
        "force_ocr": False,
        "strip_existing_ocr": False,
    }

    if max_pages is not None:
        config["max_pages"] = max_pages

    rendered = converter(str(path))
    return rendered.markdown


def _convert_with_pypdf2(path: Path, max_pages: int | None) -> str:
    """使用 PyPDF2 进行基础文本提取（回退方案）。

    仅提取纯文本，不识别文档结构，但无需 GPU/大模型。
    """
    try:
        from PyPDF2 import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]
        except ImportError:
            raise RuntimeError(
                "PDF 转换需要安装 marker-pdf 或 pypdf：pip install marker-pdf 或 pip install pypdf"
            )

    reader = PdfReader(str(path))
    total_pages = len(reader.pages)

    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    text_parts: list[str] = []
    for i in range(total_pages):
        page = reader.pages[i]
        text = page.extract_text() or ""
        text_parts.append(text)

    # 简单的 Markdown 格式化：每页之间添加分隔
    markdown = "\n\n---\n\n".join(text_parts)

    if not markdown.strip():
        logger.warning("PDF 文本提取结果为空（可能是扫描件，需要 OCR）: %s", path)

    return markdown


def convert_epub_to_markdown(file_path: str | Path) -> str:
    """将 EPUB 文件转换为 Markdown 文本。

    使用 ebooklib 提取 EPUB 内容并转为 Markdown。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    if path.suffix.lower() != ".epub":
        raise ValueError(f"仅支持 EPUB 格式，收到: {path.suffix}")

    try:
        import ebooklib  # type: ignore[import-not-found]
        from ebooklib import epub  # type: ignore[import-not-found]
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]
    except ImportError:
        raise RuntimeError(
            "EPUB 转换需要安装 ebooklib 和 beautifulsoup4：pip install ebooklib beautifulsoup4"
        )

    book = epub.read_epub(str(path))
    text_parts: list[str] = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")

        # 将 HTML 转为简单 Markdown
        for element in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            tag = element.name
            text = element.get_text(strip=True)
            if not text:
                continue
            if tag == "h1":
                text_parts.append(f"\n# {text}\n")
            elif tag == "h2":
                text_parts.append(f"\n## {text}\n")
            elif tag == "h3":
                text_parts.append(f"\n### {text}\n")
            else:
                text_parts.append(text)

    return "\n\n".join(text_parts)


# 可选依赖声明（用于文档和安装提示）
OPTIONAL_DEPENDENCIES = {
    "marker": "marker-pdf>=0.3.0",  # 高质量 PDF 转换（需要 GPU）
    "pypdf": "pypdf>=4.0.0",  # 基础 PDF 文本提取
    "epub": ["ebooklib>=0.18", "beautifulsoup4>=4.12.0"],  # EPUB 转换
}
