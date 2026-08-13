"""职业成长事件 API — /api/events

CRUD 端点供前端时间线页面使用。注意：与埋点 API（/api/tracking/events）不同，
本模块管理用户的职业成长事件（入职、晋升、项目完成等），含 STAR+R 反思。
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.career_event import CareerEvent, EventType
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.event import EventCreate, EventResponse, EventUpdate

router = APIRouter(prefix="/api/events", tags=["职业事件"])


class EventBatchRequest(BaseModel):
    """批量获取职业事件请求体。"""

    ids: list[str] = Field(
        ..., min_length=1, max_length=100, description="事件 ID 列表（最多 100 个）"
    )


@router.get("", response_model=PaginatedResponse[EventResponse])
def list_events(
    event_type: EventType | None = Query(None, description="按事件类型过滤"),
    start_date: date | None = Query(None, description="开始日期（含）"),
    end_date: date | None = Query(None, description="结束日期（含）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出当前用户的职业事件，支持按类型和日期范围过滤。"""
    q = db.query(CareerEvent).filter(CareerEvent.user_id == user.id)
    if event_type is not None:
        q = q.filter(CareerEvent.event_type == event_type)
    if start_date is not None:
        q = q.filter(CareerEvent.event_date >= start_date)
    if end_date is not None:
        q = q.filter(CareerEvent.event_date <= end_date)

    total = q.count()
    items = (
        q.order_by(CareerEvent.event_date.desc(), CareerEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/batch", response_model=list[EventResponse])
def batch_events(
    body: EventBatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量获取职业事件（消除前端 N+1 调用，仅返回当前用户的事件）。

    前端在时间线详情/对比页一次展示 N 个事件时，原需发 N 次
    `/events/{id}` 请求；本接口一次返回所有事件信息。
    """
    raw_ids = body.ids[:100]
    parsed_ids: list[UUID] = []
    for raw in raw_ids:
        try:
            parsed_ids.append(UUID(raw))
        except (ValueError, AttributeError):
            continue
    if not parsed_ids:
        return []
    # 安全约束：仅返回当前用户的事件，防止越权
    items = (
        db.query(CareerEvent)
        .filter(
            CareerEvent.id.in_(parsed_ids),
            CareerEvent.user_id == user.id,
        )
        .all()
    )
    return [EventResponse.model_validate(e) for e in items]


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单个职业事件。"""
    event = db.query(CareerEvent).filter(
        CareerEvent.id == event_id, CareerEvent.user_id == user.id
    ).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事件不存在")
    return event


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建职业事件。"""
    event = CareerEvent(
        user_id=user.id,
        event_date=data.event_date,
        event_type=data.event_type,
        title=data.title,
        description=data.description,
        situation=data.situation,
        task=data.task,
        action=data.action,
        result=data.result,
        reflection=data.reflection,
        skills_gained=data.skills_gained,
        impact_metrics=data.impact_metrics,
        mood=data.mood,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID,
    data: EventUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新职业事件（部分更新）。"""
    event = db.query(CareerEvent).filter(
        CareerEvent.id == event_id, CareerEvent.user_id == user.id
    ).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事件不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除职业事件。"""
    event = db.query(CareerEvent).filter(
        CareerEvent.id == event_id, CareerEvent.user_id == user.id
    ).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事件不存在")
    db.delete(event)
    db.commit()
