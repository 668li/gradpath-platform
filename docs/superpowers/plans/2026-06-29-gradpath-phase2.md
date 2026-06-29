# GradPath Phase 2 实施计划 — 高校就业质量报告数据管道

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 LLM 辅助的高校就业质量报告采集管道 + 结构化搜索 API + 前端去向探索页面，使用户能搜索"清华机械"并查看去向分布、单位排名和趋势。

**Architecture:** 后端新增 School/ReportRecord/EmploymentData 三层模型 + 四步流水线管道(fetch→extract→review→publish) + 搜索 API。前端新增去向探索页面含三块可视化卡片。LLM 用于解析报告 HTML 为结构化 JSON。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Click CLI + httpx + BeautifulSoup4 + pdfplumber + 智谱GLM-4/OpenAI API + Next.js 14 + Recharts

**设计文档:** `docs/superpowers/specs/2026-06-29-gradpath-phase2-design.md`

---

## 文件结构

### 后端新增文件

```
backend/
  app/
    models/
      school.py              # School 模型
      report_record.py       # ReportRecord + ParseStatus 枚举
      employment_data.py     # EmploymentData + Degree 枚举
    schemas/
      employment.py          # 搜索/辅助 API 的 Pydantic schema
    api/
      employment.py          # 4 个搜索端点
    services/
      employment_service.py  # 搜索/聚合逻辑
  pipeline/
    __init__.py
    cli.py                   # Click CLI 入口
    fetcher.py               # HTML/PDF 抓取
    extractor.py             # LLM 解析
    reviewer.py              # 终端抽检
    prompts/
      extract_report.txt     # LLM 提示词模板
  tests/
    test_models_employment.py
    test_api_employment.py
    test_pipeline_fetcher.py
    test_pipeline_extractor.py
    test_pipeline_review.py
```

### 后端修改文件

```
backend/app/
  config.py                  # 新增 LLM_API_KEY / LLM_MODEL / LLM_BASE_URL
  models/__init__.py         # 注册新模型
  main.py                    # 注册 employment 路由
```

### 前端新增文件

```
frontend/
  app/(app)/explore/
    page.tsx                 # 搜索首页
    result/page.tsx          # 搜索结果页（三块卡片）
  components/
    employment-charts.tsx    # 饼图+条形图+折线图组件
```

### 前端修改文件

```
frontend/
  types/index.ts             # 新增 EmploymentSearchResult 等类型
  lib/api.ts                 # 新增 employmentApi
  lib/constants.ts           # 新增 EMPLOYMENT_RATE_LABEL 映射
  components/nav.tsx         # 新增「去向探索」导航项
```

---

## Task 1: 数据模型 — School / ReportRecord / EmploymentData

**Files:**
- Create: `backend/app/models/school.py`
- Create: `backend/app/models/report_record.py`
- Create: `backend/app/models/employment_data.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_models_employment.py`

- [ ] **Step 1: 编写模型测试**

```python
# backend/tests/test_models_employment.py
import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree


class TestSchool:
    def test_create_school(self, db_session):
        school = School(name="清华大学", slug="tsinghua", code="10003")
        db_session.add(school)
        db_session.commit()
        assert school.id is not None
        assert school.name == "清华大学"
        assert school.slug == "tsinghua"

    def test_school_name_unique(self, db_session):
        db_session.add(School(name="清华大学", slug="tsinghua"))
        db_session.commit()
        with pytest.raises(IntegrityError):
            db_session.add(School(name="清华大学", slug="pku"))
            db_session.commit()

    def test_school_slug_unique(self, db_session):
        db_session.add(School(name="清华大学", slug="tsinghua"))
        db_session.commit()
        with pytest.raises(IntegrityError):
            db_session.add(School(name="北京大学", slug="tsinghua"))
            db_session.commit()


class TestReportRecord:
    def test_create_report(self, db_session):
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="https://career.tsinghua.edu.cn/report2024.htm",
        )
        db_session.add(report)
        db_session.commit()
        assert report.id is not None
        assert report.parse_status == ParseStatus.pending

    def test_school_year_unique(self, db_session):
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        db_session.add(ReportRecord(school_id=school.id, year=2024, source_url="url1"))
        db_session.commit()
        with pytest.raises(IntegrityError):
            db_session.add(ReportRecord(school_id=school.id, year=2024, source_url="url2"))
            db_session.commit()


class TestEmploymentData:
    def test_create_employment_data(self, db_session):
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(school_id=school.id, year=2024, source_url="url")
        db_session.add(report)
        db_session.commit()
        data = EmploymentData(
            report_id=report.id,
            major="机械工程",
            degree=Degree.bachelor,
            total_graduates=120,
            employment_rate=0.45,
            further_study_rate=0.35,
            employer_ranking=[{"name": "三一重工", "count": 15}],
            industry_distribution={"制造业": 0.4},
        )
        db_session.add(data)
        db_session.commit()
        assert data.id is not None
        assert data.employer_ranking == [{"name": "三一重工", "count": 15}]

    def test_report_major_degree_unique(self, db_session):
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(school_id=school.id, year=2024, source_url="url")
        db_session.add(report)
        db_session.commit()
        db_session.add(EmploymentData(report_id=report.id, major="机械", degree=Degree.bachelor))
        db_session.commit()
        with pytest.raises(IntegrityError):
            db_session.add(EmploymentData(report_id=report.id, major="机械", degree=Degree.bachelor))
            db_session.commit()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /workspace/backend && python -m pytest tests/test_models_employment.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.school'`

- [ ] **Step 3: 创建 School 模型**

```python
# backend/app/models/school.py
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class School(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String(10))
    report_index_url: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(String(20))
    level: Mapped[str | None] = mapped_column(String(20))  # 985/211/双一流/普通

    reports: Mapped[list["ReportRecord"]] = relationship(back_populates="school")
```

- [ ] **Step 4: 创建 ReportRecord 模型**

```python
# backend/app/models/report_record.py
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class ParseStatus(str, enum.Enum):
    pending = "pending"
    parsed = "parsed"
    failed = "failed"
    reviewed = "reviewed"
    published = "published"


class ReportRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "report_records"
    __table_args__ = (
        UniqueConstraint("school_id", "year", name="uq_school_year"),
    )

    school_id: Mapped[UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_html: Mapped[str | None] = mapped_column(Text)
    raw_pdf_path: Mapped[str | None] = mapped_column(String(500))
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus), default=ParseStatus.pending, nullable=False
    )
    parse_error: Mapped[str | None] = mapped_column(Text)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    school: Mapped["School"] = relationship(back_populates="reports")
    employment_data: Mapped[list["EmploymentData"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
```

- [ ] **Step 5: 创建 EmploymentData 模型**

```python
# backend/app/models/employment_data.py
import enum
from uuid import UUID

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class Degree(str, enum.Enum):
    bachelor = "bachelor"
    master = "master"
    phd = "phd"
    all = "all"


class EmploymentData(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employment_data"
    __table_args__ = (
        UniqueConstraint("report_id", "major", "degree", name="uq_report_major_degree"),
    )

    report_id: Mapped[UUID] = mapped_column(ForeignKey("report_records.id"), nullable=False)
    major: Mapped[str] = mapped_column(String(200), nullable=False)
    degree: Mapped[Degree] = mapped_column(Enum(Degree), default=Degree.all, nullable=False)
    total_graduates: Mapped[int | None] = mapped_column(Integer)

    employment_rate: Mapped[float | None] = mapped_column(Float)
    further_study_rate: Mapped[float | None] = mapped_column(Float)
    civil_service_rate: Mapped[float | None] = mapped_column(Float)
    abroad_rate: Mapped[float | None] = mapped_column(Float)
    startup_rate: Mapped[float | None] = mapped_column(Float)
    gap_year_rate: Mapped[float | None] = mapped_column(Float)

    employer_ranking: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    industry_distribution: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    destination_region: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    school_for_further_study: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    report: Mapped["ReportRecord"] = relationship(back_populates="employment_data")
```

- [ ] **Step 6: 注册模型到 `__init__.py`**

```python
# backend/app/models/__init__.py
from app.models.career_event import CareerEvent, EventType
from app.models.destination_decision import DecisionStatus, DestinationDecision, DestinationType
from app.models.employment_data import Degree, EmploymentData
from app.models.reference_snapshot import ReferenceSnapshot, SnapshotSource
from app.models.report_record import ParseStatus, ReportRecord
from app.models.retrospective import PeriodType, Retrospective
from app.models.school import School
from app.models.skill_node import SkillNode
from app.models.user import User, UserStage

__all__ = [
    "User", "UserStage",
    "DestinationDecision", "DestinationType", "DecisionStatus",
    "CareerEvent", "EventType",
    "SkillNode",
    "Retrospective", "PeriodType",
    "ReferenceSnapshot", "SnapshotSource",
    "School",
    "ReportRecord", "ParseStatus",
    "EmploymentData", "Degree",
]
```

- [ ] **Step 7: 运行测试确认通过**

Run: `cd /workspace/backend && python -m pytest tests/test_models_employment.py -v`
Expected: 7 passed

- [ ] **Step 8: 运行全量测试确认无回归**

Run: `cd /workspace/backend && python -m pytest -v`
Expected: 全部通过（Phase 1 的 31 个 + 新增 7 个 = 38 个）

- [ ] **Step 9: 提交**

```bash
cd /workspace
git add backend/app/models/school.py backend/app/models/report_record.py backend/app/models/employment_data.py backend/app/models/__init__.py backend/tests/test_models_employment.py
git commit -m "feat(models): 新增 School/ReportRecord/EmploymentData 就业数据模型"
```

---

## Task 2: 配置扩展 — LLM API 配置

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: 添加 LLM 配置字段**

```python
# backend/app/config.py — 完整文件
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./gradpath.db"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # LLM 配置（Phase 2 管道用）
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "glm-4"
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 2: 运行全量测试确认无回归**

Run: `cd /workspace/backend && python -m pytest -v`
Expected: 全部通过

- [ ] **Step 3: 提交**

```bash
cd /workspace
git add backend/app/config.py
git commit -m "feat(config): 新增 LLM API 配置字段"
```

---

## Task 3: 管道 fetcher — HTML/PDF 抓取

**Files:**
- Create: `backend/pipeline/__init__.py`
- Create: `backend/pipeline/fetcher.py`
- Test: `backend/tests/test_pipeline_fetcher.py`

- [ ] **Step 1: 编写 fetcher 测试**

```python
# backend/tests/test_pipeline_fetcher.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from pipeline.fetcher import fetch_report


SAMPLE_HTML = """
<html><body>
<h1>清华大学2024届毕业生就业质量年度报告</h1>
<table>
<tr><th>专业</th><th>毕业人数</th><th>就业率</th></tr>
<tr><td>机械工程</td><td>120</td><td>45%</td></tr>
</table>
</body></html>
"""


class TestFetcher:
    def test_fetch_html_report(self, db_session):
        """测试成功抓取 HTML 报告"""
        school = School(name="清华大学", slug="tsinghua", report_index_url="https://career.tsinghua.edu.cn/")
        db_session.add(school)
        db_session.commit()

        with patch("pipeline.fetcher.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_HTML
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value = mock_response

            report = fetch_report(db_session, school_slug="tsinghua", year=2024)

        assert report is not None
        assert report.school_id == school.id
        assert report.year == 2024
        assert report.parse_status == ParseStatus.pending
        assert "清华大学2024届" in report.raw_html

    def test_fetch_report_not_found(self, db_session):
        """测试报告链接未找到"""
        school = School(name="清华大学", slug="tsinghua", report_index_url="https://career.tsinghua.edu.cn/")
        db_session.add(school)
        db_session.commit()

        with patch("pipeline.fetcher.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            report = fetch_report(db_session, school_slug="tsinghua", year=2024)

        assert report is not None
        assert report.parse_status == ParseStatus.failed
        assert "404" in (report.parse_error or "")

    def test_fetch_school_not_found(self, db_session):
        """测试学校不存在"""
        report = fetch_report(db_session, school_slug="nonexistent", year=2024)
        assert report is None

    def test_fetch_direct_url(self, db_session):
        """测试直接提供报告 URL"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()

        with patch("pipeline.fetcher.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_HTML
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value = mock_response

            report = fetch_report(
                db_session,
                school_slug="tsinghua",
                year=2024,
                direct_url="https://example.com/report.htm",
            )

        assert report is not None
        assert report.source_url == "https://example.com/report.htm"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /workspace/backend && python -m pytest tests/test_pipeline_fetcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: 创建 pipeline 包**

```python
# backend/pipeline/__init__.py
```

- [ ] **Step 4: 实现 fetcher**

```python
# backend/pipeline/fetcher.py
"""高校就业质量报告抓取器"""
import time
import re
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy.orm import Session

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus

USER_AGENT = "GradPathBot/1.0 (career research; +https://github.com/gradpath)"
REQUEST_DELAY = 3  # 秒，请求间隔
TIMEOUT = 30
MAX_RETRIES = 3


def check_robots_allowed(url: str) -> bool:
    """检查 robots.txt 是否允许抓取"""
    try:
        rp = RobotFileParser()
        rp.set_url(url + "/robots.txt" if not url.endswith("/") else url + "robots.txt")
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True  # 无法读取 robots.txt 时默认允许


def fetch_report(
    db: Session,
    school_slug: str,
    year: int,
    direct_url: str | None = None,
) -> ReportRecord | None:
    """抓取指定学校的指定年份就业质量报告。

    Args:
        db: 数据库会话
        school_slug: 学校 slug（如 tsinghua）
        year: 报告年份
        direct_url: 直接提供报告 URL（跳过入口页搜索）

    Returns:
        ReportRecord 或 None（学校不存在时）
    """
    school = db.query(School).filter(School.slug == school_slug).first()
    if not school:
        return None

    # 确定报告 URL
    if direct_url:
        report_url = direct_url
    elif school.report_index_url:
        report_url = _find_report_url(school.report_index_url, year)
        if not report_url:
            report = ReportRecord(
                school_id=school.id,
                year=year,
                source_url=school.report_index_url,
                parse_status=ParseStatus.failed,
                parse_error=f"未找到 {year} 年报告链接",
            )
            db.add(report)
            db.commit()
            return report
    else:
        report = ReportRecord(
            school_id=school.id,
            year=year,
            source_url="",
            parse_status=ParseStatus.failed,
            parse_error="学校未配置 report_index_url",
        )
        db.add(report)
        db.commit()
        return report

    # 抓取报告内容
    html_content = _fetch_url(report_url)
    if html_content is None:
        report = ReportRecord(
            school_id=school.id,
            year=year,
            source_url=report_url,
            parse_status=ParseStatus.failed,
            parse_error=f"抓取失败: HTTP 错误或网络超时",
        )
        db.add(report)
        db.commit()
        return report

    report = ReportRecord(
        school_id=school.id,
        year=year,
        source_url=report_url,
        raw_html=html_content,
        parse_status=ParseStatus.pending,
    )
    db.add(report)
    db.commit()
    return report


def _find_report_url(index_url: str, year: int) -> str | None:
    """从入口页搜索指定年份的报告链接"""
    html = _fetch_url(index_url)
    if not html:
        return None
    # 搜索包含年份关键词的链接
    pattern = rf'href=["\']([^"\']*{year}[^"\']*(?:就业|employment|report)[^"\']*)["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)
    if matches:
        from urllib.parse import urljoin
        return urljoin(index_url, matches[0])
    return None


def _fetch_url(url: str) -> str | None:
    """带重试的 HTTP GET"""
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY)
            resp = httpx.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 404:
                return None
        except httpx.RequestError:
            if attempt < MAX_RETRIES - 1:
                time.sleep(REQUEST_DELAY * (attempt + 2))
                continue
            return None
    return None
```

- [ ] **Step 5: 安装新依赖**

Run: `pip install httpx beautifulsoup4 pdfplumber click --break-system-packages`

- [ ] **Step 6: 运行测试确认通过**

Run: `cd /workspace/backend && python -m pytest tests/test_pipeline_fetcher.py -v`
Expected: 4 passed

- [ ] **Step 7: 提交**

```bash
cd /workspace
git add backend/pipeline/__init__.py backend/pipeline/fetcher.py backend/tests/test_pipeline_fetcher.py
git commit -m "feat(pipeline): 实现 fetcher 报告抓取模块"
```

---

## Task 4: 管道 extractor — LLM 解析

**Files:**
- Create: `backend/pipeline/prompts/extract_report.txt`
- Create: `backend/pipeline/extractor.py`
- Test: `backend/tests/test_pipeline_extractor.py`

- [ ] **Step 1: 编写 extractor 测试**

```python
# backend/tests/test_pipeline_extractor.py
import pytest
import json
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree
from pipeline.extractor import extract_report


SAMPLE_REPORT_HTML = """
<html><body>
<h1>清华大学2024届毕业生就业质量年度报告</h1>
<h2>机械工程</h2>
<p>毕业人数：120人，就业率45%，升学率35%</p>
<table><tr><td>三一重工</td><td>15</td></tr></table>
</body></html>
"""

MOCK_LLM_RESPONSE = json.dumps({
    "majors": [
        {
            "major": "机械工程",
            "degree": "bachelor",
            "total_graduates": 120,
            "employment_rate": 0.45,
            "further_study_rate": 0.35,
            "civil_service_rate": 0.10,
            "abroad_rate": 0.10,
            "startup_rate": 0.0,
            "gap_year_rate": 0.0,
            "employer_ranking": [{"name": "三一重工", "count": 15}],
            "industry_distribution": {"制造业": 0.4, "互联网": 0.2},
            "destination_region": {"北京": 0.3, "上海": 0.15},
            "school_for_further_study": [{"name": "清华大学", "count": 20}]
        }
    ]
})


class TestExtractor:
    def test_extract_success(self, db_session):
        """测试 LLM 解析成功"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=SAMPLE_REPORT_HTML,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        with patch("pipeline.extractor.call_llm", return_value=MOCK_LLM_RESPONSE):
            extract_report(db_session, report_id=report.id)

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.parsed
        assert report.parsed_at is not None

        data = db_session.query(EmploymentData).filter(EmploymentData.report_id == report.id).all()
        assert len(data) == 1
        assert data[0].major == "机械工程"
        assert data[0].employment_rate == 0.45
        assert data[0].employer_ranking == [{"name": "三一重工", "count": 15}]

    def test_extract_llm_failure(self, db_session):
        """测试 LLM 返回无效 JSON"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=SAMPLE_REPORT_HTML,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        with patch("pipeline.extractor.call_llm", return_value="not valid json"):
            extract_report(db_session, report_id=report.id)

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.failed
        assert report.parse_error is not None

    def test_extract_no_html(self, db_session):
        """测试无 raw_html"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=None,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        result = extract_report(db_session, report_id=report.id)
        assert result is None

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.failed
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /workspace/backend && python -m pytest tests/test_pipeline_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.extractor'`

- [ ] **Step 3: 创建 LLM 提示词模板**

```text
# backend/pipeline/prompts/extract_report.txt
你是一个就业质量报告解析助手。请从以下高校就业质量年度报告文本中提取结构化数据。

要求：
1. 按专业拆分，每个专业一条记录
2. 所有比例值用 0-1 之间的小数表示（如 45% = 0.45）
3. 如果某个字段在报告中未提及，设为 null（数字字段）或空数组/空对象
4. employer_ranking 按人数降序排列
5. 严格返回 JSON，不要添加任何解释文字

返回格式：
{
  "majors": [
    {
      "major": "专业名称",
      "degree": "bachelor|master|phd|all",
      "total_graduates": 120,
      "employment_rate": 0.45,
      "further_study_rate": 0.35,
      "civil_service_rate": 0.10,
      "abroad_rate": 0.10,
      "startup_rate": 0.0,
      "gap_year_rate": 0.0,
      "employer_ranking": [{"name": "单位名", "count": 人数}],
      "industry_distribution": {"行业名": 比例},
      "destination_region": {"省份/城市": 比例},
      "school_for_further_study": [{"name": "学校名", "count": 人数}]
    }
  ]
}

报告文本：
{report_text}
```

- [ ] **Step 4: 实现 extractor**

```python
# backend/pipeline/extractor.py
"""LLM 辅助就业报告解析器"""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.config import settings
from app.models.employment_data import Degree, EmploymentData
from app.models.report_record import ParseStatus, ReportRecord

PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_report.txt"
MAX_TEXT_LENGTH = 12000  # LLM 输入文本上限


def extract_report(db: Session, report_id: UUID) -> ReportRecord | None:
    """解析报告，通过 LLM 提取结构化就业数据。

    Args:
        db: 数据库会话
        report_id: ReportRecord 的 ID

    Returns:
        更新后的 ReportRecord，或 None（报告不存在时）
    """
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        return None

    if not report.raw_html:
        report.parse_status = ParseStatus.failed
        report.parse_error = "无 raw_html 内容"
        db.commit()
        return report

    # 清洗 HTML 为纯文本
    text = _clean_html(report.raw_html)
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    # 调用 LLM
    try:
        llm_response = call_llm(text)
        data = json.loads(llm_response)
    except json.JSONDecodeError as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"LLM 返回无效 JSON: {e}"
        db.commit()
        return report
    except Exception as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"LLM 调用失败: {e}"
        db.commit()
        return report

    # 写入 EmploymentData
    majors = data.get("majors", [])
    for major_data in majors:
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

    report.parse_status = ParseStatus.parsed
    report.parsed_at = datetime.now(timezone.utc)
    report.parse_error = None
    db.commit()
    return report


def _clean_html(html: str) -> str:
    """将 HTML 清洗为纯文本 + 表格结构"""
    soup = BeautifulSoup(html, "html.parser")
    # 移除 script/style
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    # 保留表格结构
    text = soup.get_text(separator="\n", strip=True)
    # 压缩空行
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def call_llm(report_text: str) -> str:
    """调用 LLM API 解析报告文本，返回 JSON 字符串。

    使用 OpenAI 兼容接口（智谱 GLM-4 / OpenAI GPT-4o 均支持）。
    """
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = prompt_template.replace("{report_text}", report_text)

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "timeout": 60,
    }

    resp = httpx.post(
        f"{settings.LLM_BASE_URL}chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /workspace/backend && python -m pytest tests/test_pipeline_extractor.py -v`
Expected: 3 passed

- [ ] **Step 6: 提交**

```bash
cd /workspace
git add backend/pipeline/extractor.py backend/pipeline/prompts/extract_report.txt backend/tests/test_pipeline_extractor.py
git commit -m "feat(pipeline): 实现 LLM extractor 报告解析模块"
```

---

## Task 5: 管道 review/publish — CLI 命令

**Files:**
- Create: `backend/pipeline/reviewer.py`
- Create: `backend/pipeline/cli.py`
- Test: `backend/tests/test_pipeline_review.py`

- [ ] **Step 1: 编写 review/publish 测试**

```python
# backend/tests/test_pipeline_review.py
import pytest
from unittest.mock import patch
from io import StringIO

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree
from pipeline.reviewer import review_report, publish_report


class TestReviewer:
    def test_review_accept(self, db_session):
        """测试审核通过"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.parsed,
        )
        db_session.add(report)
        db_session.commit()
        db_session.add(EmploymentData(
            report_id=report.id, major="机械工程", degree=Degree.bachelor,
            employment_rate=0.45, employer_ranking=[{"name": "三一重工", "count": 15}],
        ))
        db_session.commit()

        with patch("builtins.input", return_value="y"):
            review_report(db_session, report_id=report.id)

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.reviewed

    def test_review_reject(self, db_session):
        """测试审核拒绝"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.parsed,
        )
        db_session.add(report)
        db_session.commit()

        with patch("builtins.input", return_value="n"):
            review_report(db_session, report_id=report.id)

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.pending

    def test_review_wrong_status(self, db_session):
        """测试非 parsed 状态不能审核"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        result = review_report(db_session, report_id=report.id)
        assert result is None

    def test_publish(self, db_session):
        """测试发布"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.reviewed,
        )
        db_session.add(report)
        db_session.commit()

        publish_report(db_session, report_id=report.id)
        db_session.refresh(report)
        assert report.parse_status == ParseStatus.published

    def test_publish_wrong_status(self, db_session):
        """测试非 reviewed 状态不能发布"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.parsed,
        )
        db_session.add(report)
        db_session.commit()

        result = publish_report(db_session, report_id=report.id)
        assert result is None
        db_session.refresh(report)
        assert report.parse_status == ParseStatus.parsed
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /workspace/backend && python -m pytest tests/test_pipeline_review.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.reviewer'`

- [ ] **Step 3: 实现 reviewer**

```python
# backend/pipeline/reviewer.py
"""报告审核与发布模块"""
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.employment_data import EmploymentData
from app.models.report_record import ParseStatus, ReportRecord


def review_report(db: Session, report_id: UUID) -> ReportRecord | None:
    """终端输出解析结果摘要，人工确认。

    仅 parse_status == parsed 的报告可审核。
    """
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report or report.parse_status != ParseStatus.parsed:
        print(f"无法审核：报告不存在或状态不是 parsed（当前: {report.parse_status if report else '不存在'}）")
        return None

    # 输出摘要
    data_list = db.query(EmploymentData).filter(EmploymentData.report_id == report_id).all()
    print(f"\n{'='*60}")
    print(f"报告审核：{report.year}年（{report.source_url}）")
    print(f"{'='*60}")
    for i, data in enumerate(data_list, 1):
        print(f"\n[{i}] 专业: {data.major} ({data.degree.value})")
        print(f"    毕业人数: {data.total_graduates}")
        print(f"    就业率: {data.employment_rate}, 升学率: {data.further_study_rate}")
        print(f"    考公率: {data.civil_service_rate}, 出国率: {data.abroad_rate}")
        if data.employer_ranking:
            print(f"    Top5 雇主:")
            for emp in data.employer_ranking[:5]:
                print(f"      - {emp['name']}: {emp['count']}人")
        if data.school_for_further_study:
            print(f"    Top5 升学去向:")
            for sch in data.school_for_further_study[:5]:
                print(f"      - {sch['name']}: {sch['count']}人")
    print(f"\n{'='*60}")

    choice = input("确认解析结果正确？(y/n): ").strip().lower()
    if choice == "y":
        report.parse_status = ParseStatus.reviewed
        db.commit()
        print("已标记为 reviewed")
    else:
        report.parse_status = ParseStatus.pending
        db.commit()
        print("已回退为 pending，可调整后重新 extract")
    return report


def publish_report(db: Session, report_id: UUID) -> ReportRecord | None:
    """发布报告，仅 reviewed 状态可发布。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report or report.parse_status != ParseStatus.reviewed:
        print(f"无法发布：报告不存在或状态不是 reviewed")
        return None

    report.parse_status = ParseStatus.published
    db.commit()
    print(f"报告已发布，数据对前端搜索可见")
    return report
```

- [ ] **Step 4: 实现 CLI 入口**

```python
# backend/pipeline/cli.py
"""管道 CLI 入口"""
import click
from uuid import UUID

from app.database import SessionLocal
from pipeline.extractor import extract_report
from pipeline.fetcher import fetch_report
from pipeline.reviewer import publish_report, review_report


@click.group()
def cli():
    """GradPath 就业报告数据管道"""
    pass


@cli.command()
@click.option("--school", required=True, help="学校 slug（如 tsinghua）")
@click.option("--year", required=True, type=int, help="报告年份")
@click.option("--url", default=None, help="直接提供报告 URL（可选）")
def fetch(school: str, year: int, url: str | None):
    """抓取高校就业质量报告"""
    db = SessionLocal()
    try:
        report = fetch_report(db, school_slug=school, year=year, direct_url=url)
        if report is None:
            click.echo(f"学校 '{school}' 不存在")
        else:
            click.echo(f"报告已创建: id={report.id}, status={report.parse_status}")
    finally:
        db.close()


@cli.command()
@click.option("--report-id", required=True, help="ReportRecord UUID")
def extract(report_id: str):
    """LLM 解析报告"""
    db = SessionLocal()
    try:
        report = extract_report(db, report_id=UUID(report_id))
        if report is None:
            click.echo("报告不存在")
        else:
            click.echo(f"解析完成: status={report.parse_status}")
            if report.parse_error:
                click.echo(f"错误: {report.parse_error}")
    finally:
        db.close()


@cli.command()
@click.option("--report-id", required=True, help="ReportRecord UUID")
def review(report_id: str):
    """人工审核解析结果"""
    db = SessionLocal()
    try:
        review_report(db, report_id=UUID(report_id))
    finally:
        db.close()


@cli.command()
@click.option("--report-id", required=True, help="ReportRecord UUID")
def publish(report_id: str):
    """发布报告"""
    db = SessionLocal()
    try:
        publish_report(db, report_id=UUID(report_id))
    finally:
        db.close()


if __name__ == "__main__":
    cli()
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /workspace/backend && python -m pytest tests/test_pipeline_review.py -v`
Expected: 5 passed

- [ ] **Step 6: 提交**

```bash
cd /workspace
git add backend/pipeline/reviewer.py backend/pipeline/cli.py backend/tests/test_pipeline_review.py
git commit -m "feat(pipeline): 实现 review/publish CLI 命令"
```

---

## Task 6: 搜索 API — Service + Schema + Router

**Files:**
- Create: `backend/app/schemas/employment.py`
- Create: `backend/app/services/employment_service.py`
- Create: `backend/app/api/employment.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api_employment.py`

- [ ] **Step 1: 编写 API 测试**

```python
# backend/tests/test_api_employment.py
import pytest
from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree


def _seed_employment_data(db_session):
    """创建测试种子数据"""
    school = School(name="清华大学", slug="tsinghua", code="10003")
    db_session.add(school)
    db_session.commit()

    for year in [2023, 2024]:
        report = ReportRecord(
            school_id=school.id, year=year, source_url=f"url-{year}",
            parse_status=ParseStatus.published,
        )
        db_session.add(report)
        db_session.commit()
        db_session.add(EmploymentData(
            report_id=report.id, major="机械工程", degree=Degree.bachelor,
            total_graduates=120, employment_rate=0.45 + (2024 - year) * 0.05,
            further_study_rate=0.35, civil_service_rate=0.10, abroad_rate=0.10,
            employer_ranking=[{"name": "三一重工", "count": 15}, {"name": "比亚迪", "count": 12}],
            industry_distribution={"制造业": 0.4, "互联网": 0.2},
            destination_region={"北京": 0.3, "上海": 0.15},
            school_for_further_study=[{"name": "清华大学", "count": 20}],
        ))
        db_session.commit()

    # 未发布的报告不应出现在搜索结果
    unpublished = ReportRecord(
        school_id=school.id, year=2022, source_url="url-2022",
        parse_status=ParseStatus.parsed,
    )
    db_session.add(unpublished)
    db_session.commit()
    db_session.add(EmploymentData(
        report_id=unpublished.id, major="机械工程", degree=Degree.bachelor,
        total_graduates=100, employment_rate=0.50,
    ))
    db_session.commit()


class TestEmploymentSearch:
    def test_search_by_school_and_major(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械")
        assert resp.status_code == 200
        data = resp.json()
        assert data["school"]["name"] == "清华大学"
        assert "机械" in data["major"]
        assert len(data["records"]) == 2  # 2023 + 2024
        assert data["records"][0]["year"] == 2024  # 降序

    def test_search_with_year_filter(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械&year=2024")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["records"]) == 1
        assert data["records"][0]["year"] == 2024

    def test_search_trend(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械")
        data = resp.json()
        assert "trend" in data
        assert data["trend"]["years"] == [2023, 2024]  # 升序
        assert len(data["trend"]["employment_rate"]) == 2

    def test_search_excludes_unpublished(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械")
        data = resp.json()
        years = [r["year"] for r in data["records"]]
        assert 2022 not in years  # 未发布的不出现

    def test_search_no_result(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=不存在&major=机械")
        assert resp.status_code == 200
        data = resp.json()
        assert data["records"] == []
        assert data["school"] is None


class TestEmploymentSchools:
    def test_list_schools(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/schools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "清华大学"
        assert data[0]["report_count"] == 2  # 只有 published 的


class TestEmploymentStats:
    def test_stats(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["school_count"] == 1
        assert data["report_count"] == 2  # 只算 published
        assert data["major_count"] >= 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /workspace/backend && python -m pytest tests/test_api_employment.py -v`
Expected: FAIL — 404 或路由不存在

- [ ] **Step 3: 创建 schema**

```python
# backend/app/schemas/employment.py
from pydantic import BaseModel


class SchoolResponse(BaseModel):
    id: str
    name: str
    slug: str
    code: str | None = None
    report_count: int = 0
    major_count: int = 0


class EmploymentRecordResponse(BaseModel):
    year: int
    degree: str
    total_graduates: int | None
    rates: dict
    employer_ranking: list
    industry_distribution: dict
    destination_region: dict
    school_for_further_study: list


class TrendResponse(BaseModel):
    years: list[int]
    employment_rate: list[float | None]
    further_study_rate: list[float | None]
    civil_service_rate: list[float | None]
    abroad_rate: list[float | None]


class EmploymentSearchResponse(BaseModel):
    school: SchoolResponse | None
    major: str | None
    records: list[EmploymentRecordResponse]
    trend: TrendResponse | None


class EmploymentStatsResponse(BaseModel):
    school_count: int
    report_count: int
    major_count: int
    year_range: tuple[int | None, int | None]
```

- [ ] **Step 4: 创建 service**

```python
# backend/app/services/employment_service.py
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.models.employment_data import EmploymentData
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School


def search_employment(
    db: Session,
    school: str,
    major: str,
    year: int | None = None,
    degree: str | None = None,
) -> dict:
    """搜索就业数据"""
    # 模糊匹配学校
    school_obj = db.query(School).filter(School.name.ilike(f"%{school}%")).first()

    if not school_obj:
        return {"school": None, "major": None, "records": [], "trend": None}

    # 查询已发布的报告
    query = (
        db.query(EmploymentData)
        .join(ReportRecord)
        .filter(
            ReportRecord.school_id == school_obj.id,
            ReportRecord.parse_status == ParseStatus.published,
            EmploymentData.major.ilike(f"%{major}%"),
        )
    )
    if year:
        query = query.filter(ReportRecord.year == year)
    if degree:
        query = query.filter(EmploymentData.degree == degree)

    query = query.order_by(ReportRecord.year.desc())
    results = query.all()

    # 构建记录
    records = []
    for emp in results:
        report = emp.report
        records.append({
            "year": report.year,
            "degree": emp.degree.value,
            "total_graduates": emp.total_graduates,
            "rates": {
                "employment": emp.employment_rate,
                "further_study": emp.further_study_rate,
                "civil_service": emp.civil_service_rate,
                "abroad": emp.abroad_rate,
                "startup": emp.startup_rate,
                "gap_year": emp.gap_year_rate,
            },
            "employer_ranking": emp.employer_ranking,
            "industry_distribution": emp.industry_distribution,
            "destination_region": emp.destination_region,
            "school_for_further_study": emp.school_for_further_study,
        })

    # 构建趋势
    trend = _build_trend(results)

    return {
        "school": {"id": str(school_obj.id), "name": school_obj.name, "slug": school_obj.slug, "code": school_obj.code},
        "major": results[0].major if results else None,
        "records": records,
        "trend": trend,
    }


def _build_trend(results: list[EmploymentData]) -> dict | None:
    if len(results) < 1:
        return None
    # 按年份升序
    sorted_results = sorted(results, key=lambda x: x.report.year)
    years = [r.report.year for r in sorted_results]
    return {
        "years": years,
        "employment_rate": [r.employment_rate for r in sorted_results],
        "further_study_rate": [r.further_study_rate for r in sorted_results],
        "civil_service_rate": [r.civil_service_rate for r in sorted_results],
        "abroad_rate": [r.abroad_rate for r in sorted_results],
    }


def list_schools(db: Session) -> list[dict]:
    """列出已收录学校（含已发布报告数）"""
    schools = db.query(School).all()
    result = []
    for s in schools:
        report_count = (
            db.query(func.count(ReportRecord.id))
            .filter(ReportRecord.school_id == s.id, ReportRecord.parse_status == ParseStatus.published)
            .scalar() or 0
        )
        major_count = (
            db.query(distinct(EmploymentData.major))
            .join(ReportRecord)
            .filter(ReportRecord.school_id == s.id, ReportRecord.parse_status == ParseStatus.published)
            .count()
        )
        if report_count > 0:
            result.append({
                "id": str(s.id), "name": s.name, "slug": s.slug, "code": s.code,
                "report_count": report_count, "major_count": major_count,
            })
    return result


def list_majors(db: Session, school: str) -> list[str]:
    """列出某校已收录专业"""
    school_obj = db.query(School).filter(School.name.ilike(f"%{school}%")).first()
    if not school_obj:
        return []
    majors = (
        db.query(distinct(EmploymentData.major))
        .join(ReportRecord)
        .filter(ReportRecord.school_id == school_obj.id, ReportRecord.parse_status == ParseStatus.published)
        .all()
    )
    return [m[0] for m in majors]


def get_stats(db: Session) -> dict:
    """全局统计"""
    published_reports = (
        db.query(ReportRecord)
        .filter(ReportRecord.parse_status == ParseStatus.published)
        .all()
    )
    school_ids = set(r.school_id for r in published_reports)
    major_count = (
        db.query(distinct(EmploymentData.major))
        .join(ReportRecord)
        .filter(ReportRecord.parse_status == ParseStatus.published)
        .count()
    )
    years = [r.year for r in published_reports]
    return {
        "school_count": len(school_ids),
        "report_count": len(published_reports),
        "major_count": major_count,
        "year_range": [min(years) if years else None, max(years) if years else None],
    }
```

- [ ] **Step 5: 创建 API 路由**

```python
# backend/app/api/employment.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.employment_service import get_stats, list_majors, list_schools, search_employment

router = APIRouter(prefix="/api/employment", tags=["就业数据"])


@router.get("/search")
def search(
    school: str = Query(..., description="学校名称（模糊匹配）"),
    major: str = Query(..., description="专业名称（模糊匹配）"),
    year: int | None = Query(None, description="年份筛选"),
    degree: str | None = Query(None, description="学历筛选"),
    db: Session = Depends(get_db),
):
    return search_employment(db, school, major, year, degree)


@router.get("/schools")
def schools(db: Session = Depends(get_db)):
    return list_schools(db)


@router.get("/majors")
def majors(school: str = Query(...), db: Session = Depends(get_db)):
    return list_majors(db, school)


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    return get_stats(db)
```

- [ ] **Step 6: 注册路由到 main.py**

在 `backend/app/main.py` 的 `app.include_router` 区域添加：

```python
from app.api.employment import router as employment_router
# ... 其他 import ...
app.include_router(employment_router)
```

- [ ] **Step 7: 运行测试确认通过**

Run: `cd /workspace/backend && python -m pytest tests/test_api_employment.py -v`
Expected: 7 passed

- [ ] **Step 8: 提交**

```bash
cd /workspace
git add backend/app/schemas/employment.py backend/app/services/employment_service.py backend/app/api/employment.py backend/app/main.py backend/tests/test_api_employment.py
git commit -m "feat(api): 实现就业数据搜索 API（search/schools/majors/stats）"
```

---

## Task 7: 前端类型与 API 客户端

**Files:**
- Modify: `frontend/types/index.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/constants.ts`

- [ ] **Step 1: 在 types/index.ts 末尾新增就业数据类型**

```typescript
// ===== 就业数据搜索 =====
export interface SchoolInfo {
  id: string;
  name: string;
  slug: string;
  code: string | null;
  report_count: number;
  major_count: number;
}

export interface EmploymentRecord {
  year: number;
  degree: string;
  total_graduates: number | null;
  rates: {
    employment: number | null;
    further_study: number | null;
    civil_service: number | null;
    abroad: number | null;
    startup: number | null;
    gap_year: number | null;
  };
  employer_ranking: { name: string; count: number }[];
  industry_distribution: Record<string, number>;
  destination_region: Record<string, number>;
  school_for_further_study: { name: string; count: number }[];
}

export interface EmploymentTrend {
  years: number[];
  employment_rate: (number | null)[];
  further_study_rate: (number | null)[];
  civil_service_rate: (number | null)[];
  abroad_rate: (number | null)[];
}

export interface EmploymentSearchResult {
  school: SchoolInfo | null;
  major: string | null;
  records: EmploymentRecord[];
  trend: EmploymentTrend | null;
}

export interface EmploymentStats {
  school_count: number;
  report_count: number;
  major_count: number;
  year_range: [number | null, number | null];
}
```

- [ ] **Step 2: 在 constants.ts 末尾新增去向标签映射**

```typescript
// ===== 就业去向分布标签 =====
export const RATE_LABEL: Record<string, string> = {
  employment: "就业",
  further_study: "升学",
  civil_service: "考公",
  abroad: "出国",
  startup: "创业",
  gap_year: "间隔年",
};

export const RATE_COLORS: Record<string, string> = {
  employment: "#3377f6",
  further_study: "#16a34a",
  civil_service: "#d97706",
  abroad: "#7c3aed",
  startup: "#dc2626",
  gap_year: "#64748b",
};
```

- [ ] **Step 3: 在 api.ts 中新增 employmentApi**

在 `api.ts` 文件末尾、`export const xxxApi` 区域之后添加：

```typescript
export const employmentApi = {
  async search(params: {
    school: string;
    major: string;
    year?: number;
    degree?: string;
  }): Promise<EmploymentSearchResult> {
    const qs = new URLSearchParams({ school: params.school, major: params.major });
    if (params.year) qs.set("year", String(params.year));
    if (params.degree) qs.set("degree", params.degree);
    const resp = await fetch(`/api/employment/search?${qs}`);
    if (!resp.ok) throw new Error("搜索失败");
    return resp.json();
  },

  async schools(): Promise<SchoolInfo[]> {
    const resp = await fetch(`/api/employment/schools`);
    if (!resp.ok) throw new Error("获取学校列表失败");
    return resp.json();
  },

  async majors(school: string): Promise<string[]> {
    const resp = await fetch(`/api/employment/majors?school=${encodeURIComponent(school)}`);
    if (!resp.ok) throw new Error("获取专业列表失败");
    return resp.json();
  },

  async stats(): Promise<EmploymentStats> {
    const resp = await fetch(`/api/employment/stats`);
    if (!resp.ok) throw new Error("获取统计失败");
    return resp.json();
  },
};
```

同时更新 `api.ts` 顶部的 import，添加新类型：

```typescript
import type {
  // ... 现有类型 ...
  EmploymentSearchResult,
  EmploymentStats,
  SchoolInfo,
} from "@/types";
```

- [ ] **Step 4: 验证前端构建**

Run: `cd /workspace/frontend && npx next build 2>&1 | tail -5`
Expected: 构建成功（可能有 warning 但无 error）

- [ ] **Step 5: 提交**

```bash
cd /workspace
git add frontend/types/index.ts frontend/lib/api.ts frontend/lib/constants.ts
git commit -m "feat(frontend): 新增就业数据类型定义和 API 客户端"
```

---

## Task 8: 前端去向探索页面

**Files:**
- Create: `frontend/app/(app)/explore/page.tsx`
- Create: `frontend/app/(app)/explore/result/page.tsx`
- Create: `frontend/components/employment-charts.tsx`

- [ ] **Step 1: 创建图表组件**

```tsx
// frontend/components/employment-charts.tsx
"use client";

import { useState } from "react";
import {
  PieChart, Pie, Cell, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip,
  LineChart, Line, CartesianGrid, Legend,
} from "recharts";
import { RATE_LABEL, RATE_COLORS } from "@/lib/constants";
import type { EmploymentRecord, EmploymentTrend } from "@/types";

export function DestinationPie({ record }: { record: EmploymentRecord }) {
  const data = Object.entries(record.rates)
    .filter(([, v]) => v !== null && v > 0)
    .map(([key, value]) => ({
      name: RATE_LABEL[key] ?? key,
      value: value!,
      key,
    }));

  if (data.length === 0) return <p className="text-sm text-slate-400">暂无去向分布数据</p>;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={100}
          label={({ name, value }) => `${name} ${(value * 100).toFixed(0)}%`}
        >
          {data.map((d) => (
            <Cell key={d.key} fill={RATE_COLORS[d.key] ?? "#999"} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function RankingBar({
  data,
  title,
}: {
  data: { name: string; count: number }[];
  title: string;
}) {
  if (!data || data.length === 0)
    return <p className="text-sm text-slate-400">暂无{title}数据</p>;

  const top10 = data.slice(0, 10).reverse();

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, top10.length * 32)}>
      <BarChart data={top10} layout="vertical">
        <XAxis type="number" />
        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} />
        <Tooltip />
        <Bar dataKey="count" fill="#3377f6" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TrendLine({ trend }: { trend: EmploymentTrend }) {
  if (!trend || trend.years.length < 1)
    return <p className="text-sm text-slate-400">暂无趋势数据</p>;

  const data = trend.years.map((year, i) => ({
    year: String(year),
    就业率: trend.employment_rate[i],
    升学率: trend.further_study_rate[i],
    考公率: trend.civil_service_rate[i],
    出国率: trend.abroad_rate[i],
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="year" />
        <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
        <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
        <Legend />
        <Line type="monotone" dataKey="就业率" stroke="#3377f6" />
        <Line type="monotone" dataKey="升学率" stroke="#16a34a" />
        <Line type="monotone" dataKey="考公率" stroke="#d97706" />
        <Line type="monotone" dataKey="出国率" stroke="#7c3aed" />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: 创建搜索首页**

```tsx
// frontend/app/(app)/explore/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Search, School as SchoolIcon } from "lucide-react";
import { employmentApi } from "@/lib/api";
import { Button } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import type { SchoolInfo, EmploymentStats } from "@/types";

export default function ExplorePage() {
  const [schools, setSchools] = useState<SchoolInfo[]>([]);
  const [stats, setStats] = useState<EmploymentStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [schoolQuery, setSchoolQuery] = useState("");
  const [majorQuery, setMajorQuery] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [s, st] = await Promise.all([
          employmentApi.schools(),
          employmentApi.stats(),
        ]);
        setSchools(s);
        setStats(st);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <LoadingState />;

  const searchUrl = `/explore/result?school=${encodeURIComponent(schoolQuery)}&major=${encodeURIComponent(majorQuery)}`;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">去向探索</h1>
        <p className="text-sm text-slate-500 mt-1">
          搜索高校专业的毕业去向分布、重点单位排名和趋势
        </p>
      </div>

      {/* 搜索栏 */}
      <div className="card">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1">学校</label>
            <input
              type="text"
              value={schoolQuery}
              onChange={(e) => setSchoolQuery(e.target.value)}
              placeholder="如：清华大学"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none"
              list="school-list"
            />
            <datalist id="school-list">
              {schools.map((s) => <option key={s.id} value={s.name} />)}
            </datalist>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1">专业</label>
            <input
              type="text"
              value={majorQuery}
              onChange={(e) => setMajorQuery(e.target.value)}
              placeholder="如：机械工程"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none"
            />
          </div>
          <div className="flex items-end">
            <Link href={searchUrl}>
              <Button disabled={!schoolQuery || !majorQuery}>
                <Search className="h-4 w-4" /> 搜索
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* 全局统计 */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-brand-600">{stats.school_count}</p>
            <p className="text-xs text-slate-500">已收录高校</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">{stats.report_count}</p>
            <p className="text-xs text-slate-500">就业报告</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-amber-600">{stats.major_count}</p>
            <p className="text-xs text-slate-500">专业数据</p>
          </div>
        </div>
      )}

      {/* 已收录学校列表 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">已收录高校</h2>
        {schools.length === 0 ? (
          <EmptyState title="暂无数据" description="尚未收录任何高校就业报告" />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {schools.map((s) => (
              <div
                key={s.id}
                className="rounded-lg border border-slate-100 p-4 hover:border-brand-200 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <SchoolIcon className="h-4 w-4 text-brand-500" />
                  <span className="font-medium text-slate-800">{s.name}</span>
                </div>
                <p className="text-xs text-slate-400">
                  {s.report_count} 份报告 · {s.major_count} 个专业
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 创建搜索结果页**

```tsx
// frontend/app/(app)/explore/result/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/router";
import { ArrowLeft, Compass } from "lucide-react";
import { employmentApi } from "@/lib/api";
import { Button } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { DestinationPie, RankingBar, TrendLine } from "@/components/employment-charts";
import type { EmploymentSearchResult } from "@/types";

export default function ExploreResultPage() {
  const params = useSearchParams();
  const school = params.get("school") ?? "";
  const major = params.get("major") ?? "";
  const [data, setData] = useState<EmploymentSearchResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!school || !major) return;
    (async () => {
      try {
        const result = await employmentApi.search({ school, major });
        setData(result);
      } finally {
        setLoading(false);
      }
    })();
  }, [school, major]);

  if (loading) return <LoadingState />;

  if (!data || !data.school || data.records.length === 0) {
    return (
      <div className="space-y-6">
        <Link href="/explore" className="inline-flex items-center text-sm text-brand-600 hover:underline">
          <ArrowLeft className="h-4 w-4" /> 返回搜索
        </Link>
        <EmptyState
          title="未找到匹配数据"
          description={`暂无「${school} · ${major}」的就业去向数据`}
          action={
            <Link href="/explore">
              <Button>查看已收录学校</Button>
            </Link>
          }
        />
      </div>
    );
  }

  const latest = data.records[0];

  return (
    <div className="space-y-6">
      <Link href="/explore" className="inline-flex items-center text-sm text-brand-600 hover:underline">
        <ArrowLeft className="h-4 w-4" /> 返回搜索
      </Link>

      <div>
        <h1 className="page-title">{data.school.name} · {data.major}</h1>
        <p className="text-sm text-slate-500 mt-1">
          {data.records.length} 条记录 · 数据来源：高校就业质量年度报告
        </p>
      </div>

      {/* 卡片一：去向分布 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">毕业去向分布（{latest.year}年）</h2>
        <DestinationPie record={latest} />
        {latest.total_graduates && (
          <p className="text-center text-sm text-slate-400 mt-2">
            毕业总人数：{latest.total_graduates}人
          </p>
        )}
      </div>

      {/* 卡片二：排名 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">重点单位 / 升学去向排名</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h3 className="text-sm font-medium text-slate-600 mb-2">就业单位 Top10</h3>
            <RankingBar data={latest.employer_ranking} title="就业单位" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-slate-600 mb-2">升学去向 Top10</h3>
            <RankingBar data={latest.school_for_further_study} title="升学去向" />
          </div>
        </div>
      </div>

      {/* 卡片三：趋势 */}
      {data.trend && data.trend.years.length > 1 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">多年趋势</h2>
          <TrendLine trend={data.trend} />
        </div>
      )}

      {/* CTA */}
      <div className="card bg-brand-50 border-brand-100">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-slate-800">你的去向是什么？</p>
            <p className="text-sm text-slate-500">记录你的去向决策，与同专业数据对比</p>
          </div>
          <Link href={`/decisions?school=${encodeURIComponent(school)}&major=${encodeURIComponent(major)}`}>
            <Button>
              <Compass className="h-4 w-4" /> 记录去向决策
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 验证前端构建**

Run: `cd /workspace/frontend && npx next build 2>&1 | tail -10`
Expected: 构建成功

- [ ] **Step 5: 提交**

```bash
cd /workspace
git add frontend/app/\(app\)/explore/ frontend/components/employment-charts.tsx
git commit -m "feat(frontend): 新增去向探索页面和三块可视化卡片"
```

---

## Task 9: 导航更新

**Files:**
- Modify: `frontend/components/nav.tsx`

- [ ] **Step 1: 在 NAV_ITEMS 中添加去向探索项**

在 `frontend/components/nav.tsx` 的 `NAV_ITEMS` 数组中，在 `个人看板` 之后添加：

```typescript
import { Telescope } from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "个人看板", icon: LayoutDashboard },
  { href: "/explore", label: "去向探索", icon: Telescope },
  { href: "/decisions", label: "去向决策", icon: Compass },
  { href: "/timeline", label: "成长时间线", icon: History },
  { href: "/skills", label: "技能树", icon: Network },
  { href: "/retrospectives", label: "阶段复盘", icon: ClipboardList },
];
```

- [ ] **Step 2: 验证前端构建**

Run: `cd /workspace/frontend && npx next build 2>&1 | tail -5`
Expected: 构建成功

- [ ] **Step 3: 提交**

```bash
cd /workspace
git add frontend/components/nav.tsx
git commit -m "feat(frontend): 导航栏新增「去向探索」入口"
```

---

## Task 10: 种子数据脚本

**Files:**
- Create: `backend/pipeline/seed.py`

- [ ] **Step 1: 创建种子数据脚本**

```python
# backend/pipeline/seed.py
"""种子数据脚本：配置标杆高校并生成模拟数据用于验证"""
from app.database import SessionLocal
from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree


SEED_SCHOOLS = [
    {
        "name": "清华大学", "slug": "tsinghua", "code": "10003",
        "report_index_url": "https://career.tsinghua.edu.cn/",
        "province": "北京", "level": "985",
    },
    {
        "name": "北京大学", "slug": "pku", "code": "10001",
        "report_index_url": "https://scc.pku.edu.cn/",
        "province": "北京", "level": "985",
    },
    {
        "name": "浙江大学", "slug": "zju", "code": "10335",
        "report_index_url": "https://www.career.zju.edu.cn/",
        "province": "浙江", "level": "985",
    },
]

SEED_DATA = [
    # (school_slug, major, year, degree, total, emp_rate, study_rate, civil_rate, abroad_rate, employers, industries, regions, schools)
    ("tsinghua", "机械工程", 2024, "bachelor", 120, 0.45, 0.35, 0.08, 0.12,
     [{"name": "三一重工", "count": 15}, {"name": "比亚迪", "count": 12}, {"name": "华为", "count": 8}],
     {"制造业": 0.4, "互联网": 0.2, "金融": 0.1},
     {"北京": 0.3, "上海": 0.15, "广东": 0.1},
     [{"name": "清华大学", "count": 20}, {"name": "北京大学", "count": 5}]),
    ("tsinghua", "计算机科学与技术", 2024, "bachelor", 180, 0.55, 0.25, 0.05, 0.15,
     [{"name": "字节跳动", "count": 25}, {"name": "腾讯", "count": 20}, {"name": "阿里巴巴", "count": 15}],
     {"互联网": 0.5, "金融": 0.15, "制造业": 0.1},
     {"北京": 0.4, "上海": 0.2, "广东": 0.15},
     [{"name": "清华大学", "count": 30}, {"name": "斯坦福大学", "count": 8}]),
    ("tsinghua", "电子工程", 2024, "bachelor", 150, 0.50, 0.30, 0.07, 0.13,
     [{"name": "华为", "count": 20}, {"name": "中兴", "count": 10}, {"name": "大疆", "count": 8}],
     {"通讯": 0.35, "互联网": 0.25, "制造业": 0.15},
     {"北京": 0.35, "广东": 0.2, "上海": 0.1},
     [{"name": "清华大学", "count": 25}, {"name": "MIT", "count": 6}]),
    ("pku", "计算机科学与技术", 2024, "bachelor", 160, 0.52, 0.28, 0.06, 0.14,
     [{"name": "百度", "count": 18}, {"name": "字节跳动", "count": 15}, {"name": "腾讯", "count": 12}],
     {"互联网": 0.45, "金融": 0.2, "教育": 0.1},
     {"北京": 0.45, "上海": 0.15, "广东": 0.1},
     [{"name": "北京大学", "count": 28}, {"name": "清华大学", "count": 8}]),
    ("pku", "金融学", 2024, "bachelor", 100, 0.48, 0.32, 0.10, 0.10,
     [{"name": "中金公司", "count": 10}, {"name": "中信证券", "count": 8}, {"name": "工商银行", "count": 6}],
     {"金融": 0.6, "互联网": 0.1, "咨询": 0.1},
     {"北京": 0.5, "上海": 0.25, "深圳": 0.1},
     [{"name": "北京大学", "count": 15}, {"name": "清华大学", "count": 5}]),
    ("pku", "法学", 2024, "bachelor", 90, 0.40, 0.35, 0.15, 0.10,
     [{"name": "金杜律所", "count": 8}, {"name": "方达律所", "count": 6}, {"name": "最高法", "count": 5}],
     {"法律": 0.55, "金融": 0.15, "政府": 0.1},
     {"北京": 0.55, "上海": 0.2, "广东": 0.08},
     [{"name": "北京大学", "count": 18}, {"name": "中国政法大学", "count": 6}]),
    ("zju", "计算机科学与技术", 2024, "bachelor", 200, 0.58, 0.22, 0.05, 0.15,
     [{"name": "阿里巴巴", "count": 30}, {"name": "网易", "count": 18}, {"name": "字节跳动", "count": 15}],
     {"互联网": 0.55, "制造业": 0.1, "金融": 0.1},
     {"浙江": 0.4, "上海": 0.15, "北京": 0.15},
     [{"name": "浙江大学", "count": 35}, {"name": "清华大学", "count": 10}]),
    ("zju", "机械工程", 2024, "bachelor", 130, 0.50, 0.30, 0.08, 0.12,
     [{"name": "吉利汽车", "count": 12}, {"name": "海康威视", "count": 10}, {"name": "大华", "count": 8}],
     {"制造业": 0.45, "互联网": 0.15, "汽车": 0.15},
     {"浙江": 0.45, "上海": 0.15, "江苏": 0.1},
     [{"name": "浙江大学", "count": 22}, {"name": "上海交大", "count": 8}]),
    ("zju", "化学", 2024, "bachelor", 80, 0.42, 0.38, 0.05, 0.15,
     [{"name": "药明康德", "count": 8}, {"name": "恒瑞医药", "count": 6}, {"name": "巴斯夫", "count": 5}],
     {"化工": 0.4, "医药": 0.25, "材料": 0.1},
     {"浙江": 0.35, "上海": 0.2, "江苏": 0.15},
     [{"name": "浙江大学", "count": 20}, {"name": "北大", "count": 6}]),
]

# 2023年数据（简化版，只调整比例略变化）
SEED_DATA_2023 = [
    (*d[:4], d[4], d[5] + 0.03, d[6] - 0.02, d[7], d[8], d[9], d[10], d[11], d[12])
    for d in SEED_DATA
]


def run_seed():
    db = SessionLocal()
    try:
        # 创建学校
        for s in SEED_SCHOOLS:
            existing = db.query(School).filter(School.slug == s["slug"]).first()
            if not existing:
                db.add(School(**s))
        db.commit()

        # 创建报告和就业数据
        for year_data in [SEED_DATA, SEED_DATA_2023]:
            year = 2024 if year_data is SEED_DATA else 2023
            for row in year_data:
                slug, major, _, degree, total, emp_rate, study_rate, civil_rate, abroad_rate, \
                    employers, industries, regions, schools = row

                school = db.query(School).filter(School.slug == slug).first()
                if not school:
                    continue

                # 检查是否已存在
                existing = db.query(ReportRecord).filter(
                    ReportRecord.school_id == school.id,
                    ReportRecord.year == year,
                ).first()
                if existing:
                    continue

                report = ReportRecord(
                    school_id=school.id,
                    year=year,
                    source_url=f"https://{school.report_index_url}{year}/report.htm",
                    parse_status=ParseStatus.published,
                )
                db.add(report)
                db.commit()

                emp = EmploymentData(
                    report_id=report.id,
                    major=major,
                    degree=Degree(degree),
                    total_graduates=total,
                    employment_rate=emp_rate,
                    further_study_rate=study_rate,
                    civil_service_rate=civil_rate,
                    abroad_rate=abroad_rate,
                    startup_rate=0.0,
                    gap_year_rate=0.0,
                    employer_ranking=employers,
                    industry_distribution=industries,
                    destination_region=regions,
                    school_for_further_study=schools,
                )
                db.add(emp)
                db.commit()

        print(f"种子数据导入完成")
        # 统计
        from sqlalchemy import func
        sc = db.query(School).count()
        rc = db.query(ReportRecord).filter(ReportRecord.parse_status == ParseStatus.published).count()
        ec = db.query(EmploymentData).count()
        print(f"学校: {sc}, 已发布报告: {rc}, 就业数据记录: {ec}")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
```

- [ ] **Step 2: 运行种子脚本**

Run: `cd /workspace/backend && python -m pipeline.seed`
Expected: `种子数据导入完成 / 学校: 3, 已发布报告: 18, 就业数据记录: 18`

- [ ] **Step 3: 验证 API 返回种子数据**

Run: `curl -s "http://localhost:8000/api/employment/search?school=清华&major=机械" | python3 -m json.tool | head -20`
Expected: 返回包含去向分布、雇主排名、趋势的 JSON

Run: `curl -s "http://localhost:8000/api/employment/stats" | python3 -m json.tool`
Expected: `school_count: 3, report_count: 18`

- [ ] **Step 4: 提交**

```bash
cd /workspace
git add backend/pipeline/seed.py
git commit -m "feat(pipeline): 种子数据脚本（3校×3专业×2年=18条已发布数据）"
```

---

## 自审清单

**Spec coverage 检查：**
- [x] 2.1 School 模型 → Task 1
- [x] 2.1 ReportRecord 模型 → Task 1
- [x] 2.1 EmploymentData 模型 → Task 1
- [x] 2.2 唯一约束 → Task 1 测试覆盖
- [x] 3.3 fetch → Task 3
- [x] 3.4 extract + LLM → Task 4
- [x] 3.5 review → Task 5
- [x] 3.6 publish → Task 5
- [x] 4.1 搜索 API → Task 6
- [x] 4.2 辅助接口 → Task 6
- [x] 5.2 搜索首页 → Task 8
- [x] 5.3 结果页三块卡片 → Task 8
- [x] 5.4 空结果处理 → Task 8
- [x] 5.5 CTA 衔接 → Task 8
- [x] 5.6 导航更新 → Task 9
- [x] 7.1 配置变更 → Task 2
- [x] 6.1 种子数据 → Task 10

**Placeholder scan：** 无 TBD/TODO，所有代码块完整。

**Type consistency：** `employmentApi.search` 参数与 `search_employment` service 参数一致；`EmploymentSearchResult` 类型与 API 返回结构匹配；`RATE_LABEL` / `RATE_COLORS` 在 charts 组件和 constants 中一致。
