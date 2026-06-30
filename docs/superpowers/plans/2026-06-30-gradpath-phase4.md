# Phase 4 — 公司面试经验聚合 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户匿名分享面试经历，按公司+岗位聚合后展示"这家公司面试官实际看重什么能力"。

**Architecture:** 复用 Phase 3 社区聚合模式——后端新增 `InterviewReport` 模型 + 6 个 API 端点，前端新增面试分享页 + 聚合结果页（含雷达图），导航新增入口。

**Tech Stack:** FastAPI + SQLAlchemy + Pydantic（后端）；Next.js 14 + Recharts + Tailwind（前端）

**Spec:** `docs/superpowers/specs/2026-06-30-gradpath-phase4-design.md`

---

## 文件结构

### 后端（新建）

| 文件 | 职责 |
|------|------|
| `backend/app/models/interview_report.py` | InterviewReport 模型 + InterviewDimension/InterviewResult 枚举 |
| `backend/app/schemas/interview.py` | Pydantic schemas（提交/响应/聚合查询/聚合响应/统计） |
| `backend/app/services/interview_service.py` | 提交(upsert)、查询、删除、聚合、统计、公司列表 |
| `backend/app/api/interview.py` | 6 个 API 端点 |
| `backend/pipeline/seed_interview.py` | 10 家公司约 40 条种子数据 |
| `backend/tests/test_api_interview.py` | 全部测试用例 |

### 后端（修改）

| 文件 | 改动 |
|------|------|
| `backend/app/models/__init__.py` | 注册 InterviewReport + 枚举 |
| `backend/app/main.py` | 挂载 interview_router |

### 前端（新建）

| 文件 | 职责 |
|------|------|
| `frontend/app/(app)/interview/page.tsx` | 面试分享提交页 |
| `frontend/app/(app)/interview/result/page.tsx` | 公司面试聚合结果页（雷达图+柱状图+饼图） |

### 前端（修改）

| 文件 | 改动 |
|------|------|
| `frontend/types/index.ts` | 新增 InterviewReport 等类型 |
| `frontend/lib/api.ts` | 新增 interviewApi |
| `frontend/lib/constants.ts` | 新增维度/结果标签映射 |
| `frontend/components/nav.tsx` | 新增"面试经验"导航项 |

---

## Task 1: 后端模型 — InterviewReport

**Files:**
- Create: `backend/app/models/interview_report.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建模型文件**

创建 `backend/app/models/interview_report.py`：

```python
# backend/app/models/interview_report.py
"""公司面试经验报告模型 — 用户匿名分享面试经历，聚合后展示"这家公司面试官看重什么"。"""
import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class InterviewDimension(str, enum.Enum):
    algorithm = "algorithm"
    system_design = "system_design"
    project_depth = "project_depth"
    culture_fit = "culture_fit"
    communication = "communication"
    domain_knowledge = "domain"
    behavior = "behavior"


class InterviewResult(str, enum.Enum):
    offer = "offer"
    rejected = "rejected"
    pending = "pending"


class InterviewReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "interview_reports"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "company", "position", "interview_year",
            name="uq_user_company_pos_year",
        ),
    )

    community_report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("community_reports.id"), nullable=True
    )
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))
    interview_year: Mapped[int] = mapped_column(Integer, nullable=False)
    rounds: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[InterviewResult] = mapped_column(
        Enum(InterviewResult), default=InterviewResult.pending, nullable=False
    )
    dimensions: Mapped[list] = mapped_column(JSONB, default=list)
    difficulty: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
```

- [ ] **Step 2: 注册到 models/__init__.py**

在 `backend/app/models/__init__.py` 末尾添加导入和 `__all__` 条目：

```python
from app.models.interview_report import InterviewDimension, InterviewReport, InterviewResult
```

在 `__all__` 列表中添加：

```python
    "InterviewReport", "InterviewDimension", "InterviewResult",
```

- [ ] **Step 3: 验证模型可被导入**

Run: `cd /workspace/backend && python -c "from app.models.interview_report import InterviewReport, InterviewDimension, InterviewResult; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/interview_report.py backend/app/models/__init__.py
git commit -m "feat(phase4): add InterviewReport model with dimensions and result enums"
```

---

## Task 2: 后端 Schemas

**Files:**
- Create: `backend/app/schemas/interview.py`

- [ ] **Step 1: 创建 schema 文件**

创建 `backend/app/schemas/interview.py`：

```python
# backend/app/schemas/interview.py
"""公司面试经验报告的 Pydantic Schema 定义。"""
from pydantic import BaseModel, field_validator


class InterviewSubmit(BaseModel):
    company: str
    position: str
    interview_year: int
    city: str | None = None
    rounds: int | None = None
    result: str = "pending"
    dimensions: list[str] = []
    difficulty: int | None = None
    summary: str | None = None
    community_report_id: str | None = None


class InterviewReportResponse(BaseModel):
    id: str
    company: str
    position: str
    interview_year: int
    city: str | None = None
    rounds: int | None = None
    result: str
    dimensions: list[str] = []
    difficulty: int | None = None
    summary: str | None = None
    community_report_id: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("id", "community_report_id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        if v is None:
            return v
        return str(v) if hasattr(v, "value") or isinstance(v, object) else v

    @field_validator("result", mode="before")
    @classmethod
    def convert_enum(cls, v):
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)


class InterviewAggregateQuery(BaseModel):
    company: str
    position: str | None = None


class InterviewAggregateResponse(BaseModel):
    company: str
    position: str | None = None
    sample_count: int
    sufficient: bool
    avg_difficulty: float | None = None
    avg_rounds: float | None = None
    result_distribution: dict[str, float] | None = None
    dimension_frequency: dict[str, float] | None = None
    common_positions: list[dict] | None = None


class InterviewStats(BaseModel):
    total_reports: int
    company_count: int
    position_count: int


class CompanyQuery(BaseModel):
    keyword: str = ""
```

- [ ] **Step 2: 验证 schema 可被导入**

Run: `cd /workspace/backend && python -c "from app.schemas.interview import InterviewSubmit, InterviewAggregateResponse; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/interview.py
git commit -m "feat(phase4): add Pydantic schemas for interview report API"
```

---

## Task 3: 后端 Service

**Files:**
- Create: `backend/app/services/interview_service.py`

- [ ] **Step 1: 创建 service 文件**

创建 `backend/app/services/interview_service.py`：

```python
# backend/app/services/interview_service.py
"""公司面试经验报告服务层 — 提交、查询、删除与聚合统计。"""
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.interview_report import InterviewReport
from app.schemas.interview import (
    InterviewAggregateResponse,
    InterviewStats,
    InterviewSubmit,
)
from app.services.employment_service import escape_like

MIN_SAMPLE = 3


def submit_report(db: Session, user_id: UUID, data: InterviewSubmit) -> InterviewReport:
    """提交面试报告（upsert：同一用户 + 同一公司 + 同一岗位 + 同一年唯一）。"""
    existing = (
        db.query(InterviewReport)
        .filter(
            InterviewReport.user_id == user_id,
            InterviewReport.company == data.company,
            InterviewReport.position == data.position,
            InterviewReport.interview_year == data.interview_year,
        )
        .first()
    )
    if existing:
        for key, value in data.model_dump().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    report = InterviewReport(user_id=user_id, **data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_my_reports(db: Session, user_id: UUID) -> list[InterviewReport]:
    """获取当前用户提交的所有面试报告。"""
    return (
        db.query(InterviewReport)
        .filter(InterviewReport.user_id == user_id)
        .order_by(InterviewReport.interview_year.desc())
        .all()
    )


def delete_report(db: Session, user_id: UUID, report_id: str) -> None:
    """删除当前用户指定的面试报告。"""
    try:
        rid = uuid.UUID(report_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在"
        )
    report = (
        db.query(InterviewReport)
        .filter(
            InterviewReport.id == rid,
            InterviewReport.user_id == user_id,
        )
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在"
        )
    db.delete(report)
    db.commit()


def aggregate(
    db: Session, company: str, position: str | None = None
) -> InterviewAggregateResponse:
    """聚合统计：模糊匹配公司与岗位，返回考察维度频率、难度分布、结果分布。

    当样本量 < MIN_SAMPLE 时仅返回 sample_count，不返回分布数据（隐私保护）。
    """
    filters = [
        InterviewReport.company.ilike(f"%{escape_like(company)}%", escape="\\"),
    ]
    if position:
        filters.append(
            InterviewReport.position.ilike(f"%{escape_like(position)}%", escape="\\")
        )

    sample_count = (
        db.query(func.count(InterviewReport.id)).filter(*filters).scalar() or 0
    )

    if sample_count < MIN_SAMPLE:
        return InterviewAggregateResponse(
            company=company,
            position=position,
            sample_count=sample_count,
            sufficient=False,
        )

    # 平均难度（仅非空值）
    avg_difficulty = (
        db.query(func.avg(InterviewReport.difficulty))
        .filter(*filters, InterviewReport.difficulty.isnot(None))
        .scalar()
    )

    # 平均轮数（仅非空值）
    avg_rounds = (
        db.query(func.avg(InterviewReport.rounds))
        .filter(*filters, InterviewReport.rounds.isnot(None))
        .scalar()
    )

    # 结果分布（比例）
    result_rows = (
        db.query(
            InterviewReport.result,
            func.count(InterviewReport.id),
        )
        .filter(*filters)
        .group_by(InterviewReport.result)
        .all()
    )
    result_distribution = {
        r.value: count / sample_count for r, count in result_rows
    }

    # 考察维度频率：由于 dimensions 存在 JSONB 数组中，
    # 需要逐行统计（SQLite 测试环境不支持 JSONB 查询）
    all_reports = (
        db.query(InterviewReport.dimensions)
        .filter(*filters)
        .all()
    )
    dim_count: dict[str, int] = {}
    for (dims,) in all_reports:
        if dims:
            for d in dims:
                dim_count[d] = dim_count.get(d, 0) + 1
    dimension_frequency = {
        d: count / sample_count for d, count in dim_count.items()
    }

    # 常见岗位（仅在不指定岗位时返回）
    common_positions = None
    if not position:
        pos_rows = (
            db.query(
                InterviewReport.position,
                func.count(InterviewReport.id),
            )
            .filter(*filters)
            .group_by(InterviewReport.position)
            .order_by(func.count(InterviewReport.id).desc())
            .limit(10)
            .all()
        )
        common_positions = [
            {"name": name, "count": count} for name, count in pos_rows
        ]

    return InterviewAggregateResponse(
        company=company,
        position=position,
        sample_count=sample_count,
        sufficient=True,
        avg_difficulty=round(float(avg_difficulty), 1) if avg_difficulty else None,
        avg_rounds=round(float(avg_rounds), 1) if avg_rounds else None,
        result_distribution=result_distribution,
        dimension_frequency=dimension_frequency,
        common_positions=common_positions,
    )


def get_stats(db: Session) -> InterviewStats:
    """全局统计：报告总数、覆盖公司数、覆盖岗位数。"""
    total = db.query(func.count(InterviewReport.id)).scalar() or 0
    company_count = (
        db.query(func.count(func.distinct(InterviewReport.company))).scalar() or 0
    )
    position_count = (
        db.query(func.count(func.distinct(InterviewReport.position))).scalar() or 0
    )
    return InterviewStats(
        total_reports=total,
        company_count=company_count,
        position_count=position_count,
    )


def list_companies(db: Session, keyword: str = "") -> list[dict]:
    """已收录公司列表（含样本数），支持模糊搜索。"""
    filters = []
    if keyword:
        filters.append(
            InterviewReport.company.ilike(
                f"%{escape_like(keyword)}%", escape="\\"
            )
        )
    rows = (
        db.query(
            InterviewReport.company,
            func.count(InterviewReport.id),
        )
        .filter(*filters)
        .group_by(InterviewReport.company)
        .order_by(func.count(InterviewReport.id).desc())
        .limit(50)
        .all()
    )
    return [{"name": name, "count": count} for name, count in rows]
```

- [ ] **Step 2: 验证 service 可被导入**

Run: `cd /workspace/backend && python -c "from app.services.interview_service import submit_report, aggregate, get_stats; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/interview_service.py
git commit -m "feat(phase4): add interview service with submit, aggregate, stats, companies"
```

---

## Task 4: 后端 API 路由

**Files:**
- Create: `backend/app/api/interview.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建 API 路由文件**

创建 `backend/app/api/interview.py`：

```python
# backend/app/api/interview.py
"""公司面试经验报告 API 路由。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.interview import (
    CompanyQuery,
    InterviewAggregateQuery,
    InterviewAggregateResponse,
    InterviewReportResponse,
    InterviewStats,
    InterviewSubmit,
)
from app.services.interview_service import (
    aggregate,
    delete_report,
    get_my_reports,
    get_stats,
    list_companies,
    submit_report,
)

router = APIRouter(prefix="/api/interview", tags=["面试经验"])


@router.post("/submit", response_model=InterviewReportResponse)
def submit(
    body: InterviewSubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return submit_report(db, user.id, body)


@router.get("/my-reports", response_model=list[InterviewReportResponse])
def my_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_my_reports(db, user.id)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    report_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_report(db, user.id, report_id)


@router.post("/aggregate", response_model=InterviewAggregateResponse)
def aggregate_endpoint(
    body: InterviewAggregateQuery,
    db: Session = Depends(get_db),
):
    return aggregate(db, body.company, body.position)


@router.get("/stats", response_model=InterviewStats)
def stats(db: Session = Depends(get_db)):
    return get_stats(db)


@router.post("/companies", response_model=list[dict])
def companies(
    body: CompanyQuery,
    db: Session = Depends(get_db),
):
    return list_companies(db, body.keyword)
```

- [ ] **Step 2: 挂载到 main.py**

在 `backend/app/main.py` 中添加导入和路由挂载。

在现有导入区域添加：

```python
from app.api.interview import router as interview_router
```

在 `app.include_router(community_router)` 之后添加：

```python
app.include_router(interview_router)
```

- [ ] **Step 3: 验证路由注册**

Run: `cd /workspace/backend && python -c "from app.main import app; routes = [r.path for r in app.routes]; print('/api/interview/submit' in routes)"`
Expected: 输出 `True`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/interview.py backend/app/main.py
git commit -m "feat(phase4): add interview API router with 6 endpoints"
```

---

## Task 5: 后端测试

**Files:**
- Create: `backend/tests/test_api_interview.py`

- [ ] **Step 1: 创建测试文件**

创建 `backend/tests/test_api_interview.py`：

```python
# backend/tests/test_api_interview.py
"""公司面试经验报告 API 测试。"""
import pytest


# ======================================================================
# 辅助函数
# ======================================================================

def _submit_report(client, headers, **overrides):
    """通过 API 提交一条面试报告，返回响应。"""
    payload = {
        "company": "腾讯",
        "position": "后端开发",
        "interview_year": 2024,
        "city": "深圳",
        "rounds": 3,
        "result": "offer",
        "dimensions": ["algorithm", "system_design"],
        "difficulty": 4,
        "summary": "侧重算法和系统设计",
    }
    payload.update(overrides)
    return client.post("/api/interview/submit", headers=headers, json=payload)


# ======================================================================
# 提交报告
# ======================================================================

class TestSubmitReport:
    def test_submit_report(self, auth_headers, client):
        """提交报告成功。"""
        resp = _submit_report(client, auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"] == "腾讯"
        assert data["position"] == "后端开发"
        assert data["interview_year"] == 2024
        assert data["result"] == "offer"
        assert data["dimensions"] == ["algorithm", "system_design"]
        assert data["difficulty"] == 4
        assert "id" in data

    def test_submit_report_minimal(self, auth_headers, client):
        """仅填写必填字段也可提交。"""
        resp = client.post(
            "/api/interview/submit",
            headers=auth_headers,
            json={
                "company": "字节跳动",
                "position": "前端开发",
                "interview_year": 2024,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["city"] is None
        assert data["rounds"] is None
        assert data["result"] == "pending"
        assert data["dimensions"] == []
        assert data["difficulty"] is None


class TestSubmitDuplicateUpsert:
    def test_submit_duplicate_upsert(self, auth_headers, client):
        """同一用户同公司同岗位同年重复提交应更新已有记录。"""
        resp1 = _submit_report(client, auth_headers, result="offer")
        assert resp1.status_code == 200
        report_id = resp1.json()["id"]

        resp2 = _submit_report(client, auth_headers, result="rejected")
        assert resp2.status_code == 200
        assert resp2.json()["id"] == report_id
        assert resp2.json()["result"] == "rejected"

        resp3 = client.get("/api/interview/my-reports", headers=auth_headers)
        assert resp3.status_code == 200
        assert len(resp3.json()) == 1


class TestMyReports:
    def test_my_reports(self, auth_headers, client):
        """查看自己的报告列表。"""
        for year in [2022, 2023, 2024]:
            _submit_report(client, auth_headers, interview_year=year)

        resp = client.get("/api/interview/my-reports", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        years = [r["interview_year"] for r in data]
        assert years == [2024, 2023, 2022]

    def test_my_reports_empty(self, auth_headers, client):
        """无报告时返回空列表。"""
        resp = client.get("/api/interview/my-reports", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestDeleteReport:
    def test_delete_report(self, auth_headers, client):
        """删除自己的报告。"""
        resp = _submit_report(client, auth_headers)
        report_id = resp.json()["id"]

        resp_del = client.delete(
            f"/api/interview/{report_id}", headers=auth_headers
        )
        assert resp_del.status_code == 204

        resp_list = client.get("/api/interview/my-reports", headers=auth_headers)
        assert len(resp_list.json()) == 0

    def test_delete_nonexistent_report(self, auth_headers, client):
        """删除不存在的报告返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.delete(f"/api/interview/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404


# ======================================================================
# 聚合统计
# ======================================================================

class TestAggregate:
    def test_aggregate_sufficient(self, auth_headers, client):
        """样本 >= 3 时返回完整分布数据。"""
        _submit_report(
            client, auth_headers, interview_year=2022,
            dimensions=["algorithm", "system_design"], difficulty=4, result="offer",
        )
        _submit_report(
            client, auth_headers, interview_year=2023,
            dimensions=["algorithm", "project_depth"], difficulty=3, result="rejected",
        )
        _submit_report(
            client, auth_headers, interview_year=2024,
            dimensions=["algorithm", "system_design", "communication"], difficulty=5, result="offer",
        )

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 3
        assert data["sufficient"] is True

        # 维度频率
        dims = data["dimension_frequency"]
        assert dims is not None
        assert pytest.approx(dims["algorithm"], rel=1e-2) == 1.0
        assert pytest.approx(dims["system_design"], rel=1e-2) == 2 / 3

        # 结果分布
        results = data["result_distribution"]
        assert results is not None
        assert pytest.approx(results["offer"], rel=1e-2) == 2 / 3
        assert pytest.approx(results["rejected"], rel=1e-2) == 1 / 3

        # 平均难度
        assert data["avg_difficulty"] == 4.0

    def test_aggregate_insufficient(self, auth_headers, client):
        """样本 < 3 时仅返回 sample_count，不返回分布数据。"""
        _submit_report(client, auth_headers, interview_year=2024)
        _submit_report(client, auth_headers, interview_year=2023)

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 2
        assert data["sufficient"] is False
        assert data["dimension_frequency"] is None
        assert data["result_distribution"] is None

    def test_aggregate_zero_samples(self, client):
        """无匹配数据时 sample_count=0。"""
        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "不存在的公司"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 0
        assert data["sufficient"] is False

    def test_aggregate_fuzzy_match(self, auth_headers, client):
        """ILIKE 模糊匹配。"""
        for year in [2022, 2023, 2024]:
            _submit_report(client, auth_headers, interview_year=year)

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 3

    def test_aggregate_with_position_filter(self, auth_headers, client):
        """岗位过滤。"""
        _submit_report(client, auth_headers, interview_year=2022, position="后端开发")
        _submit_report(client, auth_headers, interview_year=2023, position="前端开发")
        _submit_report(client, auth_headers, interview_year=2024, position="后端开发")

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯", "position": "后端"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sample_count"] == 2

    def test_aggregate_common_positions(self, auth_headers, client):
        """不指定岗位时返回常见岗位列表。"""
        _submit_report(client, auth_headers, interview_year=2022, position="后端开发")
        _submit_report(client, auth_headers, interview_year=2023, position="前端开发")
        _submit_report(client, auth_headers, interview_year=2024, position="后端开发")

        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["common_positions"] is not None
        assert len(data["common_positions"]) == 2


# ======================================================================
# 全局统计
# ======================================================================

class TestStats:
    def test_stats(self, auth_headers, client):
        """全局统计。"""
        _submit_report(client, auth_headers, company="腾讯", position="后端开发")
        _submit_report(client, auth_headers, company="腾讯", position="前端开发", interview_year=2023)
        _submit_report(client, auth_headers, company="字节跳动", position="后端开发", interview_year=2022)

        resp = client.get("/api/interview/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 3
        assert data["company_count"] == 2
        assert data["position_count"] == 2

    def test_stats_empty(self, client):
        """空数据库时统计为 0。"""
        resp = client.get("/api/interview/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_reports"] == 0


# ======================================================================
# 公司列表
# ======================================================================

class TestCompanies:
    def test_companies(self, auth_headers, client):
        """公司列表。"""
        _submit_report(client, auth_headers, company="腾讯", position="后端开发")
        _submit_report(client, auth_headers, company="腾讯", position="前端开发", interview_year=2023)
        _submit_report(client, auth_headers, company="字节跳动", position="后端开发", interview_year=2022)

        resp = client.post(
            "/api/interview/companies",
            json={"keyword": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "腾讯"
        assert data[0]["count"] == 2

    def test_companies_search(self, auth_headers, client):
        """模糊搜索公司。"""
        _submit_report(client, auth_headers, company="腾讯科技")
        _submit_report(client, auth_headers, company="字节跳动")

        resp = client.post(
            "/api/interview/companies",
            json={"keyword": "腾"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "腾讯科技"


# ======================================================================
# 权限控制
# ======================================================================

class TestAuth:
    def test_anonymous_submit_fails(self, client):
        """未登录不能提交报告。"""
        resp = client.post(
            "/api/interview/submit",
            json={"company": "腾讯", "position": "后端开发", "interview_year": 2024},
        )
        assert resp.status_code == 401

    def test_anonymous_my_reports_fails(self, client):
        """未登录不能查看自己的报告。"""
        resp = client.get("/api/interview/my-reports")
        assert resp.status_code == 401

    def test_anonymous_delete_fails(self, client):
        """未登录不能删除报告。"""
        resp = client.delete("/api/interview/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401

    def test_aggregate_no_auth_required(self, client):
        """聚合查询不需要登录。"""
        resp = client.post(
            "/api/interview/aggregate",
            json={"company": "腾讯"},
        )
        assert resp.status_code == 200

    def test_stats_no_auth_required(self, client):
        """全局统计不需要登录。"""
        resp = client.get("/api/interview/stats")
        assert resp.status_code == 200
```

- [ ] **Step 2: 运行测试验证全部通过**

Run: `cd /workspace/backend && python -m pytest tests/test_api_interview.py -v --tb=short`
Expected: 所有测试通过

- [ ] **Step 3: 运行全量测试确保无回归**

Run: `cd /workspace/backend && python -m pytest --tb=short -q`
Expected: 所有测试通过（原有 96 + 新增约 20 = 约 116 个）

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_api_interview.py
git commit -m "test(phase4): add 20+ test cases for interview API endpoints"
```

---

## Task 6: 后端种子数据

**Files:**
- Create: `backend/pipeline/seed_interview.py`

- [ ] **Step 1: 创建种子数据脚本**

创建 `backend/pipeline/seed_interview.py`：

```python
# backend/pipeline/seed_interview.py
"""面试经验种子数据脚本。

为 10 家公司创建约 40 条面试经验报告。
复用 Phase 3 的社区种子用户（community_seed_1~10@test.com）。
统一密码：Test1234!

注意：InterviewReport 的唯一约束为 (user_id, company, position, interview_year)，
同一用户对同一公司同岗位同年只能有一条记录。
"""
from app.core.security import hash_password
from app.database import SessionLocal
from app.models.interview_report import (
    InterviewDimension,
    InterviewReport,
    InterviewResult,
)
from app.models.user import User

SEED_PASSWORD = "Test1234!"

# 每个种子用户及其提交的面试报告列表
SEED_DATA = [
    # ---- 用户1: 腾讯 (4条) ----
    {
        "email": "interview_seed_1@test.com",
        "name": "面试用户1",
        "reports": [
            {"company": "腾讯", "position": "后端开发", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design", "project_depth"], "difficulty": 4,
             "summary": "三轮技术面，算法题中等难度，系统设计考了短链接"},
            {"company": "腾讯", "position": "前端开发", "interview_year": 2023, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "project_depth", "communication"], "difficulty": 3,
             "summary": "前端框架原理问得多，有手写代码环节"},
            {"company": "字节跳动", "position": "后端开发", "interview_year": 2024, "city": "北京",
             "rounds": 4, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "system_design"], "difficulty": 5,
             "summary": "算法题偏难，第四轮挂了"},
            {"company": "阿里巴巴", "position": "数据分析", "interview_year": 2022, "city": "杭州",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["project_depth", "communication", "behavior"], "difficulty": 3,
             "summary": "偏业务理解，有案例分析环节"},
        ],
    },
    # ---- 用户2: 字节跳动 (4条) ----
    {
        "email": "interview_seed_2@test.com",
        "name": "面试用户2",
        "reports": [
            {"company": "字节跳动", "position": "后端开发", "interview_year": 2024, "city": "北京",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design", "project_depth"], "difficulty": 5,
             "summary": "算法题难度高，系统设计考了Feed流"},
            {"company": "字节跳动", "position": "客户端开发", "interview_year": 2023, "city": "北京",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "project_depth", "domain"], "difficulty": 4,
             "summary": "客户端性能优化问得多"},
            {"company": "腾讯", "position": "后端开发", "interview_year": 2022, "city": "深圳",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "system_design"], "difficulty": 4,
             "summary": "二面系统设计没答好"},
            {"company": "百度", "position": "算法工程师", "interview_year": 2024, "city": "北京",
             "rounds": 4, "result": InterviewResult.pending,
             "dimensions": ["algorithm", "domain", "project_depth"], "difficulty": 4,
             "summary": "NLP方向，问了Transformer原理"},
        ],
    },
    # ---- 用户3: 阿里巴巴 (3条) ----
    {
        "email": "interview_seed_3@test.com",
        "name": "面试用户3",
        "reports": [
            {"company": "阿里巴巴", "position": "后端开发", "interview_year": 2024, "city": "杭州",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["system_design", "project_depth", "culture_fit"], "difficulty": 4,
             "summary": "系统设计考了电商秒杀，有HR文化面"},
            {"company": "阿里巴巴", "position": "数据分析", "interview_year": 2023, "city": "杭州",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["project_depth", "communication"], "difficulty": 3,
             "summary": "业务案例不够深入"},
            {"company": "字节跳动", "position": "后端开发", "interview_year": 2022, "city": "北京",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design"], "difficulty": 5,
             "summary": "算法考了动态规划"},
        ],
    },
    # ---- 用户4: 华为 (4条) ----
    {
        "email": "interview_seed_4@test.com",
        "name": "面试用户4",
        "reports": [
            {"company": "华为", "position": "硬件工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth", "culture_fit"], "difficulty": 3,
             "summary": "专业知识问得细，有上机测试"},
            {"company": "华为", "position": "算法工程师", "interview_year": 2023, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "domain", "project_depth"], "difficulty": 4,
             "summary": "CV方向，问了目标检测算法"},
            {"company": "大疆", "position": "算法工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "project_depth"], "difficulty": 4,
             "summary": "二面项目深挖没答好"},
            {"company": "腾讯", "position": "后端开发", "interview_year": 2022, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design"], "difficulty": 4,
             "summary": "常规后端面试"},
        ],
    },
    # ---- 用户5: 中金公司 (3条) ----
    {
        "email": "interview_seed_5@test.com",
        "name": "面试用户5",
        "reports": [
            {"company": "中金公司", "position": "投行分析师", "interview_year": 2024, "city": "北京",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "communication", "behavior"], "difficulty": 4,
             "summary": "财务建模+行为面试，英文面占比较大"},
            {"company": "中金公司", "position": "研究员", "interview_year": 2023, "city": "北京",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["domain", "communication"], "difficulty": 4,
             "summary": "行业研究深度不够"},
            {"company": "中信证券", "position": "研究员", "interview_year": 2024, "city": "北京",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["domain", "behavior", "communication"], "difficulty": 3,
             "summary": "面试相对常规，偏行业理解"},
        ],
    },
    # ---- 用户6: 百度 (4条) ----
    {
        "email": "interview_seed_6@test.com",
        "name": "面试用户6",
        "reports": [
            {"company": "百度", "position": "算法工程师", "interview_year": 2024, "city": "北京",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design", "domain"], "difficulty": 4,
             "summary": "推荐系统方向，考了召回排序"},
            {"company": "百度", "position": "后端开发", "interview_year": 2023, "city": "北京",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "system_design"], "difficulty": 4,
             "summary": "系统设计没答好"},
            {"company": "字节跳动", "position": "算法工程师", "interview_year": 2022, "city": "北京",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "domain", "project_depth"], "difficulty": 5,
             "summary": "NLP方向，考了BERT"},
            {"company": "腾讯", "position": "算法工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.pending,
             "dimensions": ["algorithm", "domain"], "difficulty": 4,
             "summary": "还在等结果"},
        ],
    },
    # ---- 用户7: 三一重工 (3条) ----
    {
        "email": "interview_seed_7@test.com",
        "name": "面试用户7",
        "reports": [
            {"company": "三一重工", "position": "机械工程师", "interview_year": 2024, "city": "长沙",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth", "culture_fit"], "difficulty": 2,
             "summary": "偏专业知识，面试氛围友好"},
            {"company": "三一重工", "position": "项目经理", "interview_year": 2023, "city": "长沙",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["project_depth", "communication", "behavior"], "difficulty": 3,
             "summary": "项目管理案例面试"},
            {"company": "比亚迪", "position": "电池工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["domain", "culture_fit"], "difficulty": 2,
             "summary": "专业面+HR面，比较顺利"},
        ],
    },
    # ---- 用户8: 比亚迪 (3条) ----
    {
        "email": "interview_seed_8@test.com",
        "name": "面试用户8",
        "reports": [
            {"company": "比亚迪", "position": "嵌入式工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth", "culture_fit"], "difficulty": 3,
             "summary": "嵌入式基础+项目经验"},
            {"company": "比亚迪", "position": "电池工程师", "interview_year": 2023, "city": "深圳",
             "rounds": 2, "result": InterviewResult.rejected,
             "dimensions": ["domain"], "difficulty": 3,
             "summary": "专业知识不够深"},
            {"company": "华为", "position": "硬件工程师", "interview_year": 2022, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth"], "difficulty": 3,
             "summary": "硬件基础+电路设计"},
        ],
    },
    # ---- 用户9: 大疆 (4条) ----
    {
        "email": "interview_seed_9@test.com",
        "name": "面试用户9",
        "reports": [
            {"company": "大疆", "position": "算法工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "project_depth", "domain"], "difficulty": 4,
             "summary": "视觉算法方向，考了SLAM"},
            {"company": "大疆", "position": "嵌入式工程师", "interview_year": 2023, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth", "algorithm"], "difficulty": 4,
             "summary": "C++底层+RTOS"},
            {"company": "华为", "position": "算法工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "domain"], "difficulty": 4,
             "summary": "一面算法没做好"},
            {"company": "腾讯", "position": "算法工程师", "interview_year": 2022, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design"], "difficulty": 4,
             "summary": "推荐系统方向"},
        ],
    },
    # ---- 用户10: 中信证券 (4条) ----
    {
        "email": "interview_seed_10@test.com",
        "name": "面试用户10",
        "reports": [
            {"company": "中信证券", "position": "研究员", "interview_year": 2024, "city": "北京",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "communication", "behavior"], "difficulty": 4,
             "summary": "行业研究+财务分析"},
            {"company": "中信证券", "position": "投行", "interview_year": 2023, "city": "北京",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["domain", "behavior"], "difficulty": 4,
             "summary": "估值建模环节不够熟练"},
            {"company": "中金公司", "position": "投行分析师", "interview_year": 2022, "city": "北京",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["domain", "communication", "behavior"], "difficulty": 5,
             "summary": "全英文面试，准备不充分"},
            {"company": "百度", "position": "数据分析", "interview_year": 2024, "city": "北京",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "project_depth", "communication"], "difficulty": 3,
             "summary": "SQL+业务理解"},
        ],
    },
]


def run_seed():
    """执行种子数据导入。

    幂等：先清理旧种子数据，再重新导入。
    """
    db = SessionLocal()
    try:
        # ---- 清理旧种子数据 ----
        seed_users = (
            db.query(User)
            .filter(User.email.like("interview_seed_%@test.com"))
            .all()
        )
        for user in seed_users:
            db.query(InterviewReport).filter(
                InterviewReport.user_id == user.id
            ).delete()
            db.delete(user)
        db.commit()

        # ---- 重新导入 ----
        total_reports = 0
        for user_data in SEED_DATA:
            user = User(
                email=user_data["email"],
                password_hash=hash_password(SEED_PASSWORD),
                name=user_data["name"],
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            for report_data in user_data["reports"]:
                report = InterviewReport(user_id=user.id, **report_data)
                db.add(report)
                db.commit()
                total_reports += 1

        print("面试经验种子数据导入完成")
        from sqlalchemy import func

        user_count = (
            db.query(User)
            .filter(User.email.like("interview_seed_%@test.com"))
            .count()
        )
        report_count = db.query(InterviewReport).count()
        company_count = (
            db.query(func.count(func.distinct(InterviewReport.company)))
            .scalar()
            or 0
        )
        position_count = (
            db.query(func.count(func.distinct(InterviewReport.position)))
            .scalar()
            or 0
        )
        print(
            f"种子用户: {user_count}, 面试报告: {report_count}, "
            f"覆盖公司: {company_count}, 覆盖岗位: {position_count}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
```

- [ ] **Step 2: 运行种子脚本**

Run: `cd /workspace/backend && python -m pipeline.seed_interview`
Expected: 输出 `面试经验种子数据导入完成` 和统计信息

- [ ] **Step 3: 验证 API 返回种子数据**

Run: `curl -s http://localhost:8000/api/interview/stats`
Expected: `{"total_reports":36,"company_count":10,"position_count":12}` 或类似

- [ ] **Step 4: Commit**

```bash
git add backend/pipeline/seed_interview.py
git commit -m "feat(phase4): add seed data with 36 interview reports across 10 companies"
```

---

## Task 7: 前端类型 + API + 常量

**Files:**
- Modify: `frontend/types/index.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/constants.ts`

- [ ] **Step 1: 在 types/index.ts 末尾添加面试相关类型**

在 `frontend/types/index.ts` 文件末尾添加：

```typescript
// ===== 面试经验 =====
export interface InterviewReport {
  id: string;
  company: string;
  position: string;
  interview_year: number;
  city: string | null;
  rounds: number | null;
  result: string;
  dimensions: string[];
  difficulty: number | null;
  summary: string | null;
  community_report_id: string | null;
}

export interface InterviewSubmit {
  company: string;
  position: string;
  interview_year: number;
  city?: string;
  rounds?: number;
  result?: string;
  dimensions?: string[];
  difficulty?: number;
  summary?: string;
  community_report_id?: string;
}

export interface InterviewAggregate {
  company: string;
  position: string | null;
  sample_count: number;
  sufficient: boolean;
  avg_difficulty: number | null;
  avg_rounds: number | null;
  result_distribution: Record<string, number> | null;
  dimension_frequency: Record<string, number> | null;
  common_positions: { name: string; count: number }[] | null;
}

export interface InterviewStats {
  total_reports: number;
  company_count: number;
  position_count: number;
}

export interface CompanyInfo {
  name: string;
  count: number;
}
```

- [ ] **Step 2: 在 api.ts 中添加 interviewApi**

在 `frontend/lib/api.ts` 中：

在 import 块中添加面试相关类型导入（添加到现有 import 列表末尾的 `} from "@/types";` 之前）：

```typescript
  CompanyInfo,
  InterviewAggregate,
  InterviewReport,
  InterviewStats,
  InterviewSubmit,
```

在文件末尾（`communityApi` 之后）添加：

```typescript
// ===== 面试经验 =====
export const interviewApi = {
  submit: (body: InterviewSubmit) =>
    request<InterviewReport>("/api/interview/submit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  myReports: () => request<InterviewReport[]>("/api/interview/my-reports"),
  remove: (id: string) =>
    request<void>(`/api/interview/${id}`, { method: "DELETE" }),
  aggregate: (body: { company: string; position?: string }) =>
    request<InterviewAggregate>("/api/interview/aggregate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  stats: () => request<InterviewStats>("/api/interview/stats"),
  companies: (keyword: string = "") =>
    request<CompanyInfo[]>("/api/interview/companies", {
      method: "POST",
      body: JSON.stringify({ keyword }),
    }),
};
```

- [ ] **Step 3: 在 constants.ts 末尾添加面试相关常量**

在 `frontend/lib/constants.ts` 文件末尾添加：

```typescript
// ===== 面试经验 =====
export const INTERVIEW_DIMENSION_LABEL: Record<string, string> = {
  algorithm: "算法/编程",
  system_design: "系统设计",
  project_depth: "项目深度",
  culture_fit: "文化匹配",
  communication: "沟通表达",
  domain: "专业知识",
  behavior: "行为面试",
};

export const INTERVIEW_DIMENSIONS = [
  "algorithm",
  "system_design",
  "project_depth",
  "culture_fit",
  "communication",
  "domain",
  "behavior",
];

export const INTERVIEW_RESULT_LABEL: Record<string, string> = {
  offer: "拿到 offer",
  rejected: "未通过",
  pending: "进行中",
};

export const INTERVIEW_RESULTS = ["offer", "rejected", "pending"];

export const INTERVIEW_RESULT_COLOR: Record<string, string> = {
  offer: "#16a34a",
  rejected: "#dc2626",
  pending: "#d97706",
};
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd /workspace/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 无错误输出

- [ ] **Step 5: Commit**

```bash
git add frontend/types/index.ts frontend/lib/api.ts frontend/lib/constants.ts
git commit -m "feat(phase4): add interview types, API client, and constants"
```

---

## Task 8: 前端面试提交页

**Files:**
- Create: `frontend/app/(app)/interview/page.tsx`

- [ ] **Step 1: 创建面试提交页**

创建 `frontend/app/(app)/interview/page.tsx`。此页面参照 `community/page.tsx` 的模式，包含：顶部统计卡片、提交表单（公司/岗位/城市/年份/轮数/结果/考察维度多选/难度/总结）、我的提交记录列表。

完整代码参见 `community/page.tsx` 的结构模式，主要差异：
- 表单字段改为面试相关（公司、岗位、城市、面试年份、轮数、结果按钮组、考察维度多选按钮组、难度 1-5 星、一句话总结）
- 使用 `interviewApi` 替代 `communityApi`
- 使用 `INTERVIEW_DIMENSIONS` / `INTERVIEW_DIMENSION_LABEL` / `INTERVIEW_RESULTS` / `INTERVIEW_RESULT_LABEL` 常量
- 跳转聚合结果用 `encodeParam(company)` 传参

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Send, Trash2, BarChart3, Briefcase, Star } from "lucide-react";
import { interviewApi } from "@/lib/api";
import { Button, Input, Select } from "@/components/ui/form-controls";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import {
  INTERVIEW_DIMENSIONS,
  INTERVIEW_DIMENSION_LABEL,
  INTERVIEW_RESULTS,
  INTERVIEW_RESULT_LABEL,
} from "@/lib/constants";
import type {
  CompanyInfo,
  InterviewReport,
  InterviewStats,
  InterviewSubmit,
} from "@/types";

const YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025];

function encodeParam(value: string): string {
  return btoa(unescape(encodeURIComponent(value)));
}

export default function InterviewPage() {
  const router = useRouter();
  const toast = useToast();

  const [stats, setStats] = useState<InterviewStats | null>(null);
  const [companies, setCompanies] = useState<CompanyInfo[]>([]);
  const [myReports, setMyReports] = useState<InterviewReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // 表单状态
  const [company, setCompany] = useState("");
  const [position, setPosition] = useState("");
  const [city, setCity] = useState("");
  const [interviewYear, setInterviewYear] = useState<number>(2024);
  const [rounds, setRounds] = useState<number>(3);
  const [result, setResult] = useState("pending");
  const [dimensions, setDimensions] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState<number>(3);
  const [summary, setSummary] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [st, comps, mine] = await Promise.all([
          interviewApi.stats(),
          interviewApi.companies(),
          interviewApi.myReports(),
        ]);
        setStats(st);
        setCompanies(comps);
        setMyReports(mine);
      } catch (err) {
        toast.push(
          err instanceof Error ? err.message : "加载数据失败",
          "error",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  const toggleDimension = (dim: string) => {
    setDimensions((prev) =>
      prev.includes(dim) ? prev.filter((d) => d !== dim) : [...prev, dim],
    );
  };

  const refreshStats = async () => {
    try {
      const st = await interviewApi.stats();
      setStats(st);
    } catch {
      // 静默失败
    }
  };

  const handleSubmit = async () => {
    const co = company.trim();
    const pos = position.trim();
    if (!co || !pos) {
      toast.push("请填写公司和岗位", "error");
      return;
    }

    const body: InterviewSubmit = {
      company: co,
      position: pos,
      interview_year: interviewYear,
    };
    if (city.trim()) body.city = city.trim();
    if (rounds) body.rounds = rounds;
    if (result) body.result = result;
    if (dimensions.length > 0) body.dimensions = dimensions;
    if (difficulty) body.difficulty = difficulty;
    if (summary.trim()) body.summary = summary.trim();

    setSubmitting(true);
    try {
      const report = await interviewApi.submit(body);
      toast.push("提交成功，感谢你的分享！", "success");
      setMyReports((prev) => [report, ...prev]);
      setCompany("");
      setPosition("");
      setCity("");
      setSummary("");
      setDimensions([]);
      refreshStats();
    } catch (err) {
      toast.push(
        err instanceof Error ? err.message : "提交失败",
        "error",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await interviewApi.remove(id);
      setMyReports((prev) => prev.filter((r) => r.id !== id));
      toast.push("已删除该记录", "success");
      refreshStats();
    } catch (err) {
      toast.push(
        err instanceof Error ? err.message : "删除失败",
        "error",
      );
    }
  };

  const handleViewAggregate = () => {
    const co = company.trim();
    if (!co) {
      toast.push("请先填写公司名称", "info");
      return;
    }
    const c = encodeParam(co);
    router.push(`/interview/result?c=${c}`);
  };

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">面试经验</h1>
        <p className="text-sm text-slate-500 mt-1">
          匿名分享你的面试经历，聚合后展示"这家公司面试官实际看重什么"
        </p>
      </div>

      {/* 统计 */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-brand-600">
              {stats.total_reports}
            </p>
            <p className="text-xs text-slate-500">面试样本</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">
              {stats.company_count}
            </p>
            <p className="text-xs text-slate-500">覆盖公司</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-amber-600">
              {stats.position_count}
            </p>
            <p className="text-xs text-slate-500">覆盖岗位</p>
          </div>
        </div>
      )}

      {/* 提交表单 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <Briefcase className="h-4 w-4 text-brand-500" />
          匿名提交面试经验
        </h2>

        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                公司 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="如：腾讯"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                list="interview-company-list"
              />
              <datalist id="interview-company-list">
                {companies.map((c) => (
                  <option key={c.name} value={c.name} />
                ))}
              </datalist>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                岗位 <span className="text-red-500">*</span>
              </label>
              <Input
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                placeholder="如：后端开发"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                城市
              </label>
              <Input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="如：深圳"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                面试年份 <span className="text-red-500">*</span>
              </label>
              <Select
                value={interviewYear}
                onChange={(e) => setInterviewYear(Number(e.target.value))}
              >
                {YEARS.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1">
                面试轮数
              </label>
              <Select
                value={rounds}
                onChange={(e) => setRounds(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((r) => (
                  <option key={r} value={r}>
                    {r} 轮
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {/* 面试结果 */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-2">
              面试结果 <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {INTERVIEW_RESULTS.map((r) => {
                const active = result === r;
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setResult(r)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-brand-300 hover:text-brand-600",
                    )}
                  >
                    {INTERVIEW_RESULT_LABEL[r] ?? r}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 考察维度多选 */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-2">
              考察维度 <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {INTERVIEW_DIMENSIONS.map((dim) => {
                const active = dimensions.includes(dim);
                return (
                  <button
                    key={dim}
                    type="button"
                    onClick={() => toggleDimension(dim)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-brand-300 hover:text-brand-600",
                    )}
                  >
                    {INTERVIEW_DIMENSION_LABEL[dim] ?? dim}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 难度评分 */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-2">
              难度评分
            </label>
            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setDifficulty(star)}
                  className="p-1"
                  aria-label={`${star} 星`}
                >
                  <Star
                    className={cn(
                      "h-6 w-6 transition-colors",
                      star <= difficulty
                        ? "fill-amber-400 text-amber-400"
                        : "text-slate-300 hover:text-amber-300",
                    )}
                  />
                </button>
              ))}
              <span className="text-sm text-slate-500 ml-2">
                {difficulty}/5
              </span>
            </div>
          </div>

          {/* 一句话总结 */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1">
              一句话总结
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="如：侧重算法和系统设计，三轮技术面"
              maxLength={200}
              rows={2}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button onClick={handleSubmit} loading={submitting}>
              <Send className="h-4 w-4" /> 提交报告
            </Button>
            <Button variant="secondary" onClick={handleViewAggregate}>
              <BarChart3 className="h-4 w-4" /> 查看聚合结果
            </Button>
            <span className="text-xs text-slate-400">
              数据完全匿名，仅用于聚合统计
            </span>
          </div>
        </div>
      </div>

      {/* 我的提交记录 */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-4">我的提交记录</h2>
        {myReports.length === 0 ? (
          <EmptyState
            title="暂无提交记录"
            description="提交你的第一份面试报告，它会出现在这里"
          />
        ) : (
          <div className="space-y-3">
            {myReports.map((r) => (
              <div
                key={r.id}
                className="rounded-lg border border-slate-100 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-slate-800">
                        {r.company} · {r.position}
                      </span>
                      <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                        {INTERVIEW_RESULT_LABEL[r.result] ?? r.result}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">
                      {r.interview_year}年{r.city ? ` · ${r.city}` : ""}
                      {r.rounds ? ` · ${r.rounds}轮` : ""}
                      {r.difficulty ? ` · 难度${r.difficulty}/5` : ""}
                    </p>
                    {r.dimensions.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {r.dimensions.map((d) => (
                          <span
                            key={d}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500"
                          >
                            {INTERVIEW_DIMENSION_LABEL[d] ?? d}
                          </span>
                        ))}
                      </div>
                    )}
                    {r.summary && (
                      <p className="mt-1 text-sm text-slate-600">{r.summary}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Link
                      href={`/interview/result?c=${encodeParam(r.company)}`}
                      className="text-xs text-brand-600 hover:underline"
                    >
                      查看聚合
                    </Link>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                      aria-label="删除记录"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/\(app\)/interview/page.tsx
git commit -m "feat(phase4): add interview submit page with form and my reports list"
```

---

## Task 9: 前端面试聚合结果页

**Files:**
- Create: `frontend/app/(app)/interview/result/page.tsx`

- [ ] **Step 1: 创建聚合结果页**

创建 `frontend/app/(app)/interview/result/page.tsx`，参照 `community/result/page.tsx` 模式，包含：考察维度雷达图（RadarChart）、面试结果饼图、常见岗位排名。

```tsx
"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, AlertTriangle, Briefcase } from "lucide-react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { interviewApi } from "@/lib/api";
import { LoadingState, EmptyState } from "@/components/ui/empty";
import { Button } from "@/components/ui/form-controls";
import { useToast } from "@/components/ui/toast";
import { RankingBar } from "@/components/employment-charts";
import {
  INTERVIEW_DIMENSION_LABEL,
  INTERVIEW_DIMENSIONS,
  INTERVIEW_RESULT_LABEL,
  INTERVIEW_RESULT_COLOR,
} from "@/lib/constants";
import type { InterviewAggregate } from "@/types";

const CHART_HEIGHT = 300;

function InterviewResultContent() {
  const router = useRouter();
  const toast = useToast();
  const searchParams = useSearchParams();
  const cEncoded = searchParams.get("c") ?? "";
  const company = cEncoded ? decodeURIComponent(escape(atob(cEncoded))) : "";

  const [data, setData] = useState<InterviewAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    if (!company) {
      setRedirecting(true);
      router.replace("/interview");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const result = await interviewApi.aggregate({ company });
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          toast.push(
            err instanceof Error ? err.message : "加载聚合数据失败",
            "error",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [company, router, toast]);

  if (redirecting || loading) return <LoadingState />;

  if (!data || data.sample_count === 0) {
    return (
      <div className="space-y-6">
        <Link
          href="/interview"
          className="inline-flex items-center text-sm text-brand-600 hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> 返回面试经验
        </Link>
        <EmptyState
          title="暂无面试数据"
          description={`「${company}」还没有人分享面试经历`}
          action={
            <Link href="/interview">
              <Button>
                <Briefcase className="h-4 w-4" /> 我来分享面试经历
              </Button>
            </Link>
          }
        />
      </div>
    );
  }

  const insufficient = !data.sufficient || data.sample_count < 3;

  // 雷达图数据
  const radarData = data.dimension_frequency
    ? INTERVIEW_DIMENSIONS.map((dim) => ({
        dimension: INTERVIEW_DIMENSION_LABEL[dim] ?? dim,
        frequency: Math.round((data.dimension_frequency![dim] ?? 0) * 100),
      }))
    : [];

  // 饼图数据
  const pieData = data.result_distribution
    ? Object.entries(data.result_distribution)
        .filter(([, v]) => v > 0)
        .map(([key, value]) => ({
          name: INTERVIEW_RESULT_LABEL[key] ?? key,
          value: value,
          key,
        }))
    : [];

  return (
    <div className="space-y-6">
      <Link
        href="/interview"
        className="inline-flex items-center text-sm text-brand-600 hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> 返回面试经验
      </Link>

      <div>
        <h1 className="page-title">{company}</h1>
        <p className="text-sm text-slate-500 mt-1">
          面试聚合数据 · 共 {data.sample_count} 份匿名报告
        </p>
      </div>

      {/* 样本数提示 */}
      {insufficient ? (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" />
          <div>
            <p className="text-sm font-medium text-amber-800">样本不足</p>
            <p className="text-xs text-amber-700 mt-0.5">
              当前仅 {data.sample_count} 份样本（建议至少 3 份），数据仅供参考，请谨慎解读。
            </p>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 px-4 py-3">
          <Briefcase className="h-5 w-5 shrink-0 text-green-600" />
          <p className="text-sm text-green-800">
            已聚合 {data.sample_count} 份匿名报告，数据具备一定参考价值
          </p>
        </div>
      )}

      {/* 基本信息 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card text-center">
          <p className="text-2xl font-bold text-brand-600">
            {data.avg_difficulty ? `${data.avg_difficulty}/5` : "—"}
          </p>
          <p className="text-xs text-slate-500">平均难度</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-green-600">
            {data.avg_rounds ? `${data.avg_rounds}` : "—"}
          </p>
          <p className="text-xs text-slate-500">平均轮数</p>
        </div>
      </div>

      {/* 考察维度雷达图 */}
      {radarData.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">考察维度频率</h2>
          <div
            role="img"
            aria-label={`${company}面试考察维度频率：${radarData.map((d) => `${d.dimension}${d.frequency}%`).join("，")}`}
          >
            <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ fontSize: 12, fill: "#64748b" }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: "#94a3b8" }}
                />
                <Radar
                  name="频率"
                  dataKey="frequency"
                  stroke="#3377f6"
                  fill="#3377f6"
                  fillOpacity={0.3}
                />
                <Tooltip
                  formatter={(v: number) => `${v}%`}
                />
              </RadarChart>
            </ResponsiveContainer>
            <span className="sr-only">
              {`${company}面试考察维度频率：${radarData.map((d) => `${d.dimension}${d.frequency}%`).join("，")}`}
            </span>
          </div>
        </div>
      )}

      {/* 面试结果分布 */}
      {pieData.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">面试结果分布</h2>
          <div
            role="img"
            aria-label={`${company}面试结果分布：${pieData.map((d) => `${d.name}${(d.value * 100).toFixed(0)}%`).join("，")}`}
          >
            <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ name, value }) =>
                    `${name} ${(value * 100).toFixed(0)}%`
                  }
                >
                  {pieData.map((d) => (
                    <Cell key={d.key} fill={INTERVIEW_RESULT_COLOR[d.key] ?? "#999"} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                />
              </PieChart>
            </ResponsiveContainer>
            <span className="sr-only">
              {`${company}面试结果分布：${pieData.map((d) => `${d.name}${(d.value * 100).toFixed(0)}%`).join("，")}`}
            </span>
          </div>
        </div>
      )}

      {/* 常见岗位 */}
      {data.common_positions && data.common_positions.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">常见岗位</h2>
          <RankingBar data={data.common_positions} title="常见岗位" />
        </div>
      )}

      {/* CTA */}
      <div className="card bg-brand-50 border-brand-100">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-slate-800">你的面试经历是什么？</p>
            <p className="text-sm text-slate-500">
              分享你的面试经验，让这份数据更准确
            </p>
          </div>
          <Link href="/interview">
            <Button>
              <Briefcase className="h-4 w-4" /> 提交我的经历
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function InterviewResultPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <InterviewResultContent />
    </Suspense>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/\(app\)/interview/result/page.tsx
git commit -m "feat(phase4): add interview aggregate result page with radar chart"
```

---

## Task 10: 导航更新 + 构建验证

**Files:**
- Modify: `frontend/components/nav.tsx`

- [ ] **Step 1: 在 nav.tsx 中添加面试经验导航项**

在 `frontend/components/nav.tsx` 中：

1. 在 lucide-react import 中添加 `Briefcase`：

```typescript
  Briefcase,
  Users,
```

2. 在 `NAV_ITEMS` 数组中，在 `{ href: "/community", label: "社区数据", icon: Users }` 之后添加：

```typescript
  { href: "/interview", label: "面试经验", icon: Briefcase },
```

- [ ] **Step 2: 验证前端构建通过**

Run: `cd /workspace/frontend && npm run build 2>&1 | tail -20`
Expected: 构建成功，包含 `/interview` 和 `/interview/result` 路由

- [ ] **Step 3: 验证后端全量测试通过**

Run: `cd /workspace/backend && python -m pytest --tb=short -q`
Expected: 所有测试通过

- [ ] **Step 4: Commit**

```bash
git add frontend/components/nav.tsx
git commit -m "feat(phase4): add interview nav item and verify build"
```

---

## 自审检查

**Spec 覆盖率：**
- [x] InterviewReport 模型 + 枚举 → Task 1
- [x] Pydantic schemas → Task 2
- [x] 6 个 API 端点（submit/my-reports/delete/aggregate/stats/companies） → Task 3+4
- [x] 聚合逻辑（模糊匹配+隐私阈值+维度频率+结果分布） → Task 3
- [x] 测试用例（20+ 覆盖所有端点+边界情况） → Task 5
- [x] 种子数据（10公司约40条） → Task 6
- [x] 前端类型+API+常量 → Task 7
- [x] 提交页（表单+我的记录+统计） → Task 8
- [x] 聚合结果页（雷达图+饼图+常见岗位） → Task 9
- [x] 导航+构建验证 → Task 10

**占位符扫描：** 无 TBD/TODO

**类型一致性：** InterviewDimension 枚举值 `domain_knowledge` 在前端常量中对应 key `domain`，与 schema 的 `dimensions: list[str]` 一致
