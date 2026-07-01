from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.retrospective import Retrospective
from app.schemas.retrospective import RetroCreate, RetroUpdate


def create_retrospective(db: Session, user_id: UUID, data: RetroCreate) -> Retrospective:
    retro = Retrospective(user_id=user_id, **data.model_dump())
    db.add(retro)
    db.commit()
    db.refresh(retro)
    return retro


def list_retrospectives(db: Session, user_id: UUID) -> list[Retrospective]:
    return (
        db.query(Retrospective)
        .filter(Retrospective.user_id == user_id)
        .order_by(Retrospective.period_end.desc())
        .all()
    )


def list_retrospectives_paginated(
    db: Session, user_id: UUID, page: int = 1, page_size: int = 20
) -> tuple[list[Retrospective], int]:
    """分页查询复盘列表（按复盘时段结束日期降序）。"""
    query = db.query(Retrospective).filter(Retrospective.user_id == user_id)
    total = query.count()
    items = (
        query.order_by(Retrospective.period_end.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_retrospective(db: Session, user_id: UUID, retro_id: UUID) -> Retrospective:
    retro = (
        db.query(Retrospective)
        .filter(Retrospective.id == retro_id, Retrospective.user_id == user_id)
        .first()
    )
    if not retro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="复盘不存在")
    return retro


def update_retrospective(db: Session, user_id: UUID, retro_id: UUID, data: RetroUpdate) -> Retrospective:
    retro = get_retrospective(db, user_id, retro_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(retro, key, value)
    db.commit()
    db.refresh(retro)
    return retro


def delete_retrospective(db: Session, user_id: UUID, retro_id: UUID) -> None:
    retro = get_retrospective(db, user_id, retro_id)
    db.delete(retro)
    db.commit()


def generate_draft(
    db: Session, user_id: UUID, period_start: date, period_end: date
) -> dict:
    events = (
        db.query(CareerEvent)
        .filter(
            CareerEvent.user_id == user_id,
            CareerEvent.event_date >= period_start,
            CareerEvent.event_date <= period_end,
        )
        .order_by(CareerEvent.event_date.desc())
        .all()
    )
    event_summaries = [
        {"id": str(e.id), "event_date": e.event_date.isoformat(), "event_type": e.event_type.value, "title": e.title}
        for e in events
    ]
    suggested_achievements = [e.title for e in events if e.event_type.value in ("promotion", "project_done", "certification")]
    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "event_summaries": event_summaries,
        "suggested_achievements": suggested_achievements,
    }
