# backend/pipeline/extractors/csv_extractor.py
"""CSV 文本提取器 — 无新依赖。"""
import csv
import io

from app.models.pipeline_enums import ContentType
from pipeline.extractors import ExtractResult


def extract_csv(csv_content: str) -> ExtractResult:
    """读取 CSV 内容，检测分隔符，转为 markdown 表格。"""
    # 检测分隔符
    delimiter = ","
    first_line = csv_content.split("\n")[0] if csv_content else ""
    if "\t" in first_line:
        delimiter = "\t"
    elif ";" in first_line and "," not in first_line:
        delimiter = ";"

    reader = csv.reader(io.StringIO(csv_content), delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return ExtractResult(
            text="",
            content_type=ContentType.csv,
            metadata={"row_count": 0},
        )

    col_count = len(rows[0])
    parts = ["| " + " | ".join(rows[0]) + " |"]
    parts.append("| " + " | ".join(["---"] * col_count) + " |")
    for row in rows[1:]:
        # 补齐列数
        padded = list(row) + [""] * (col_count - len(row))
        parts.append("| " + " | ".join(padded[:col_count]) + " |")

    full_text = "\n".join(parts)
    return ExtractResult(
        text=full_text,
        content_type=ContentType.csv,
        metadata={"row_count": len(rows), "col_count": col_count},
    )
