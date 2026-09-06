"""北极星度量报表 API（2026-09-06 性能体检产物）。

北极星 = 条件完成率 + 回传率（next-roadmap 定稿）。此前只有职位级视图和
全站静态 group_by，没有时间序列与比率——「有星没望远镜」。本端点给管理员
一个统一的汇总视图：

- 条件完成率：UserConditionStatus 全表 met/total + 按周序列
- 回传率：PathComparison 中 outcome_status != pending 的占比 + 按周序列
- 回传满意度均分（1-5）

全部只读聚合，admin 门控，Redis 60s 缓存。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.deps import get_admin_user
from app.database import get_db
from app.models.path_comparison import PathComparison
from app.models.user_condition_status import UserConditionStatus

if TYPE_CHECKING:
    from app.models.user import User

router = APIRouter(prefix="/api/north-star", tags=["北极星度量"])

_WEEKS = 8  # 趋势窗口：8 周


def _week_start(dt: datetime) -> str:
    """取所在周的周一（UTC），ISO 日期串。"""
    monday = dt - timedelta(days=dt.weekday())
    return monday.date().isoformat()


def _weekly_series(db: Session) -> list[dict]:
    """近 8 周聚合：每周新建决策数 / 回传数 / 条件记录数 / met 数。"""
    since = datetime.now(timezone.utc) - timedelta(weeks=_WEEKS)

    rows = (
        db.query(PathComparison.created_at, PathComparison.reviewed_at)
        .filter(PathComparison.created_at >= since)
        .all()
    )
    created_by_week: dict[str, int] = {}
    responded_by_week: dict[str, int] = {}
    for created, reviewed in rows:
        wk = _week_start(created)
        created_by_week[wk] = created_by_week.get(wk, 0) + 1
        if reviewed is not None:
            rwk = _week_start(reviewed)
            responded_by_week[rwk] = responded_by_week.get(rwk, 0) + 1

    cond_rows = (
        db.query(UserConditionStatus.created_at, UserConditionStatus.status)
        .filter(UserConditionStatus.created_at >= since)
        .all()
    )
    cond_total_by_week: dict[str, int] = {}
    cond_met_by_week: dict[str, int] = {}
    for created, status in cond_rows:
        wk = _week_start(created)
        cond_total_by_week[wk] = cond_total_by_week.get(wk, 0) + 1
        if status == "met":
            cond_met_by_week[wk] = cond_met_by_week.get(wk, 0) + 1

    series = []
    for i in range(_WEEKS):
        day = (datetime.now(timezone.utc) - timedelta(weeks=_WEEKS - 1 - i))
        wk = _week_start(day)
        series.append(
            {
                "week": wk,
                "decisions": created_by_week.get(wk, 0),
                "responded": responded_by_week.get(wk, 0),
                "condition_records": cond_total_by_week.get(wk, 0),
                "condition_met": cond_met_by_week.get(wk, 0),
            }
        )
    return series


@router.get("/summary")
def north_star_summary(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """北极星汇总：条件完成率 + 回传率（总量比率 + 近 8 周序列）。管理员专用。"""
    cached = cache.get("north_star:summary")
    if cached is not None:
        return cached

    # 条件完成率（全表）
    cond_total = db.query(func.count(UserConditionStatus.id)).scalar() or 0
    cond_met = (
        db.query(func.count(UserConditionStatus.id))
        .filter(UserConditionStatus.status == "met")
        .scalar()
        or 0
    )

    # 回传率（outcome_status 非 pending 且已 review 即算回传）
    pc_total = db.query(func.count(PathComparison.id)).scalar() or 0
    pc_responded = (
        db.query(func.count(PathComparison.id))
        .filter(
            PathComparison.outcome_status.isnot(None),
            PathComparison.outcome_status != "pending",
        )
        .scalar()
        or 0
    )
    avg_satisfaction = (
        db.query(func.avg(PathComparison.satisfaction)).scalar()
    )

    result = {
        "condition_completion": {
            "met": cond_met,
            "total": cond_total,
            "ratio": round(cond_met / cond_total, 4) if cond_total else None,
        },
        "outcome_response": {
            "total": pc_total,
            "responded": pc_responded,
            "ratio": round(pc_responded / pc_total, 4) if pc_total else None,
            "avg_satisfaction": round(float(avg_satisfaction), 2) if avg_satisfaction else None,
        },
        "weekly": _weekly_series(db),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    cache.set("north_star:summary", result, ttl=60)
    return result
