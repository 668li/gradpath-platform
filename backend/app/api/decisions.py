from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.decision import DecisionCreate, DecisionResponse, DecisionUpdate
from app.services.decision_service import (
    create_decision,
    delete_decision,
    get_decision,
    get_decision_stats,
    list_decisions,
    update_decision,
)

router = APIRouter(prefix="/api/decisions", tags=["去向决策"])


@router.post("", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
def create(data: DecisionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_decision(db, user.id, data)


@router.get("", response_model=list[DecisionResponse])
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list_decisions(db, user.id)


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_decision_stats(db, user.id)


@router.get("/{decision_id}", response_model=DecisionResponse)
def get_one(decision_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_decision(db, user.id, decision_id)


@router.patch("/{decision_id}", response_model=DecisionResponse)
def update(decision_id: UUID, data: DecisionUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_decision(db, user.id, decision_id, data)


@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(decision_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_decision(db, user.id, decision_id)
