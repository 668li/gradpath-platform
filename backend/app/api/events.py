# backend/app/api/events.py
"""用户行为埋点API — 可用性测试数据采集。

- POST /api/events        批量接收事件（page_view/click/dwell/error/web_vital）
- GET  /api/events/export 导出事件（仅测试环境，供分析脚本）
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.event import Event
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["埋点"])


class EventItem(BaseModel):
    session_id: str = Field(..., description="会话ID")
    event_type: str = Field(..., description="事件类型: page_view/click/dwell/error/web_vital")
    page: str | None = None
    element: str | None = None
    payload: dict[str, Any] | None = None


class EventBatch(BaseModel):
    events: list[EventItem] = Field(..., max_length=50, description="单次最多50条")


class EventExportItem(BaseModel):
    id: int
    user_id: str | None
    session_id: str
    event_type: str
    page: str | None
    element: str | None
    payload: dict[str, Any] | None
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def validate_user_id(cls, v):
        return str(v) if hasattr(v, "hex") else v

    @classmethod
    def validate_created_at(cls, v):
        return v.isoformat() if hasattr(v, "isoformat") else str(v)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_events(
    batch: EventBatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量接收用户行为事件。"""
    try:
        events = [
            Event(
                user_id=user.id,
                session_id=e.session_id,
                event_type=e.event_type,
                page=e.page,
                element=e.element,
                payload=e.payload,
            )
            for e in batch.events
        ]
        db.bulk_save_objects(events)
        db.commit()
        return {"received": len(events)}
    except Exception as e:
        logger.error("事件写入失败: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="事件写入失败")


@router.get("/export", response_model=list[EventExportItem])
def export_events(
    session_id: str | None = Query(None, description="按会话ID过滤"),
    limit: int = Query(10000, ge=1, le=100000),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """导出事件（供分析脚本拉取）。"""
    q = db.query(Event)
    if session_id:
        q = q.filter(Event.session_id == session_id)
    return q.order_by(Event.id.asc()).limit(limit).all()
