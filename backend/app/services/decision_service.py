from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.destination_decision import DestinationDecision
from app.schemas.decision import DecisionCreate, DecisionUpdate


def create_decision(db: Session, user_id: UUID, data: DecisionCreate) -> DestinationDecision:
    decision = DestinationDecision(user_id=user_id, **data.model_dump())
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def list_decisions(db: Session, user_id: UUID) -> list[DestinationDecision]:
    return (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .all()
    )


def get_decision(db: Session, user_id: UUID, decision_id: UUID) -> DestinationDecision:
    decision = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.id == decision_id, DestinationDecision.user_id == user_id)
        .first()
    )
    if not decision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="决策记录不存在")
    return decision


def update_decision(db: Session, user_id: UUID, decision_id: UUID, data: DecisionUpdate) -> DestinationDecision:
    decision = get_decision(db, user_id, decision_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(decision, key, value)
    db.commit()
    db.refresh(decision)
    return decision


def delete_decision(db: Session, user_id: UUID, decision_id: UUID) -> None:
    decision = get_decision(db, user_id, decision_id)
    db.delete(decision)
    db.commit()


def get_decision_stats(db: Session, user_id: UUID) -> dict[str, int]:
    decisions = db.query(DestinationDecision).filter(DestinationDecision.user_id == user_id).all()
    stats: dict[str, int] = {}
    for d in decisions:
        key = d.destination_type.value
        stats[key] = stats.get(key, 0) + 1
    return stats
