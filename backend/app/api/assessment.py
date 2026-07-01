# backend/app/api/assessment.py
"""职业测评 API 路由 — 霍兰德职业兴趣测评。

- GET /api/assessment/questions — 获取题目列表（无需认证）
- POST /api/assessment/submit — 提交答案，计算结果并保存
- GET /api/assessment/result — 获取最近一次测评结果
- GET /api/assessment/history — 获取历史记录
"""
from collections import Counter

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.assessment import Assessment
from app.models.user import User
from app.schemas.assessment import (
    AssessmentResponse,
    AssessmentSubmit,
    Question,
)
from app.services.assessment_service import (
    HOLLAND_QUESTIONS,
    calculate_holland_result,
)

router = APIRouter(prefix="/api/assessment", tags=["职业测评"])


def _to_response(assessment: Assessment) -> AssessmentResponse:
    """将 Assessment ORM 对象组装为响应（scores 由 answers 实时计算）。"""
    return AssessmentResponse(
        id=assessment.id,
        assessment_type=assessment.assessment_type,
        result_code=assessment.result_code,
        result_summary=assessment.result_summary,
        recommended_directions=assessment.recommended_directions or [],
        scores=dict(Counter(assessment.answers.values())),
        created_at=assessment.created_at,
    )


@router.get("/questions", response_model=list[Question])
def get_questions():
    """获取霍兰德测评题目列表（无需认证）。"""
    return HOLLAND_QUESTIONS


@router.post(
    "/submit",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_assessment(
    body: AssessmentSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交答案，计算结果并保存到数据库。"""
    result = calculate_holland_result(body.answers)
    assessment = Assessment(
        user_id=user.id,
        assessment_type="holland",
        answers=body.answers,
        result_code=result["result_code"],
        result_summary=result["result_summary"],
        recommended_directions=result["recommended_directions"],
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return _to_response(assessment)


@router.get("/result", response_model=AssessmentResponse | None)
def get_latest_result(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取最近一次测评结果，不存在则返回 null。"""
    assessment = (
        db.query(Assessment)
        .filter(Assessment.user_id == user.id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not assessment:
        return None
    return _to_response(assessment)


@router.get("/history", response_model=list[AssessmentResponse])
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取历史测评记录（按创建时间倒序）。"""
    assessments = (
        db.query(Assessment)
        .filter(Assessment.user_id == user.id)
        .order_by(Assessment.created_at.desc())
        .all()
    )
    return [_to_response(a) for a in assessments]
