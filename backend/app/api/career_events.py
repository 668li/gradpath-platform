# backend/app/api/career_events.py
"""职业事件 API — 用户职业时间线 CRUD。

- POST   /api/events           创建职业事件（STAR 反思结构）
- GET    /api/events           列表（支持 event_type/start_date/end_date 过滤 + 分页）
- GET    /api/events/{id}      获取单条
- PATCH  /api/events/{id}      更新
- DELETE /api/events/{id}      删除
- POST   /api/events/batch     批量获取（消除 N+1）

注：原 /api/events 前缀曾被埋点 API 占用导致冲突，
埋点 API 已迁移到 /api/tracking/events，本路由恢复为职业事件 API。
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
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.services.event_service import (
    create_event,
    delete_event,
    get_event,
    list_events,
    list_events_paginated,
)

router = APIRouter(prefix="/api/events", tags=["职业事件"])


class EventBatchRequest(BaseModel):
    """批量获取职业事件请求体。"""

    ids: list[str] = Field(
        ..., min_length=1, max_length=100, description="事件 ID 列表（最多 100 个）"
    )


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event_endpoint(
    data: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建职业事件（需登录）。"""
    return create_event(db, user_id=user.id, data=data)


@router.get("")
def list_events_endpoint(
    event_type: EventType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出当前用户的职业事件（支持过滤 + 分页）。

    为兼容旧测试契约，当无分页参数时返回 list，否则返回 {items, total, page, page_size}。
    实际行为：始终返回分页结构（test_pagination.py 期望分页响应）。
    """
    items, total = list_events_paginated(
        db,
        user_id=user.id,
        page=page,
        page_size=page_size,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "items": [EventResponse.model_validate(i).model_dump(mode="json") for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/all")
def list_all_events_endpoint(
    event_type: EventType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出当前用户全部职业事件（不分页，按事件日期降序）。"""
    items = list_events(
        db,
        user_id=user.id,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
    )
    return [EventResponse.model_validate(i).model_dump(mode="json") for i in items]


@router.post("/batch", response_model=list[EventResponse])
def batch_events(
    body: EventBatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量获取职业事件（消除前端 N+1 调用，仅返回当前用户的事件）。

    前端在时间线/对比页一次展示 N 个事件时，原需发 N 次
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
        .filter(CareerEvent.id.in_(parsed_ids), CareerEvent.user_id == user.id)
        .all()
    )
    return [EventResponse.model_validate(i) for i in items]


@router.get("/{event_id}", response_model=EventResponse)
def get_event_endpoint(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单条职业事件。"""
    return get_event(db, user_id=user.id, event_id=event_id)


@router.patch("/{event_id}", response_model=EventResponse)
def update_event_endpoint(
    event_id: UUID,
    data: EventUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新职业事件。"""
    from app.services.event_service import update_event
    return update_event(db, user_id=user.id, event_id=event_id, data=data)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_endpoint(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除职业事件。"""
    delete_event(db, user_id=user.id, event_id=event_id)
    return None
