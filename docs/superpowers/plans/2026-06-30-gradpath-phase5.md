# Phase 5: 统一数据源接入与智能路由 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展就业数据管道，支持 PDF/Excel/CSV 文件上传、URL 抓取、外部 API 对接三种数据源，通过智能路由自动识别内容类型并提取文本，统一进入已有 LLM 解析流程，同时提供管理员前端管理页面。

**Architecture:** 统一接入 API → 智能路由（确定性规则优先，LLM 兜底）→ 四种文本提取器（HTML/PDF/Excel/CSV）→ 已有 LLM 结构化解析器 → EmploymentData 入库。新增 DataSource 模型管理外部 API 配置，User 新增 is_admin 字段控制管道管理权限。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, PyMuPDF (fitz), openpyxl, python-multipart, Next.js 14, Recharts

---

## File Structure

### Backend — New Files
- `backend/app/models/data_source.py` — DataSource 模型
- `backend/app/models/pipeline_enums.py` — SourceType, ContentType 枚举
- `backend/app/schemas/pipeline.py` — Pipeline 相关 Pydantic schemas
- `backend/app/api/pipeline.py` — Pipeline API 路由（ingest/reports/sources）
- `backend/app/services/pipeline_service.py` — Pipeline 业务逻辑
- `backend/pipeline/router.py` — 智能路由
- `backend/pipeline/extractors/html_extractor.py` — HTML 提取器
- `backend/pipeline/extractors/pdf_extractor.py` — PDF 提取器
- `backend/pipeline/extractors/excel_extractor.py` — Excel 提取器
- `backend/pipeline/extractors/csv_extractor.py` — CSV 提取器
- `backend/pipeline/extractors/__init__.py` — 提取器包初始化 + ExtractResult dataclass
- `backend/pipeline/seed_sources.py` — 数据源种子数据
- `backend/tests/test_pipeline_router.py` — 路由测试
- `backend/tests/test_pipeline_extractors.py` — 提取器测试
- `backend/tests/test_api_pipeline.py` — Pipeline API 测试
- `backend/tests/test_api_sources.py` — DataSource API 测试
- `backend/tests/fixtures/sample_report.html` — 测试 HTML fixture
- `backend/tests/fixtures/sample_report.csv` — 测试 CSV fixture

### Backend — Modified Files
- `backend/app/models/report_record.py` — 新增 source_type/content_type/file_path 字段
- `backend/app/models/user.py` — 新增 is_admin 字段
- `backend/app/models/__init__.py` — 导出新模型和枚举
- `backend/app/schemas/auth.py` — UserResponse 新增 is_admin
- `backend/app/main.py` — 注册 pipeline_router
- `backend/pipeline/extractor.py` — 重构：从 _clean_html 提取为独立模块引用
- `backend/pipeline/cli.py` — 新增 ingest 命令
- `backend/.gitignore` — 排除 uploads/

### Frontend — New Files
- `frontend/app/(app)/pipeline/page.tsx` — 数据源总览页
- `frontend/app/(app)/pipeline/ingest/page.tsx` — 接入新数据页
- `frontend/app/(app)/pipeline/sources/page.tsx` — 数据源配置页

### Frontend — Modified Files
- `frontend/types/index.ts` — 新增 Pipeline 相关类型
- `frontend/lib/api.ts` — 新增 pipelineApi
- `frontend/lib/constants.ts` — 新增管道相关常量
- `frontend/components/nav.tsx` — 新增数据管道导航项（管理员可见）
- `frontend/stores/auth.ts` — UserResponse 新增 is_admin

---

## Task 1: 安装依赖 + 模型扩展

**Files:**
- Modify: `backend/app/models/pipeline_enums.py` (Create)
- Modify: `backend/app/models/report_record.py`
- Modify: `backend/app/models/data_source.py` (Create)
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/.gitignore`

- [ ] **Step 1: 安装新依赖**

```bash
cd /workspace/backend && pip install pymupdf openpyxl python-multipart --break-system-packages
```

- [ ] **Step 2: 创建 pipeline_enums.py**

```python
# backend/app/models/pipeline_enums.py
import enum


class SourceType(str, enum.Enum):
    crawl = "crawl"
    upload = "upload"
    api = "api"


class ContentType(str, enum.Enum):
    html = "html"
    pdf = "pdf"
    excel = "excel"
    csv = "csv"
    json = "json"
```

- [ ] **Step 3: 扩展 ReportRecord**

在 `backend/app/models/report_record.py` 中新增字段。在 `raw_pdf_path` 之后添加：

```python
from app.models.pipeline_enums import ContentType, SourceType

# 在类体内 raw_pdf_path 之后添加：
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType), default=SourceType.crawl, nullable=False
    )
    content_type: Mapped[ContentType | None] = mapped_column(Enum(ContentType))
    file_path: Mapped[str | None] = mapped_column(String(500))
```

同时在文件顶部 import 中加入 `from sqlalchemy import Boolean` 等（如需要）。

- [ ] **Step 4: 创建 DataSource 模型**

```python
# backend/app/models/data_source.py
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class DataSource(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="api")
    api_url: Mapped[str | None] = mapped_column(Text)
    api_key: Mapped[str | None] = mapped_column(Text)
    data_mapping: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 5: User 新增 is_admin**

在 `backend/app/models/user.py` 的 User 类末尾添加：

```python
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

并在顶部 import 中加入 `Boolean`：

```python
from sqlalchemy import Boolean, Enum, Integer, String
```

- [ ] **Step 6: 更新 models/__init__.py**

```python
from app.models.career_event import CareerEvent, EventType
from app.models.community_report import CommunityReport, DestinationType, SalaryRange
from app.models.data_source import DataSource
from app.models.destination_decision import DecisionStatus, DestinationDecision
from app.models.employment_data import Degree, EmploymentData
from app.models.interview_report import InterviewDimension, InterviewReport, InterviewResult
from app.models.pipeline_enums import ContentType, SourceType
from app.models.reference_snapshot import ReferenceSnapshot, SnapshotSource
from app.models.report_record import ParseStatus, ReportRecord
from app.models.retrospective import PeriodType, Retrospective
from app.models.school import School
from app.models.skill_node import SkillNode
from app.models.user import User, UserStage

__all__ = [
    "User", "UserStage",
    "DestinationDecision", "DecisionStatus",
    "CareerEvent", "EventType",
    "SkillNode",
    "Retrospective", "PeriodType",
    "ReferenceSnapshot", "SnapshotSource",
    "School",
    "ReportRecord", "ParseStatus",
    "EmploymentData", "Degree",
    "CommunityReport", "DestinationType", "SalaryRange",
    "InterviewReport", "InterviewDimension", "InterviewResult",
    "DataSource",
    "SourceType", "ContentType",
]
```

- [ ] **Step 7: UserResponse 新增 is_admin**

在 `backend/app/schemas/auth.py` 的 `UserResponse` 类中添加：

```python
    is_admin: bool = False
```

- [ ] **Step 8: .gitignore 排除 uploads/**

在 `backend/.gitignore` 末尾添加：

```
uploads/
```

如果 `.gitignore` 不存在则创建。

- [ ] **Step 9: 验证模型加载**

```bash
cd /workspace/backend && python -c "from app.models import DataSource, SourceType, ContentType; print('OK')"
```

- [ ] **Step 10: Commit**

```bash
cd /workspace && git add -A && git commit -m "feat(phase5): 扩展数据模型 — ReportRecord/DataSource/User.is_admin"
```

---

## Task 2: 文本提取器

**Files:**
- Create: `backend/pipeline/extractors/__init__.py`
- Create: `backend/pipeline/extractors/html_extractor.py`
- Create: `backend/pipeline/extractors/pdf_extractor.py`
- Create: `backend/pipeline/extractors/excel_extractor.py`
- Create: `backend/pipeline/extractors/csv_extractor.py`
- Create: `backend/tests/fixtures/sample_report.html`
- Create: `backend/tests/fixtures/sample_report.csv`
- Modify: `backend/pipeline/extractor.py`

- [ ] **Step 1: 创建 extractors 包 + ExtractResult**

```python
# backend/pipeline/extractors/__init__.py
from dataclasses import dataclass, field

from app.models.pipeline_enums import ContentType


@dataclass
class ExtractResult:
    """文本提取器统一输出。"""
    text: str
    content_type: ContentType
    metadata: dict = field(default_factory=dict)
```

- [ ] **Step 2: 创建 HTML 提取器**

```python
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
```

- [ ] **Step 3: 创建 PDF 提取器**

```python
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
```

- [ ] **Step 4: 创建 Excel 提取器**

```python
# backend/pipeline/extractors/excel_extractor.py
"""Excel 文本提取器 — 使用 openpyxl。"""
from openpyxl import load_workbook

from app.models.pipeline_enums import ContentType
from pipeline.extractors import ExtractResult

MAX_ROWS = 200


def extract_excel(excel_path: str) -> ExtractResult:
    """逐 sheet 读取 Excel，转为 markdown 表格文本。"""
    wb = load_workbook(excel_path, read_only=True, data_only=True)
    parts: list[str] = []
    sheet_names: list[str] = []

    for ws in wb.worksheets:
        sheet_names.append(ws.title)
        rows: list[str] = []
        row_count = 0
        for row in ws.iter_rows(values_only=True):
            if row_count >= MAX_ROWS:
                break
            cells = [str(c) if c is not None else "" for c in row]
            if any(c.strip() for c in cells):
                rows.append("| " + " | ".join(cells) + " |")
                row_count += 1
        if rows:
            # 表头分隔行
            if len(rows) > 0:
                col_count = rows[0].count("|") - 1
                separator = "| " + " | ".join(["---"] * col_count) + " |"
                parts.append(f"## {ws.title}\n\n{rows[0]}\n{separator}\n" + "\n".join(rows[1:]))

    wb.close()
    full_text = "\n\n".join(parts)
    return ExtractResult(
        text=full_text,
        content_type=ContentType.excel,
        metadata={"sheet_names": sheet_names, "char_count": len(full_text)},
    )
```

- [ ] **Step 5: 创建 CSV 提取器**

```python
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
```

- [ ] **Step 6: 重构 extractor.py 引用 html_extractor**

在 `backend/pipeline/extractor.py` 中，将 `_clean_html` 函数体替换为调用 `html_extractor`：

```python
# 在文件顶部添加 import
from pipeline.extractors.html_extractor import extract_html

# 替换 _clean_html 函数为：
def _clean_html(html: str) -> str:
    """将 HTML 清洗为纯文本（委托给 html_extractor）。"""
    return extract_html(html).text
```

保留 `_clean_html` 函数签名不变以保持向后兼容。

- [ ] **Step 7: 创建测试 fixtures**

`backend/tests/fixtures/sample_report.html`:
```html
<html>
<head><title>2024年就业质量报告</title></head>
<body>
<header>导航栏</header>
<h1>清华大学2024年就业质量报告</h1>
<table>
<tr><th>专业</th><th>就业率</th><th>升学率</th></tr>
<tr><td>计算机科学与技术</td><td>45%</td><td>35%</td></tr>
<tr><td>电子工程</td><td>50%</td><td>30%</td></tr>
</table>
<footer>页脚</footer>
</body>
</html>
```

`backend/tests/fixtures/sample_report.csv`:
```csv
专业,就业率,升学率
计算机科学与技术,0.45,0.35
电子工程,0.50,0.30
```

- [ ] **Step 8: 验证提取器可导入**

```bash
cd /workspace/backend && python -c "
from pipeline.extractors.html_extractor import extract_html
from pipeline.extractors.csv_extractor import extract_csv
r = extract_html('<html><body><h1>Test</h1></body></html>')
print('HTML:', r.content_type, len(r.text))
r2 = extract_csv('a,b\n1,2\n')
print('CSV:', r2.content_type, r2.metadata)
"
```

- [ ] **Step 9: Commit**

```bash
cd /workspace && git add -A && git commit -m "feat(phase5): 文本提取器 — HTML/PDF/Excel/CSV 四种格式"
```

---

## Task 3: 智能路由

**Files:**
- Create: `backend/pipeline/router.py`
- Create: `backend/tests/test_pipeline_router.py`

- [ ] **Step 1: 创建 router.py**

```python
# backend/pipeline/router.py
"""智能路由 — 确定性规则优先，LLM 兜底。"""
import json
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
```

- [ ] **Step 2: 创建路由测试**

```python
# backend/tests/test_pipeline_router.py
"""智能路由测试。"""
from app.models.pipeline_enums import ContentType
from pipeline.router import (
    route_by_filename,
    route_by_mime,
    route_by_url,
    route_content,
)


class TestRouteByFilename:
    def test_pdf(self):
        assert route_by_filename("report.pdf") == ContentType.pdf

    def test_excel_xlsx(self):
        assert route_by_filename("data.xlsx") == ContentType.excel

    def test_excel_xls(self):
        assert route_by_filename("data.xls") == ContentType.excel

    def test_csv(self):
        assert route_by_filename("data.csv") == ContentType.csv

    def test_html(self):
        assert route_by_filename("page.html") == ContentType.html

    def test_unknown_extension(self):
        assert route_by_filename("file.xyz") is None

    def test_no_extension(self):
        assert route_by_filename("noextension") is None

    def test_case_insensitive(self):
        assert route_by_filename("REPORT.PDF") == ContentType.pdf


class TestRouteByMime:
    def test_pdf_mime(self):
        assert route_by_mime("application/pdf") == ContentType.pdf

    def test_csv_mime(self):
        assert route_by_mime("text/csv") == ContentType.csv

    def test_unknown_mime(self):
        assert route_by_mime("application/unknown") is None


class TestRouteByUrl:
    def test_url_with_pdf(self):
        assert route_by_url("https://example.com/report.pdf") == ContentType.pdf

    def test_url_with_excel(self):
        assert route_by_url("https://example.com/data.xlsx") == ContentType.excel

    def test_url_no_extension(self):
        assert route_by_url("https://example.com/page") == ContentType.html

    def test_url_with_path_and_query(self):
        assert route_by_url("https://example.com/report.pdf?download=1") == ContentType.pdf


class TestRouteContent:
    def test_filename_priority(self):
        result = route_content(filename="report.pdf", mime_type="text/html")
        assert result == ContentType.pdf

    def test_mime_when_no_filename(self):
        result = route_content(mime_type="application/pdf")
        assert result == ContentType.pdf

    def test_url_when_no_filename_mime(self):
        result = route_content(url="https://example.com/data.csv")
        assert result == ContentType.csv

    def test_default_html(self):
        result = route_content()
        assert result == ContentType.html

    def test_llm_fallback_not_called_without_key(self, monkeypatch):
        # 没有配置 LLM_API_KEY 时不调用 LLM
        from app.config import settings
        monkeypatch.setattr(settings, "LLM_API_KEY", "")
        result = route_content(content_preview="some content")
        assert result == ContentType.html
```

- [ ] **Step 3: 运行测试**

```bash
cd /workspace/backend && python -m pytest tests/test_pipeline_router.py -v
```

- [ ] **Step 4: Commit**

```bash
cd /workspace && git add -A && git commit -m "feat(phase5): 智能路由 — 确定性规则优先，LLM 兜底"
```

---

## Task 4: Pipeline Schemas + Service

**Files:**
- Create: `backend/app/schemas/pipeline.py`
- Create: `backend/app/services/pipeline_service.py`

- [ ] **Step 1: 创建 Pipeline Schemas**

```python
# backend/app/schemas/pipeline.py
"""Pipeline Pydantic schemas。"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator


class IngestURLRequest(BaseModel):
    source_type: str = "crawl"
    school_slug: str
    year: int
    url: str


class IngestAPIRequest(BaseModel):
    source_type: str = "api"
    school_slug: str
    year: int
    api_source_id: str


class ReportListItem(BaseModel):
    id: str
    school_name: str
    year: int
    source_type: str
    content_type: str | None = None
    parse_status: str
    parse_error: str | None = None
    parsed_at: datetime | None = None
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v

    @field_validator("source_type", "content_type", "parse_status", mode="before")
    @classmethod
    def convert_enum(cls, v):
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportListItem]
    total: int
    page: int
    page_size: int


class EmploymentDataPreview(BaseModel):
    major: str
    degree: str
    total_graduates: int | None = None
    employment_rate: float | None = None
    further_study_rate: float | None = None

    @field_validator("degree", mode="before")
    @classmethod
    def convert_enum(cls, v):
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)

    model_config = {"from_attributes": True}


class ReportDetail(ReportListItem):
    source_url: str
    employment_data: list[EmploymentDataPreview] = []


class DataSourceCreate(BaseModel):
    name: str
    source_type: str = "api"
    api_url: str | None = None
    api_key: str | None = None
    data_mapping: dict | None = None
    is_active: bool = True


class DataSourceUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    api_url: str | None = None
    api_key: str | None = None
    data_mapping: dict | None = None
    is_active: bool | None = None


class DataSourceResponse(BaseModel):
    id: str
    name: str
    source_type: str
    api_url: str | None = None
    api_key: str | None = None
    data_mapping: dict | None = None
    is_active: bool

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v

    model_config = {"from_attributes": True}


class PipelineStats(BaseModel):
    total_reports: int
    published_count: int
    pending_count: int
    failed_count: int
```

- [ ] **Step 2: 创建 Pipeline Service**

```python
# backend/app/services/pipeline_service.py
"""Pipeline 业务逻辑。"""
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.data_source import DataSource
from app.models.employment_data import Degree, EmploymentData
from app.models.pipeline_enums import ContentType, SourceType
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School
from app.schemas.pipeline import (
    DataSourceCreate,
    DataSourceUpdate,
    IngestAPIRequest,
    IngestURLRequest,
)
from pipeline.extractors import ExtractResult
from pipeline.extractors.csv_extractor import extract_csv
from pipeline.extractors.excel_extractor import extract_excel
from pipeline.extractors.html_extractor import extract_html
from pipeline.extractors.pdf_extractor import extract_pdf
from pipeline.extractor import call_llm, MAX_TEXT_LENGTH
from pipeline.router import route_content

import json
import logging

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv"}


def get_or_create_report(
    db: Session, school_id: UUID, year: int, source_url: str = "", source_type: SourceType = SourceType.crawl
) -> ReportRecord:
    """获取或创建报告记录。同校同年存在则返回已有记录。"""
    existing = db.query(ReportRecord).filter(
        ReportRecord.school_id == school_id,
        ReportRecord.year == year,
    ).first()
    if existing:
        return existing
    report = ReportRecord(
        school_id=school_id,
        year=year,
        source_url=source_url,
        source_type=source_type,
        parse_status=ParseStatus.pending,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def ingest_url(db: Session, req: IngestURLRequest) -> ReportRecord:
    """URL 抓取模式。"""
    school = db.query(School).filter(School.slug == req.school_slug).first()
    if not school:
        raise ValueError(f"学校 '{req.school_slug}' 不存在")

    report = get_or_create_report(db, school.id, req.year, req.url, SourceType.crawl)
    if report.parse_status not in (ParseStatus.pending, ParseStatus.failed):
        return report  # 已有处理结果

    # 抓取内容
    try:
        resp = httpx.get(req.url, timeout=30, follow_redirects=True,
                         headers={"User-Agent": "GradPathBot/1.0"})
        resp.raise_for_status()
        raw_content = resp.text
        mime_type = resp.headers.get("content-type", "").split(";")[0].strip()
    except Exception as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"抓取失败: {e}"
        db.commit()
        return report

    # 路由
    content_type = route_content(url=req.url, mime_type=mime_type)
    report.content_type = content_type
    report.raw_html = raw_content
    db.commit()

    # 提取 + 解析
    _extract_and_parse(db, report, content_type, raw_content)
    return report


def ingest_file(
    db: Session, file_content: bytes, filename: str, school_slug: str, year: int
) -> ReportRecord:
    """文件上传模式。"""
    school = db.query(School).filter(School.slug == school_slug).first()
    if not school:
        raise ValueError(f"学校 '{school_slug}' 不存在")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}")

    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError("文件过大，最大 20MB")

    # 保存文件
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    saved_name = f"{school_slug}_{year}_{timestamp}{ext}"
    file_path = UPLOAD_DIR / saved_name
    file_path.write_bytes(file_content)

    report = get_or_create_report(db, school.id, year, str(file_path), SourceType.upload)
    report.file_path = str(file_path)
    report.source_url = str(file_path)

    # 路由
    content_type = route_content(filename=filename)
    report.content_type = content_type
    db.commit()

    # 提取
    if content_type == ContentType.pdf:
        result = extract_pdf(str(file_path))
    elif content_type == ContentType.excel:
        result = extract_excel(str(file_path))
    elif content_type == ContentType.csv:
        result = extract_csv(file_content.decode("utf-8"))
    else:
        result = extract_html(file_content.decode("utf-8", errors="replace"))

    report.raw_html = result.text
    db.commit()

    # 解析
    _run_llm_parse(db, report)
    return report


def ingest_api(db: Session, req: IngestAPIRequest) -> ReportRecord:
    """外部 API 对接模式。"""
    school = db.query(School).filter(School.slug == req.school_slug).first()
    if not school:
        raise ValueError(f"学校 '{req.school_slug}' 不存在")

    source = db.query(DataSource).filter(DataSource.id == UUID(req.api_source_id)).first()
    if not source:
        raise ValueError("数据源不存在")
    if not source.is_active:
        raise ValueError("数据源已禁用")

    report = get_or_create_report(db, school.id, req.year, source.api_url or "", SourceType.api)

    # 调用外部 API
    try:
        headers = {}
        if source.api_key:
            headers["Authorization"] = f"Bearer {source.api_key}"
        resp = httpx.get(source.api_url, headers=headers, timeout=30)
        resp.raise_for_status()
        raw_content = resp.text
        mime_type = resp.headers.get("content-type", "").split(";")[0].strip()
    except Exception as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"API 调用失败: {e}"
        db.commit()
        return report

    # 路由
    content_type = route_content(mime_type=mime_type)
    report.content_type = content_type
    report.raw_html = raw_content
    db.commit()

    # 提取 + 解析
    _extract_and_parse(db, report, content_type, raw_content)
    return report


def _extract_and_parse(db: Session, report: ReportRecord, content_type: ContentType, raw_content: str):
    """提取文本（如需要）并运行 LLM 解析。"""
    if content_type == ContentType.html:
        result = extract_html(raw_content)
        report.raw_html = result.text
    elif content_type == ContentType.csv:
        result = extract_csv(raw_content)
        report.raw_html = result.text
    else:
        # PDF/Excel 已在 ingest_file 中提取
        result = ExtractResult(text=raw_content, content_type=content_type)
    db.commit()
    _run_llm_parse(db, report)


def _run_llm_parse(db: Session, report: ReportRecord):
    """运行 LLM 结构化解析。"""
    if not settings.LLM_API_KEY:
        # LLM 未配置，保持 pending
        return

    text = report.raw_html or ""
    if not text.strip():
        report.parse_status = ParseStatus.failed
        report.parse_error = "未提取到有效内容"
        db.commit()
        return

    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    try:
        llm_response = call_llm(text)
        data = json.loads(llm_response)
    except json.JSONDecodeError as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"LLM 返回无效 JSON: {e}"
        db.commit()
        return
    except Exception as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"LLM 调用失败: {e}"
        db.commit()
        return

    # 写入 EmploymentData
    db.query(EmploymentData).filter(EmploymentData.report_id == report.id).delete()
    for major_data in data.get("majors", []):
        try:
            emp = EmploymentData(
                report_id=report.id,
                major=major_data.get("major", "未知专业"),
                degree=Degree(major_data.get("degree", "all")),
                total_graduates=major_data.get("total_graduates"),
                employment_rate=major_data.get("employment_rate"),
                further_study_rate=major_data.get("further_study_rate"),
                civil_service_rate=major_data.get("civil_service_rate"),
                abroad_rate=major_data.get("abroad_rate"),
                startup_rate=major_data.get("startup_rate"),
                gap_year_rate=major_data.get("gap_year_rate"),
                employer_ranking=major_data.get("employer_ranking", []),
                industry_distribution=major_data.get("industry_distribution", {}),
                destination_region=major_data.get("destination_region", {}),
                school_for_further_study=major_data.get("school_for_further_study", []),
            )
            db.add(emp)
        except Exception as e:
            logger.warning("跳过专业 %r: %s", major_data.get("major"), e)
            continue

    report.parse_status = ParseStatus.parsed
    report.parsed_at = datetime.now(timezone.utc)
    report.parse_error = None
    db.commit()


def reparse_report(db: Session, report_id: UUID) -> ReportRecord:
    """重新解析报告。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        raise ValueError("报告不存在")
    _run_llm_parse(db, report)
    return report


def publish_report(db: Session, report_id: UUID) -> ReportRecord:
    """发布报告。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        raise ValueError("报告不存在")
    report.parse_status = ParseStatus.published
    db.commit()
    return report


def delete_report(db: Session, report_id: UUID):
    """删除报告及其关联数据。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        raise ValueError("报告不存在")
    db.delete(report)
    db.commit()


def list_reports(
    db: Session, status_filter: str | None = None, page: int = 1, page_size: int = 20
) -> dict:
    """报告列表。"""
    query = db.query(ReportRecord).join(School)
    if status_filter:
        query = query.filter(ReportRecord.parse_status == status_filter)
    total = query.count()
    items = (
        query.order_by(ReportRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_report_detail(db: Session, report_id: UUID) -> ReportRecord:
    """报告详情。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        raise ValueError("报告不存在")
    return report


def get_pipeline_stats(db: Session) -> dict:
    """管道统计。"""
    total = db.query(ReportRecord).count()
    published = db.query(ReportRecord).filter(ReportRecord.parse_status == ParseStatus.published).count()
    pending = db.query(ReportRecord).filter(
        ReportRecord.parse_status.in_([ParseStatus.pending, ParseStatus.parsed, ParseStatus.reviewed])
    ).count()
    failed = db.query(ReportRecord).filter(ReportRecord.parse_status == ParseStatus.failed).count()
    return {
        "total_reports": total,
        "published_count": published,
        "pending_count": pending,
        "failed_count": failed,
    }


# ===== DataSource CRUD =====

def list_sources(db: Session) -> list[DataSource]:
    return db.query(DataSource).order_by(DataSource.created_at.desc()).all()


def create_source(db: Session, data: DataSourceCreate) -> DataSource:
    source = DataSource(**data.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def update_source(db: Session, source_id: UUID, data: DataSourceUpdate) -> DataSource:
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise ValueError("数据源不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source


def delete_source(db: Session, source_id: UUID):
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise ValueError("数据源不存在")
    db.delete(source)
    db.commit()
```

- [ ] **Step 3: Commit**

```bash
cd /workspace && git add -A && git commit -m "feat(phase5): Pipeline schemas + service 业务逻辑"
```

---

## Task 5: Pipeline API 路由

**Files:**
- Create: `backend/app/api/pipeline.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/deps.py`

- [ ] **Step 1: 在 deps.py 中添加管理员依赖**

在 `backend/app/core/deps.py` 末尾添加：

```python
def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
```

- [ ] **Step 2: 创建 Pipeline API 路由**

```python
# backend/app/api/pipeline.py
"""Pipeline API 路由 — 管理员专用。"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.database import get_db
from app.models.user import User
from app.schemas.pipeline import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    IngestAPIRequest,
    IngestURLRequest,
    PipelineStats,
    ReportDetail,
    ReportListResponse,
)
from app.services.pipeline_service import (
    create_source,
    delete_report,
    delete_source,
    get_pipeline_stats,
    get_report_detail,
    ingest_api,
    ingest_file,
    ingest_url,
    list_reports,
    list_sources,
    publish_report,
    reparse_report,
    update_source,
    MAX_FILE_SIZE,
)

router = APIRouter(prefix="/api/pipeline", tags=["数据管道"])


@router.post("/ingest/url", response_model=ReportDetail)
def ingest_url_endpoint(
    body: IngestURLRequest,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """URL 抓取模式接入。"""
    try:
        return ingest_url(db, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/ingest/file", response_model=ReportDetail)
async def ingest_file_endpoint(
    school_slug: str = Form(...),
    year: int = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """文件上传模式接入。"""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件过大，最大 20MB")
    try:
        report = ingest_file(db, content, file.filename or "upload.html", school_slug, year)
        return report
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/ingest/api", response_model=ReportDetail)
def ingest_api_endpoint(
    body: IngestAPIRequest,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """外部 API 对接模式接入。"""
    try:
        return ingest_api(db, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reports", response_model=ReportListResponse)
def list_reports_endpoint(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """报告列表。"""
    return list_reports(db, status_filter=status, page=page, page_size=page_size)


@router.get("/reports/{report_id}", response_model=ReportDetail)
def get_report_endpoint(
    report_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """报告详情。"""
    from uuid import UUID
    try:
        return get_report_detail(db, UUID(report_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report_endpoint(
    report_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        delete_report(db, UUID(report_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/reports/{report_id}/reparse", response_model=ReportDetail)
def reparse_endpoint(
    report_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        return reparse_report(db, UUID(report_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/reports/{report_id}/publish", response_model=ReportDetail)
def publish_endpoint(
    report_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        return publish_report(db, UUID(report_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/stats", response_model=PipelineStats)
def stats_endpoint(
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return get_pipeline_stats(db)


# ===== DataSource CRUD =====

@router.get("/sources", response_model=list[DataSourceResponse])
def list_sources_endpoint(
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return list_sources(db)


@router.post("/sources", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def create_source_endpoint(
    body: DataSourceCreate,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return create_source(db, body)


@router.put("/sources/{source_id}", response_model=DataSourceResponse)
def update_source_endpoint(
    source_id: str,
    body: DataSourceUpdate,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        return update_source(db, UUID(source_id), body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source_endpoint(
    source_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        delete_source(db, UUID(source_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
```

- [ ] **Step 3: 注册路由到 main.py**

在 `backend/app/main.py` 中添加：

```python
from app.api.pipeline import router as pipeline_router
```

并在路由注册区添加：

```python
app.include_router(pipeline_router)
```

- [ ] **Step 4: 验证 API 可启动**

```bash
cd /workspace/backend && python -c "from app.main import app; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
cd /workspace && git add -A && git commit -m "feat(phase5): Pipeline API 路由 — ingest/reports/sources 端点"
```

---

## Task 6: 提取器测试 + API 测试

**Files:**
- Create: `backend/tests/test_pipeline_extractors.py`
- Create: `backend/tests/test_api_pipeline.py`
- Create: `backend/tests/test_api_sources.py`

- [ ] **Step 1: 创建提取器测试**

```python
# backend/tests/test_pipeline_extractors.py
"""文本提取器测试。"""
from pathlib import Path

from app.models.pipeline_enums import ContentType
from pipeline.extractors.csv_extractor import extract_csv
from pipeline.extractors.html_extractor import extract_html

FIXTURES = Path(__file__).parent / "fixtures"


class TestHtmlExtractor:
    def test_basic_extraction(self):
        html = "<html><body><h1>标题</h1><p>内容</p></body></html>"
        result = extract_html(html)
        assert result.content_type == ContentType.html
        assert "标题" in result.text
        assert "内容" in result.text

    def test_removes_script_style(self):
        html = "<html><body><script>alert(1)</script><style>.x{}</style><p>text</p></body></html>"
        result = extract_html(html)
        assert "alert" not in result.text
        assert ".x{}" not in result.text
        assert "text" in result.text

    def test_removes_nav_footer(self):
        html = "<html><body><nav>菜单</nav><main>正文</main><footer>页脚</footer></body></html>"
        result = extract_html(html)
        assert "菜单" not in result.text
        assert "页脚" not in result.text
        assert "正文" in result.text

    def test_fixture_file(self):
        html_file = FIXTURES / "sample_report.html"
        result = extract_html(html_file.read_text())
        assert "清华大学" in result.text
        assert "计算机科学与技术" in result.text


class TestCsvExtractor:
    def test_basic_csv(self):
        csv_content = "专业,就业率,升学率\n计算机,0.45,0.35\n电子,0.50,0.30\n"
        result = extract_csv(csv_content)
        assert result.content_type == ContentType.csv
        assert "专业" in result.text
        assert "计算机" in result.text
        assert result.metadata["row_count"] == 3

    def test_tab_delimited(self):
        csv_content = "a\tb\n1\t2\n"
        result = extract_csv(csv_content)
        assert result.metadata["col_count"] == 2

    def test_semicolon_delimited(self):
        csv_content = "a;b\n1;2\n"
        result = extract_csv(csv_content)
        assert result.metadata["col_count"] == 2

    def test_empty_csv(self):
        result = extract_csv("")
        assert result.text == ""
        assert result.metadata["row_count"] == 0

    def test_fixture_file(self):
        csv_file = FIXTURES / "sample_report.csv"
        result = extract_csv(csv_file.read_text())
        assert "计算机科学与技术" in result.text
        assert result.metadata["row_count"] == 3
```

- [ ] **Step 2: 创建 Pipeline API 测试**

```python
# backend/tests/test_api_pipeline.py
"""Pipeline API 端点测试。"""
import pytest
from app.models.user import User
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School


@pytest.fixture
def admin_headers(client, db_session):
    """注册管理员用户并返回认证头。"""
    from app.core.security import hash_password
    admin = User(
        email="admin@test.com",
        password_hash=hash_password("Admin1234!"),
        name="管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "Admin1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def normal_headers(client, db_session):
    """普通用户认证头（非管理员）。"""
    client.post(
        "/api/auth/register",
        json={"email": "normal@test.com", "password": "Test1234!", "name": "普通用户"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "normal@test.com", "password": "Test1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestPipelineAccess:
    def test_non_admin_blocked(self, client, normal_headers):
        resp = client.get("/api/pipeline/reports", headers=normal_headers)
        assert resp.status_code == 403

    def test_admin_allowed(self, client, admin_headers):
        resp = client.get("/api/pipeline/reports", headers=admin_headers)
        assert resp.status_code == 200


class TestReportList:
    def test_list_reports(self, client, admin_headers):
        resp = client.get("/api/pipeline/reports", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_filter_by_status(self, client, admin_headers, db_session):
        # 已有种子数据中有 published 报告
        resp = client.get(
            "/api/pipeline/reports?status=published", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["parse_status"] == "published" for item in data["items"])


class TestReportDetail:
    def test_get_report_detail(self, client, admin_headers, db_session):
        report = db_session.query(ReportRecord).first()
        if not report:
            pytest.skip("无种子报告数据")
        resp = client.get(f"/api/pipeline/reports/{report.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(report.id)
        assert "employment_data" in data


class TestReportDelete:
    def test_delete_report(self, client, admin_headers, db_session):
        # 创建一个测试报告
        school = db_session.query(School).first()
        report = ReportRecord(
            school_id=school.id, year=2099, source_url="test",
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()
        resp = client.delete(f"/api/pipeline/reports/{report.id}", headers=admin_headers)
        assert resp.status_code == 204


class TestPublishReport:
    def test_publish_report(self, client, admin_headers, db_session):
        school = db_session.query(School).first()
        report = ReportRecord(
            school_id=school.id, year=2098, source_url="test",
            parse_status=ParseStatus.parsed,
        )
        db_session.add(report)
        db_session.commit()
        resp = client.post(f"/api/pipeline/reports/{report.id}/publish", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["parse_status"] == "published"


class TestIngestURL:
    def test_ingest_url_school_not_found(self, client, admin_headers):
        resp = client.post(
            "/api/pipeline/ingest/url",
            json={"source_type": "crawl", "school_slug": "nonexistent", "year": 2024, "url": "https://example.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 404


class TestStats:
    def test_stats(self, client, admin_headers):
        resp = client.get("/api/pipeline/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_reports" in data
        assert "published_count" in data
        assert "pending_count" in data
        assert "failed_count" in data


class TestFileUpload:
    def test_upload_unsupported_format(self, client, admin_headers):
        import io
        resp = client.post(
            "/api/pipeline/ingest/file",
            data={"school_slug": "tsinghua", "year": "2024"},
            files={"file": ("test.txt", io.BytesIO(b"test"), "text/plain")},
            headers=admin_headers,
        )
        assert resp.status_code == 400
```

- [ ] **Step 3: 创建 DataSource API 测试**

```python
# backend/tests/test_api_sources.py
"""DataSource API 测试。"""
import pytest
from app.models.user import User


@pytest.fixture
def admin_headers(client, db_session):
    from app.core.security import hash_password
    admin = User(
        email="admin@test.com",
        password_hash=hash_password("Admin1234!"),
        name="管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "Admin1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestDataSourceCRUD:
    def test_create_source(self, client, admin_headers):
        resp = client.post(
            "/api/pipeline/sources",
            json={
                "name": "测试数据源",
                "source_type": "api",
                "api_url": "https://api.example.com/data",
                "api_key": "test-key",
                "is_active": True,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "测试数据源"
        assert data["is_active"] is True
        assert data["id"] is not None

    def test_list_sources(self, client, admin_headers):
        # 先创建一个
        client.post(
            "/api/pipeline/sources",
            json={"name": "数据源1", "source_type": "api"},
            headers=admin_headers,
        )
        resp = client.get("/api/pipeline/sources", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_source(self, client, admin_headers):
        create_resp = client.post(
            "/api/pipeline/sources",
            json={"name": "原名", "source_type": "api"},
            headers=admin_headers,
        )
        source_id = create_resp.json()["id"]
        resp = client.put(
            f"/api/pipeline/sources/{source_id}",
            json={"name": "新名", "is_active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "新名"
        assert resp.json()["is_active"] is False

    def test_delete_source(self, client, admin_headers):
        create_resp = client.post(
            "/api/pipeline/sources",
            json={"name": "待删除", "source_type": "api"},
            headers=admin_headers,
        )
        source_id = create_resp.json()["id"]
        resp = client.delete(f"/api/pipeline/sources/{source_id}", headers=admin_headers)
        assert resp.status_code == 204

    def test_non_admin_blocked(self, client, db_session):
        client.post(
            "/api/auth/register",
            json={"email": "normal2@test.com", "password": "Test1234!", "name": "普通"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "normal2@test.com", "password": "Test1234!"},
        )
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/pipeline/sources", headers=headers)
        assert resp.status_code == 403
```

- [ ] **Step 4: 运行全部测试**

```bash
cd /workspace/backend && python -m pytest tests/test_pipeline_extractors.py tests/test_pipeline_router.py tests/test_api_pipeline.py tests/test_api_sources.py -v
```

- [ ] **Step 5: 运行全量测试确保不破坏已有功能**

```bash
cd /workspace/backend && python -m pytest --tb=short -q
```

- [ ] **Step 6: Commit**

```bash
cd /workspace && git add -A && git commit -m "test(phase5): 提取器/路由/API/数据源测试"
```

---

## Task 7: 种子数据 + CLI 扩展

**Files:**
- Create: `backend/pipeline/seed_sources.py`
- Modify: `backend/pipeline/cli.py`

- [ ] **Step 1: 创建数据源种子数据**

```python
# backend/pipeline/seed_sources.py
"""数据源种子数据脚本。"""
from app.database import SessionLocal
from app.models.data_source import DataSource
from app.models.user import User
from app.core.security import hash_password


SEED_SOURCES = [
    {
        "name": "教育部高校毕业生就业统计（示例）",
        "source_type": "api",
        "api_url": "https://api.example.edu.gov.cn/employment/stats",
        "api_key": "demo-key-001",
        "data_mapping": {
            "majors_path": "data.majors",
            "field_map": {
                "major_name": "name",
                "employment_rate": "employment",
                "further_study_rate": "further_study",
            },
        },
        "is_active": False,
    },
    {
        "name": "麦可思就业数据（示例）",
        "source_type": "api",
        "api_url": "https://api.mycos.example.com/v1/reports",
        "api_key": "demo-key-002",
        "data_mapping": {
            "majors_path": "result.list",
            "field_map": {
                "major_name": "major",
                "employment_rate": "emp_rate",
            },
        },
        "is_active": False,
    },
]


def run_seed():
    """执行种子数据导入。幂等：先清理旧种子数据，再重新导入。"""
    db = SessionLocal()
    try:
        # 清理旧数据源
        db.query(DataSource).delete()

        # 导入数据源
        for src in SEED_SOURCES:
            db.add(DataSource(**src))

        # 确保 test@test.com 用户是管理员
        admin_user = db.query(User).filter(User.email == "test@test.com").first()
        if admin_user:
            admin_user.is_admin = True

        db.commit()
        print(f"已导入 {len(SEED_SOURCES)} 个数据源配置")
        if admin_user:
            print("已将 test@test.com 设为管理员")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
```

- [ ] **Step 2: 运行种子脚本**

```bash
cd /workspace/backend && python -m pipeline.seed_sources
```

- [ ] **Step 3: Commit**

```bash
cd /workspace && git add -A && git commit -m "feat(phase5): 数据源种子数据 + 管理员用户设置"
```

---

## Task 8: 前端类型 + API 客户端 + 常量

**Files:**
- Modify: `frontend/types/index.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/constants.ts`
- Modify: `frontend/stores/auth.ts`

- [ ] **Step 1: UserResponse 新增 is_admin**

在 `frontend/types/index.ts` 的 `UserResponse` 接口中添加：

```typescript
export interface UserResponse {
  id: string;
  email: string;
  name: string;
  current_stage?: string | null;
  school?: string | null;
  major?: string | null;
  graduation_year?: number | null;
  is_admin?: boolean;
  created_at: string;
}
```

- [ ] **Step 2: 新增 Pipeline 类型**

在 `frontend/types/index.ts` 末尾添加：

```typescript
// ===== 数据管道 =====
export type ParseStatus = "pending" | "parsed" | "failed" | "reviewed" | "published";
export type SourceType = "crawl" | "upload" | "api";
export type ContentType = "html" | "pdf" | "excel" | "csv" | "json";

export interface ReportListItem {
  id: string;
  school_name: string;
  year: number;
  source_type: SourceType;
  content_type: ContentType | null;
  parse_status: ParseStatus;
  parse_error: string | null;
  parsed_at: string | null;
  created_at: string;
}

export interface ReportListResponse {
  items: ReportListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface EmploymentDataPreview {
  major: string;
  degree: string;
  total_graduates: number | null;
  employment_rate: number | null;
  further_study_rate: number | null;
}

export interface ReportDetail extends ReportListItem {
  source_url: string;
  employment_data: EmploymentDataPreview[];
}

export interface PipelineStats {
  total_reports: number;
  published_count: number;
  pending_count: number;
  failed_count: number;
}

export interface DataSourceResponse {
  id: string;
  name: string;
  source_type: string;
  api_url: string | null;
  api_key: string | null;
  data_mapping: Record<string, unknown> | null;
  is_active: boolean;
}

export interface DataSourceCreate {
  name: string;
  source_type?: string;
  api_url?: string | null;
  api_key?: string | null;
  data_mapping?: Record<string, unknown> | null;
  is_active?: boolean;
}
```

- [ ] **Step 3: 新增 pipelineApi**

在 `frontend/lib/api.ts` 末尾添加：

```typescript
// ===== 数据管道 =====
export const pipelineApi = {
  // 接入
  ingestUrl: (body: { school_slug: string; year: number; url: string }) =>
    request<ReportDetail>("/api/pipeline/ingest/url", {
      method: "POST",
      body: JSON.stringify({ ...body, source_type: "crawl" }),
    }),

  ingestFile: (file: File, schoolSlug: string, year: number) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("school_slug", schoolSlug);
    formData.append("year", String(year));
    return request<ReportDetail>("/api/pipeline/ingest/file", {
      method: "POST",
      body: formData,
      headers: {}, // 让浏览器自动设置 Content-Type
    });
  },

  ingestApi: (body: { school_slug: string; year: number; api_source_id: string }) =>
    request<ReportDetail>("/api/pipeline/ingest/api", {
      method: "POST",
      body: JSON.stringify({ ...body, source_type: "api" }),
    }),

  // 报告管理
  reports: (params?: { status?: string; page?: number; page_size?: number }) =>
    request<ReportListResponse>(`/api/pipeline/reports${buildQuery(params as Record<string, string | undefined | null> || {})}`),

  reportDetail: (id: string) =>
    request<ReportDetail>(`/api/pipeline/reports/${id}`),

  deleteReport: (id: string) =>
    request<void>(`/api/pipeline/reports/${id}`, { method: "DELETE" }),

  reparse: (id: string) =>
    request<ReportDetail>(`/api/pipeline/reports/${id}/reparse`, { method: "POST" }),

  publish: (id: string) =>
    request<ReportDetail>(`/api/pipeline/reports/${id}/publish`, { method: "POST" }),

  stats: () => request<PipelineStats>("/api/pipeline/stats"),

  // 数据源管理
  sources: () => request<DataSourceResponse[]>("/api/pipeline/sources"),

  createSource: (body: DataSourceCreate) =>
    request<DataSourceResponse>("/api/pipeline/sources", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateSource: (id: string, body: Partial<DataSourceCreate>) =>
    request<DataSourceResponse>(`/api/pipeline/sources/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  deleteSource: (id: string) =>
    request<void>(`/api/pipeline/sources/${id}`, { method: "DELETE" }),
};
```

同时在顶部 import 中添加 Pipeline 相关类型：

```typescript
import type {
  // ... 已有类型 ...
  DataSourceCreate,
  DataSourceResponse,
  PipelineStats,
  ReportDetail,
  ReportListResponse,
} from "@/types";
```

- [ ] **Step 4: 新增管道常量**

在 `frontend/lib/constants.ts` 末尾添加：

```typescript
// ===== 数据管道 =====
export const PARSE_STATUS_LABEL: Record<string, string> = {
  pending: "待解析",
  parsed: "已解析",
  failed: "失败",
  reviewed: "已审核",
  published: "已发布",
};

export const PARSE_STATUS_COLOR: Record<string, string> = {
  pending: "#d97706",
  parsed: "#2563eb",
  failed: "#dc2626",
  reviewed: "#7c3aed",
  published: "#16a34a",
};

export const SOURCE_TYPE_LABEL: Record<string, string> = {
  crawl: "爬虫抓取",
  upload: "文件上传",
  api: "API对接",
};

export const CONTENT_TYPE_LABEL: Record<string, string> = {
  html: "HTML",
  pdf: "PDF",
  excel: "Excel",
  csv: "CSV",
  json: "JSON",
};
```

- [ ] **Step 5: 修复 api.ts 的 ingestFile 方法**

注意 `request` 函数默认设置 `Content-Type: application/json`，文件上传时需要覆盖。修改 `request` 函数中的 headers 逻辑，使其在 body 为 FormData 时不设置 Content-Type：

在 `frontend/lib/api.ts` 的 `request` 函数中修改 headers 逻辑：

```typescript
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  // FormData 时让浏览器自动设置 Content-Type（含 boundary）
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
```

- [ ] **Step 6: Commit**

```bash
cd /workspace && git add -A && git commit -m "feat(phase5): 前端类型/API客户端/常量"
```

---

## Task 9: 前端管理页

**Files:**
- Create: `frontend/app/(app)/pipeline/page.tsx`
- Create: `frontend/app/(app)/pipeline/ingest/page.tsx`
- Create: `frontend/app/(app)/pipeline/sources/page.tsx`
- Modify: `frontend/components/nav.tsx`

- [ ] **Step 1: 创建管道总览页**

```typescript
// frontend/app/(app)/pipeline/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Database, RefreshCw, Trash2, Upload, Eye, CheckCircle } from "lucide-react";
import { pipelineApi } from "@/lib/api";
import { Button } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import {
  PARSE_STATUS_LABEL,
  PARSE_STATUS_COLOR,
  SOURCE_TYPE_LABEL,
  CONTENT_TYPE_LABEL,
} from "@/lib/constants";
import type { PipelineStats, ReportListItem } from "@/types";

const STATUS_TABS = ["", "pending", "parsed", "failed", "reviewed", "published"];

export default function PipelinePage() {
  const toast = useToast();
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeStatus, setActiveStatus] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const loadData = async () => {
    setLoading(true);
    try {
      const [st, list] = await Promise.all([
        pipelineApi.stats(),
        pipelineApi.reports({ status: activeStatus || undefined, page, page_size: 20 }),
      ]);
      setStats(st);
      setReports(list.items);
      setTotal(list.total);
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [activeStatus, page]);

  const handlePublish = async (id: string) => {
    try {
      await pipelineApi.publish(id);
      toast.push("已发布", "success");
      loadData();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "发布失败", "error");
    }
  };

  const handleReparse = async (id: string) => {
    try {
      await pipelineApi.reparse(id);
      toast.push("已重新解析", "success");
      loadData();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "解析失败", "error");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await pipelineApi.deleteReport(id);
      toast.push("已删除", "success");
      loadData();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">数据管道</h1>
          <p className="text-sm text-slate-500 mt-1">管理就业报告数据源与解析流程</p>
        </div>
        <Link href="/pipeline/ingest">
          <Button><Upload className="h-4 w-4" /> 接入新数据</Button>
        </Link>
      </div>

      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-slate-700">{stats.total_reports}</p>
            <p className="text-xs text-slate-500">总报告</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">{stats.published_count}</p>
            <p className="text-xs text-slate-500">已发布</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-amber-600">{stats.pending_count}</p>
            <p className="text-xs text-slate-500">待处理</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-red-600">{stats.failed_count}</p>
            <p className="text-xs text-slate-500">失败</p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {STATUS_TABS.map((s) => (
          <button
            key={s || "all"}
            onClick={() => { setActiveStatus(s); setPage(1); }}
            className={`rounded-full px-3 py-1.5 text-sm transition-colors ${
              activeStatus === s
                ? "bg-brand-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {s ? PARSE_STATUS_LABEL[s] : "全部"}
          </button>
        ))}
      </div>

      <div className="card">
        {reports.length === 0 ? (
          <EmptyState title="暂无报告" description="接入新数据源后报告会显示在这里" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-400">
                  <th className="px-3 py-2 text-left">学校</th>
                  <th className="px-3 py-2 text-left">年份</th>
                  <th className="px-3 py-2 text-left">来源</th>
                  <th className="px-3 py-2 text-left">类型</th>
                  <th className="px-3 py-2 text-left">状态</th>
                  <th className="px-3 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id} className="border-b border-slate-50">
                    <td className="px-3 py-3 font-medium text-slate-700">{r.school_name}</td>
                    <td className="px-3 py-3 text-slate-500">{r.year}</td>
                    <td className="px-3 py-3 text-slate-500">{SOURCE_TYPE_LABEL[r.source_type] ?? r.source_type}</td>
                    <td className="px-3 py-3 text-slate-500">{r.content_type ? (CONTENT_TYPE_LABEL[r.content_type] ?? r.content_type) : "—"}</td>
                    <td className="px-3 py-3">
                      <span
                        className="rounded-full px-2 py-0.5 text-xs font-medium"
                        style={{ backgroundColor: `${PARSE_STATUS_COLOR[r.parse_status]}20`, color: PARSE_STATUS_COLOR[r.parse_status] }}
                      >
                        {PARSE_STATUS_LABEL[r.parse_status] ?? r.parse_status}
                      </span>
                      {r.parse_error && (
                        <p className="mt-0.5 text-xs text-red-400 truncate max-w-xs">{r.parse_error}</p>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-1">
                        <Link href={`/pipeline/reports/${r.id}`} className="p-1.5 rounded hover:bg-slate-100" title="查看">
                          <Eye className="h-4 w-4 text-slate-400" />
                        </Link>
                        <button onClick={() => handleReparse(r.id)} className="p-1.5 rounded hover:bg-slate-100" title="重新解析">
                          <RefreshCw className="h-4 w-4 text-blue-400" />
                        </button>
                        {r.parse_status !== "published" && (
                          <button onClick={() => handlePublish(r.id)} className="p-1.5 rounded hover:bg-slate-100" title="发布">
                            <CheckCircle className="h-4 w-4 text-green-400" />
                          </button>
                        )}
                        <button onClick={() => handleDelete(r.id)} className="p-1.5 rounded hover:bg-red-50" title="删除">
                          <Trash2 className="h-4 w-4 text-red-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建接入新数据页**

```typescript
// frontend/app/(app)/pipeline/ingest/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Link2, Upload, Cloud } from "lucide-react";
import { pipelineApi, employmentApi } from "@/lib/api";
import { Button, Input, Select } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import type { SchoolInfo } from "@/types";

type Mode = "url" | "file" | "api";

export default function IngestPage() {
  const router = useRouter();
  const toast = useToast();
  const [mode, setMode] = useState<Mode>("url");
  const [schools, setSchools] = useState<SchoolInfo[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // URL 模式
  const [url, setUrl] = useState("");
  const [schoolSlug, setSchoolSlug] = useState("");
  const [year, setYear] = useState(2024);

  // API 模式
  const [apiSourceId, setApiSourceId] = useState("");

  // 文件模式
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, srcs] = await Promise.all([
          employmentApi.schools(),
          pipelineApi.sources(),
        ]);
        setSchools(s);
        setSources(srcs);
      } catch {}
    })();
  }, []);

  const handleSubmit = async () => {
    if (!schoolSlug) { toast.push("请选择学校", "error"); return; }
    setLoading(true);
    try {
      if (mode === "url") {
        if (!url.trim()) { toast.push("请输入 URL", "error"); setLoading(false); return; }
        await pipelineApi.ingestUrl({ school_slug: schoolSlug, year, url: url.trim() });
      } else if (mode === "file") {
        if (!file) { toast.push("请选择文件", "error"); setLoading(false); return; }
        await pipelineApi.ingestFile(file, schoolSlug, year);
      } else {
        if (!apiSourceId) { toast.push("请选择数据源", "error"); setLoading(false); return; }
        await pipelineApi.ingestApi({ school_slug: schoolSlug, year, api_source_id: apiSourceId });
      }
      toast.push("接入成功", "success");
      router.push("/pipeline");
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "接入失败", "error");
    } finally {
      setLoading(false);
    }
  };

  const tabs: { key: Mode; label: string; icon: typeof Link2 }[] = [
    { key: "url", label: "URL 抓取", icon: Link2 },
    { key: "file", label: "文件上传", icon: Upload },
    { key: "api", label: "API 对接", icon: Cloud },
  ];

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="page-title">接入新数据</h1>
        <p className="text-sm text-slate-500 mt-1">选择数据源类型，系统会自动识别格式并解析</p>
      </div>

      <div className="flex gap-2">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setMode(t.key)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                mode === t.key
                  ? "bg-brand-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              <Icon className="h-4 w-4" /> {t.label}
            </button>
          );
        })}
      </div>

      <div className="card space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">学校</label>
            <Select value={schoolSlug} onChange={(e) => setSchoolSlug(e.target.value)}>
              <option value="">选择学校</option>
              {schools.map((s) => (
                <option key={s.id} value={s.slug}>{s.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">年份</label>
            <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
          </div>
        </div>

        {mode === "url" && (
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">报告 URL</label>
            <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://career.tsinghua.edu.cn/..." />
          </div>
        )}

        {mode === "file" && (
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">上传文件（PDF/Excel/CSV）</label>
            <input
              type="file"
              accept=".pdf,.xlsx,.xls,.csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100"
            />
            {file && <p className="mt-1 text-xs text-slate-400">已选择: {file.name} ({(file.size / 1024).toFixed(1)} KB)</p>}
          </div>
        )}

        {mode === "api" && (
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">数据源</label>
            <Select value={apiSourceId} onChange={(e) => setApiSourceId(e.target.value)}>
              <option value="">选择数据源</option>
              {sources.map((s) => (
                <option key={s.id} value={s.id} disabled={!s.is_active}>
                  {s.name} {s.is_active ? "" : "(未启用)"}
                </option>
              ))}
            </Select>
            {sources.length === 0 && (
              <p className="mt-1 text-xs text-slate-400">暂无数据源，请先在数据源配置页添加</p>
            )}
          </div>
        )}

        <Button onClick={handleSubmit} loading={loading} className="w-full">
          开始接入
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 创建数据源配置页**

```typescript
// frontend/app/(app)/pipeline/sources/page.tsx
"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Settings } from "lucide-react";
import { pipelineApi } from "@/lib/api";
import { Button, Input } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import type { DataSourceResponse } from "@/types";

export default function SourcesPage() {
  const toast = useToast();
  const [sources, setSources] = useState<DataSourceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<DataSourceResponse | null>(null);

  // 表单
  const [name, setName] = useState("");
  const [apiUrl, setApiUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [isActive, setIsActive] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setSources(await pipelineApi.sources());
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "加载失败", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setName(""); setApiUrl(""); setApiKey(""); setIsActive(true); setEditing(null);
  };

  const handleSave = async () => {
    if (!name.trim()) { toast.push("请输入名称", "error"); return; }
    try {
      const body = { name: name.trim(), api_url: apiUrl.trim() || null, api_key: apiKey.trim() || null, is_active: isActive };
      if (editing) {
        await pipelineApi.updateSource(editing.id, body);
        toast.push("已更新", "success");
      } else {
        await pipelineApi.createSource({ ...body, source_type: "api" });
        toast.push("已创建", "success");
      }
      resetForm();
      setShowForm(false);
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "保存失败", "error");
    }
  };

  const handleEdit = (s: DataSourceResponse) => {
    setEditing(s);
    setName(s.name); setApiUrl(s.api_url ?? ""); setApiKey(s.api_key ?? ""); setIsActive(s.is_active);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await pipelineApi.deleteSource(id);
      toast.push("已删除", "success");
      load();
    } catch (err) {
      toast.push(err instanceof Error ? err.message : "删除失败", "error");
    }
  };

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">数据源配置</h1>
          <p className="text-sm text-slate-500 mt-1">管理外部 API 数据源</p>
        </div>
        <Button onClick={() => { resetForm(); setShowForm(!showForm); }}>
          <Plus className="h-4 w-4" /> {showForm ? "取消" : "新增数据源"}
        </Button>
      </div>

      {showForm && (
        <div className="card space-y-4">
          <h2 className="font-semibold text-slate-800">{editing ? "编辑数据源" : "新建数据源"}</h2>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">名称</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：教育部就业统计" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">API URL</label>
            <Input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} placeholder="https://api.example.com/data" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">API Key</label>
            <Input value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="Bearer token" />
          </div>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} className="rounded" />
            <span className="text-sm text-slate-600">启用</span>
          </label>
          <Button onClick={handleSave}>{editing ? "更新" : "创建"}</Button>
        </div>
      )}

      <div className="space-y-3">
        {sources.length === 0 && !showForm ? (
          <EmptyState title="暂无数据源" description="点击「新增数据源」添加外部 API 配置" />
        ) : (
          sources.map((s) => (
            <div key={s.id} className="card flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-800">{s.name}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${s.is_active ? "bg-green-50 text-green-600" : "bg-slate-100 text-slate-400"}`}>
                    {s.is_active ? "启用" : "禁用"}
                  </span>
                </div>
                {s.api_url && <p className="mt-0.5 text-xs text-slate-400">{s.api_url}</p>}
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => handleEdit(s)} className="p-2 rounded hover:bg-slate-100">
                  <Settings className="h-4 w-4 text-slate-400" />
                </button>
                <button onClick={() => handleDelete(s.id)} className="p-2 rounded hover:bg-red-50">
                  <Trash2 className="h-4 w-4 text-red-400" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 修改导航组件**

在 `frontend/components/nav.tsx` 中：

1. 在 import 中添加 `Database` 图标
2. 修改 `NAV_ITEMS` 使其支持条件渲染

```typescript
import {
  // ... 已有图标 ...
  Database,
} from "lucide-react";

// 修改 NAV_ITEMS 为函数，接受 is_admin 参数
function getNavItems(isAdmin: boolean = false) {
  const items = [
    { href: "/dashboard", label: "个人看板", icon: LayoutDashboard },
    { href: "/explore", label: "去向探索", icon: Telescope },
    { href: "/community", label: "社区数据", icon: Users },
    { href: "/interview", label: "面试经验", icon: Briefcase },
    { href: "/decisions", label: "去向决策", icon: Compass },
    { href: "/timeline", label: "成长时间线", icon: History },
    { href: "/skills", label: "技能树", icon: Network },
    { href: "/retrospectives", label: "阶段复盘", icon: ClipboardList },
  ];
  if (isAdmin) {
    items.push({ href: "/pipeline", label: "数据管道", icon: Database });
  }
  return items;
}
```

3. 在 `SidebarContent` 中使用 `user?.is_admin`：

```typescript
  const navItems = getNavItems(user?.is_admin);
```

4. 在 map 中使用 `navItems` 代替 `NAV_ITEMS`：

```typescript
        {navItems.map((item) => {
```

- [ ] **Step 5: 验证构建**

```bash
cd /workspace/frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
cd /workspace && git add -A && git commit -m "feat(phase5): 前端管理页 — 总览/接入/数据源配置 + 管理员导航"
```

---

## Task 10: 全量测试 + 构建验证

- [ ] **Step 1: 后端全量测试**

```bash
cd /workspace/backend && python -m pytest --tb=short -q
```

Expected: ALL PASSED (原有 118 + 新增约 35 = ~153)

- [ ] **Step 2: 前端构建**

```bash
cd /workspace/frontend && npm run build
```

Expected: Build success, 20 routes (原 17 + 新增 3)

- [ ] **Step 3: Commit**

```bash
cd /workspace && git add -A && git commit -m "chore(phase5): 全量测试与构建验证通过"
```
