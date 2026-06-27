from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.retrospective import RetroCreate, RetroResponse, RetroUpdate
from app.services.retrospective_service import (
    create_retrospective,
    delete_retrospective,
    generate_draft,
    get_retrospective,
    list_retrospectives,
    update_retrospective,
)

router = APIRouter(prefix="/api/retrospectives", tags=["阶段复盘"])


@router.post("", response_model=RetroResponse, status_code=status.HTTP_201_CREATED)
def create(data: RetroCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_retrospective(db, user.id, data)


@router.get("", response_model=list[RetroResponse])
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list_retrospectives(db, user.id)


@router.get("/draft")
def draft(
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return generate_draft(db, user.id, period_start, period_end)


@router.get("/{retro_id}", response_model=RetroResponse)
def get_one(retro_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_retrospective(db, user.id, retro_id)


@router.patch("/{retro_id}", response_model=RetroResponse)
def update(retro_id: UUID, data: RetroUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_retrospective(db, user.id, retro_id, data)


@router.delete("/{retro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(retro_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_retrospective(db, user.id, retro_id)
