from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.destination_decision import DestinationDecision
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.decision import DecisionCreate, DecisionResponse, DecisionUpdate
from app.services.decision_service import (
    create_decision,
    delete_decision,
    get_decision,
    get_decision_stats,
    list_decisions_paginated,
    update_decision,
)

router = APIRouter(prefix="/api/decisions", tags=["去向决策"])


class DecisionBatchRequest(BaseModel):
    """批量获取决策请求体。"""

    ids: list[str] = Field(
        ..., min_length=1, max_length=100, description="决策 ID 列表（最多 100 个）"
    )


@router.post("", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
def create(data: DecisionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_decision(db, user.id, data)


@router.get("", response_model=PaginatedResponse[DecisionResponse])
def list_all(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items, total = list_decisions_paginated(db, user.id, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_decision_stats(db, user.id)


@router.post("/batch", response_model=list[DecisionResponse])
def batch_decisions(
    body: DecisionBatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量获取决策（消除前端 N+1 调用，仅返回当前用户的决策）。

    前端在决策对比/详情页一次展示 N 个决策时，原需发 N 次
    `/decisions/{id}` 请求；本接口一次返回所有决策信息。
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
    # 安全约束：仅返回当前用户的决策，防止越权
    items = (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.id.in_(parsed_ids),
            DestinationDecision.user_id == user.id,
        )
        .all()
    )
    return [DecisionResponse.model_validate(d) for d in items]


@router.get("/{decision_id}", response_model=DecisionResponse)
def get_one(decision_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_decision(db, user.id, decision_id)


@router.patch("/{decision_id}", response_model=DecisionResponse)
def update(decision_id: UUID, data: DecisionUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_decision(db, user.id, decision_id, data)


@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(decision_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_decision(db, user.id, decision_id)
