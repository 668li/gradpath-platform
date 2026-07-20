from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.models.career_event import CareerEvent, EventType
from app.schemas.event import EventCreate, EventUpdate


def _invalidate_user_context_cache(user_id: UUID) -> None:
    """事件 CRUD 后失效用户上下文缓存（build_user_context 依赖 CareerEvent）。"""
    try:
        cache.delete(f"user_context:{user_id}")
    except Exception:
        pass


def create_event(db: Session, user_id: UUID, data: EventCreate) -> CareerEvent:
    event = CareerEvent(user_id=user_id, **data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    _invalidate_user_context_cache(user_id)
    return event


def list_events(
    db: Session,
    user_id: UUID,
    event_type: EventType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[CareerEvent]:
    query = db.query(CareerEvent).filter(CareerEvent.user_id == user_id)
    if event_type:
        query = query.filter(CareerEvent.event_type == event_type)
    if start_date:
        query = query.filter(CareerEvent.event_date >= start_date)
    if end_date:
        query = query.filter(CareerEvent.event_date <= end_date)
    return query.order_by(CareerEvent.event_date.desc()).all()


def list_events_paginated(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
    event_type: EventType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[list[CareerEvent], int]:
    """分页查询职业事件列表（按事件日期降序），支持类型与日期范围过滤。"""
    query = db.query(CareerEvent).filter(CareerEvent.user_id == user_id)
    if event_type:
        query = query.filter(CareerEvent.event_type == event_type)
    if start_date:
        query = query.filter(CareerEvent.event_date >= start_date)
    if end_date:
        query = query.filter(CareerEvent.event_date <= end_date)
    total = query.count()
    items = (
        query.order_by(CareerEvent.event_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_event(db: Session, user_id: UUID, event_id: UUID) -> CareerEvent:
    event = (
        db.query(CareerEvent)
        .filter(CareerEvent.id == event_id, CareerEvent.user_id == user_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="事件不存在")
    return event


def update_event(db: Session, user_id: UUID, event_id: UUID, data: EventUpdate) -> CareerEvent:
    event = get_event(db, user_id, event_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    _invalidate_user_context_cache(user_id)
    return event


def delete_event(db: Session, user_id: UUID, event_id: UUID) -> None:
    event = get_event(db, user_id, event_id)
    db.delete(event)
    db.commit()
    _invalidate_user_context_cache(user_id)
