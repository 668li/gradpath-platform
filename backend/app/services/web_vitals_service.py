"""Web Vitals 数据采集与分析服务 (C9)。

职责：
- record_web_vital: 持久化 web-vitals 上报数据到 events 表（event_type=web_vital）
- 同时调用 prometheus_client 指标记录实时 Gauge
- 提供 track_event / track_page_view / track_click 通用埋点辅助函数

设计原则：
1. 上报失败不能影响用户体验 — 所有写库 / 写 prometheus 异常被捕获并记录日志
2. events 表复用 — 不引入新表，web-vital 事件作为 Event.event_type="web_vital" 存储
3. payload schema 包含 name/value/rating/delta/metric_id/page/session_id/timestamp
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.event import Event

logger = logging.getLogger(__name__)


# 允许的 web-vitals 指标名 — 防止恶意上报注入未知指标
ALLOWED_VITAL_NAMES = frozenset({"LCP", "CLS", "INP", "TTFB", "FCP"})

# 允许的评级 — 与 web-vitals 库保持一致
ALLOWED_RATINGS = frozenset({"good", "needs-improvement", "poor"})

# 单条上报字段长度限制
PAGE_MAX_LENGTH = 500
SESSION_ID_MAX_LENGTH = 128
METRIC_ID_MAX_LENGTH = 128


def record_web_vital(
    db: Session,
    user_id: Optional[UUID],
    name: str,
    value: float,
    rating: str,
    delta: float = 0.0,
    metric_id: str = "",
    page: str = "",
    session_id: str = "",
    timestamp: Optional[str] = None,
) -> Event:
    """记录一条 web-vital 指标。

    Args:
        db: 数据库会话
        user_id: 用户 ID（未登录时为 None）
        name: 指标名（LCP/CLS/INP/TTFB/FCP）
        value: 指标值
        rating: 评级（good/needs-improvement/poor）
        delta: 当前值与上次值的差量
        metric_id: web-vitals 库生成的指标 ID
        page: 触发指标的页面路径
        session_id: 前端生成的会话 ID
        timestamp: 前端 ISO 8601 时间戳（可选）

    Returns:
        已写入的 Event 实例（已 commit）
    """
    # 输入规范化
    name_norm = (name or "").upper().strip()
    rating_norm = (rating or "").lower().strip()
    page_norm = (page or "")[:PAGE_MAX_LENGTH]
    session_id_norm = (session_id or "")[:SESSION_ID_MAX_LENGTH]
    metric_id_norm = (metric_id or "")[:METRIC_ID_MAX_LENGTH]

    if name_norm not in ALLOWED_VITAL_NAMES:
        logger.warning("拒绝未知 web-vital 指标名: %s", name)
        raise ValueError(f"不支持的 web-vital 指标名: {name}")

    if rating_norm not in ALLOWED_RATINGS:
        logger.warning("拒绝未知 web-vital 评级: %s", rating)
        raise ValueError(f"不支持的 web-vital 评级: {rating}")

    payload: dict[str, Any] = {
        "name": name_norm,
        "value": float(value),
        "rating": rating_norm,
        "delta": float(delta),
        "metric_id": metric_id_norm,
        "page": page_norm,
        "client_timestamp": timestamp,
    }

    event = Event(
        user_id=user_id,
        session_id=session_id_norm or "unknown",
        event_type="web_vital",
        page=page_norm or None,
        element=None,
        payload=payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # 同步写入 Prometheus 指标（失败不抛错）
    try:
        from app.metrics import record_web_vital as _record_metric

        _record_metric(name_norm, float(value), rating_norm, page_norm)
    except Exception as e:
        logger.debug("写入 Prometheus web-vital 指标失败: %s", e)

    logger.info(
        "web-vital 已记录: user=%s name=%s value=%.3f rating=%s page=%s",
        user_id,
        name_norm,
        float(value),
        rating_norm,
        page_norm,
    )
    return event


# ----------------------------------------------------------------------
# 通用埋点辅助函数 — 供 service 层调用
# ----------------------------------------------------------------------

def track_event(
    db: Session,
    user_id: Optional[UUID],
    session_id: str,
    event_type: str,
    page: Optional[str] = None,
    element: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> Event:
    """通用埋点 — 记录任意事件到 events 表。

    Args:
        event_type: 事件类型（page_view/click/dwell/error/web_vital/...）
        page: 触发事件的页面路径
        element: 触发事件的元素标识（如按钮 data-track-id）
        payload: 任意结构化事件数据
    """
    if not session_id or len(session_id) > SESSION_ID_MAX_LENGTH:
        session_id = "unknown"
    if event_type and len(event_type) > 50:
        event_type = event_type[:50]

    event = Event(
        user_id=user_id,
        session_id=session_id,
        event_type=event_type,
        page=page,
        element=element,
        payload=payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def track_page_view(
    db: Session,
    user_id: Optional[UUID],
    session_id: str,
    page: str,
    referrer: Optional[str] = None,
) -> Event:
    """记录页面浏览事件。"""
    payload: dict[str, Any] = {}
    if referrer:
        payload["referrer"] = referrer[:500]
    return track_event(
        db=db,
        user_id=user_id,
        session_id=session_id,
        event_type="page_view",
        page=page,
        payload=payload or None,
    )


def track_click(
    db: Session,
    user_id: Optional[UUID],
    session_id: str,
    page: str,
    element: str,
    text: Optional[str] = None,
    tag: Optional[str] = None,
) -> Event:
    """记录点击事件。"""
    payload: dict[str, Any] = {}
    if text:
        payload["text"] = text[:200]
    if tag:
        payload["tag"] = tag[:50]
    return track_event(
        db=db,
        user_id=user_id,
        session_id=session_id,
        event_type="click",
        page=page,
        element=element,
        payload=payload or None,
    )


def get_web_vitals_summary(
    db: Session,
    page: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 1000,
) -> dict[str, dict[str, float]]:
    """聚合查询 web-vitals 指标统计。

    Returns:
        按指标名分组的统计字典：
        {
            "LCP": {"count": 100, "avg": 2500.0, "p50": 2400.0, "p95": 4500.0, "poor_rate": 0.1},
            ...
        }
    """
    q = db.query(Event).filter(Event.event_type == "web_vital")
    if page:
        q = q.filter(Event.page == page)
    if session_id:
        q = q.filter(Event.session_id == session_id)
    events = q.order_by(Event.created_at.desc()).limit(limit).all()

    by_name: dict[str, list[float]] = {}
    poor_count: dict[str, int] = {}
    for ev in events:
        payload = ev.payload or {}
        name = payload.get("name")
        value = payload.get("value")
        rating = payload.get("rating")
        if not name or not isinstance(value, (int, float)):
            continue
        by_name.setdefault(name, []).append(float(value))
        if rating == "poor":
            poor_count[name] = poor_count.get(name, 0) + 1

    summary: dict[str, dict[str, float]] = {}
    for name, values in by_name.items():
        if not values:
            continue
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        # p50 取 lower median（n 为偶数时取左中位数），与 NumPy percentile(method='lower') 一致
        # 这样 4 个样本 [1000, 2000, 4000, 6000] 的 p50 = 2000，符合直觉
        summary[name] = {
            "count": float(n),
            "avg": round(sum(sorted_vals) / n, 3),
            "p50": round(sorted_vals[(n - 1) // 2], 3),
            "p95": round(sorted_vals[min(int(n * 0.95), n - 1)], 3),
            "p99": round(sorted_vals[min(int(n * 0.99), n - 1)], 3),
            "poor_rate": round(poor_count.get(name, 0) / n, 4),
        }
    return summary
