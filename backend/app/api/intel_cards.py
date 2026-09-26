# backend/app/api/intel_cards.py
"""门道库公开 API（批次 B+，2026-09-26 五问拍板：库+chat 双出口之"库"）。

只读公开端点，无鉴权（门道卡=全站公共策展内容，带源可查证）。
消费出口：前端 /intel/cards 门道库页面 + chat 注入（data_search_service）。
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intel_card import (
    INTEL_STATUS_ACTIVE,
    IntelCard,
)

router = APIRouter(prefix="/api/intel/cards", tags=["门道卡"])


class IntelCardOut(BaseModel):
    id: str
    track: str
    category: str
    question_id: str
    question_text: str
    title: str
    conclusion: str
    conditions: str
    counterexample: str | None
    confidence: str
    sources: list
    evidence_data: dict | None
    as_of: str


class IntelCardListResponse(BaseModel):
    total: int
    items: list[IntelCardOut]
    covered_questions: int


class IntelQuestionGroup(BaseModel):
    question_id: str
    question_text: str
    category: str
    cards: list[IntelCardOut]


class IntelQuestionListResponse(BaseModel):
    total: int
    groups: list[IntelQuestionGroup]


def _to_out(card: IntelCard) -> IntelCardOut:
    return IntelCardOut(
        id=str(card.id),
        track=card.track,
        category=card.category,
        question_id=card.question_id,
        question_text=card.question_text,
        title=card.title,
        conclusion=card.conclusion,
        conditions=card.conditions,
        counterexample=card.counterexample,
        confidence=card.confidence,
        sources=card.sources or [],
        evidence_data=card.evidence_data,
        as_of=card.as_of,
    )


def _active_query(db: Session, track: str):
    return (
        db.query(IntelCard)
        .filter(IntelCard.track == track, IntelCard.status == INTEL_STATUS_ACTIVE)
    )


@router.get("", response_model=IntelCardListResponse)
def list_cards(
    track: str = Query("kaoyan", description="考试线（先行 kaoyan）"),
    category: str | None = Query(None, description="rule/circle/evidence"),
    q: str | None = Query(None, description="关键词（问题/标题/结论模糊匹配）"),
    db: Session = Depends(get_db),
):
    """门道卡列表（仅 active；孤证卡前端标'孤证'徽章）。"""
    query = _active_query(db, track)
    if category:
        query = query.filter(IntelCard.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                IntelCard.question_text.ilike(like),
                IntelCard.title.ilike(like),
                IntelCard.conclusion.ilike(like),
            )
        )
    cards = query.order_by(IntelCard.category, IntelCard.question_id).all()
    return IntelCardListResponse(
        total=len(cards),
        items=[_to_out(c) for c in cards],
        covered_questions=len({c.question_id for c in cards}),
    )


@router.get("/questions", response_model=IntelQuestionListResponse)
def list_by_question(
    track: str = Query("kaoyan", description="考试线（先行 kaoyan）"),
    db: Session = Depends(get_db),
):
    """按问题清单分组返回（门道库页面按问题组织的消费形态）。"""
    cards = (
        _active_query(db, track)
        .order_by(IntelCard.category, IntelCard.question_id)
        .all()
    )
    groups: dict[tuple, list[IntelCardOut]] = {}
    for c in cards:
        groups.setdefault((c.category, c.question_id, c.question_text), []).append(
            _to_out(c)
        )
    return IntelQuestionListResponse(
        total=len(cards),
        groups=[
            IntelQuestionGroup(
                question_id=qid,
                question_text=qtext,
                category=cat,
                cards=items,
            )
            for (cat, qid, qtext), items in sorted(groups.items())
        ],
    )
