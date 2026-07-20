"""Prometheus-format metrics endpoint for GradPath API.

C9: 新增 POST /api/metrics/web-vitals 端点接收前端 web-vitals 上报。
"""
from collections import defaultdict
from threading import Lock
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from starlette.responses import PlainTextResponse

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.web_vitals_service import (
    ALLOWED_RATINGS,
    ALLOWED_VITAL_NAMES,
    record_web_vital,
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

_lock = Lock()

# In-memory counters
_request_count: dict[str, int] = defaultdict(int)
_error_count: dict[str, int] = defaultdict(int)
_response_times: list[float] = []


def record_request(method: str, path: str, status_code: int, duration_ms: float):
    """Record a request for metrics collection. Called by middleware."""
    status = "error" if status_code >= 400 else "success"
    with _lock:
        _request_count[f'{method}:{path}'] += 1
        _request_count["__total__"] += 1
        if status == "error":
            _error_count[f'{method}:{path}'] += 1
            _error_count["__total__"] += 1
        _response_times.append(duration_ms)
        if len(_response_times) > 10000:
            _response_times.pop(0)


def _histogram_buckets(values: list[float]) -> list[tuple[float, int]]:
    """Compute Prometheus-style histogram buckets."""
    buckets = [50, 100, 200, 500, 1000, 2000, 5000]
    counts = []
    for b in buckets:
        counts.append(sum(1 for v in values if v <= b))
    counts.append(len(values))  # +Inf bucket
    return list(zip(buckets + [float("inf")], counts))


@router.get("", response_class=PlainTextResponse)
def metrics_endpoint():
    """Return Prometheus-format metrics."""
    with _lock:
        total = _request_count.get("__total__", 0)
        errors = _error_count.get("__total__", 0)
        times = list(_response_times)

    lines = [
        "# HELP gradpath_requests_total Total number of requests",
        "# TYPE gradpath_requests_total counter",
        f'gradpath_requests_total {total}',
        "",
        "# HELP gradpath_errors_total Total number of error responses",
        "# TYPE gradpath_errors_total counter",
        f'gradpath_errors_total {errors}',
        "",
        "# HELP gradpath_error_rate Error rate (errors / total)",
        "# TYPE gradpath_error_rate gauge",
        f'gradpath_error_rate {errors / total:.4f}' if total > 0 else "gradpath_error_rate 0.0",
        "",
        "# HELP gradpath_response_time_ms Response time histogram",
        "# TYPE gradpath_response_time_ms histogram",
    ]
    if times:
        buckets = _histogram_buckets(times)
        for upper, count in buckets:
            label = "+Inf" if upper == float("inf") else str(int(upper))
            lines.append(f'gradpath_response_time_ms_bucket{{le="{label}"}} {count}')
        lines.append(
            f"gradpath_response_time_ms_sum {sum(times):.1f}"
        )
        lines.append(f"gradpath_response_time_ms_count {len(times)}")
    else:
        lines.append('gradpath_response_time_ms_bucket{le="+Inf"} 0')
        lines.append("gradpath_response_time_ms_sum 0.0")
        lines.append("gradpath_response_time_ms_count 0")

    lines.append("")
    return PlainTextResponse("\n".join(lines), media_type="text/plain; version=0.0.4")


# ----------------------------------------------------------------------
# C9 Web Vitals 上报端点
# ----------------------------------------------------------------------

class WebVitalReport(BaseModel):
    """前端 web-vitals 上报请求体。"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=16,
        description="指标名：LCP/CLS/INP/TTFB/FCP",
    )
    value: float = Field(
        ...,
        description="指标值（LCP/INP/TTFB/FCP 单位 ms；CLS 无单位）",
    )
    rating: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="评级：good / needs-improvement / poor",
    )
    delta: float = Field(0.0, description="当前值与上次值的差量")
    id: str = Field("", max_length=128, description="web-vitals 库生成的指标 ID")
    page: str = Field("", max_length=500, description="触发指标的页面路径")
    session_id: str = Field("", max_length=128, description="前端会话 ID")
    timestamp: Optional[str] = Field(
        None,
        max_length=64,
        description="前端 ISO 8601 时间戳",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        v_norm = (v or "").upper().strip()
        if v_norm not in ALLOWED_VITAL_NAMES:
            raise ValueError(
                f"不支持的指标名 {v}，仅允许 {sorted(ALLOWED_VITAL_NAMES)}"
            )
        return v_norm

    @field_validator("rating")
    @classmethod
    def _validate_rating(cls, v: str) -> str:
        v_norm = (v or "").lower().strip()
        if v_norm not in ALLOWED_RATINGS:
            raise ValueError(
                f"不支持的评级 {v}，仅允许 {sorted(ALLOWED_RATINGS)}"
            )
        return v_norm


class WebVitalResponse(BaseModel):
    """web-vitals 上报响应。"""
    received: bool = True
    name: str
    value: float
    rating: str


@router.post(
    "/web-vitals",
    response_model=WebVitalResponse,
    status_code=status.HTTP_201_CREATED,
)
def report_web_vitals(
    report: WebVitalReport,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """接收前端 web-vitals 上报。

    - 登录用户上报：将 user_id 关联到事件，便于按用户聚合
    - 持久化到 events 表（event_type=web_vital）
    - 同步更新 Prometheus Gauge（gradpath_web_vitals_*）
    - 同步增加 Prometheus Counter（gradpath_web_vitals_reports_total）

    请求体示例：
        {
            "name": "LCP",
            "value": 2500.5,
            "rating": "good",
            "delta": 100.2,
            "id": "v3-1718923456789-12345",
            "page": "/dashboard",
            "session_id": "sess-abc-123",
            "timestamp": "2026-07-20T10:30:00.000Z"
        }
    """
    event = record_web_vital(
        db=db,
        user_id=user.id,
        name=report.name,
        value=report.value,
        rating=report.rating,
        delta=report.delta,
        metric_id=report.id,
        page=report.page,
        session_id=report.session_id,
        timestamp=report.timestamp,
    )
    return WebVitalResponse(
        name=report.name,
        value=report.value,
        rating=report.rating,
    )


@router.get("/web-vitals/summary")
def get_web_vitals_summary_endpoint(
    page: Optional[str] = Query(None, max_length=500, description="按页面路径过滤"),
    session_id: Optional[str] = Query(None, max_length=128, description="按会话 ID 过滤"),
    limit: int = Query(1000, ge=1, le=10000, description="聚合样本上限"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询 web-vitals 聚合统计（按指标名分组）。

    返回结构：
        {
            "LCP": {"count": 100, "avg": 2500.0, "p50": 2400.0, "p95": 4500.0, "poor_rate": 0.1},
            "CLS": {...},
            ...
        }
    """
    from app.services.web_vitals_service import get_web_vitals_summary

    return get_web_vitals_summary(
        db=db,
        page=page,
        session_id=session_id,
        limit=limit,
    )
