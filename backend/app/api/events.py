from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.career_event import EventType
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.services.event_service import (
    create_event,
    delete_event,
    get_event,
    list_events_paginated,
    update_event,
)

router = APIRouter(prefix="/api/events", tags=["职业事件"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create(data: EventCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_event(db, user.id, data)


@router.get("", response_model=PaginatedResponse[EventResponse])
def list_all(
    event_type: EventType | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items, total = list_events_paginated(
        db, user.id, page, page_size, event_type, start_date, end_date
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{event_id}", response_model=EventResponse)
def get_one(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_event(db, user.id, event_id)


@router.patch("/{event_id}", response_model=EventResponse)
def update(event_id: UUID, data: EventUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_event(db, user.id, event_id, data)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_event(db, user.id, event_id)
