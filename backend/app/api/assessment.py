# backend/app/api/assessment.py
"""职业测评 API 路由 — 支持 4 种测评体系。

- GET /api/assessment/questions — 获取题目列表（可选 type 参数，默认 holland，无需认证）
- POST /api/assessment/submit — 提交答案，计算结果并保存
- GET /api/assessment/result — 获取最近一次测评结果
- GET /api/assessment/history — 获取历史记录

支持的测评类型：holland | mbti | big_five | disc
"""
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cache import cache
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
    ASSESSMENT_CALCULATORS,
    ASSESSMENT_QUESTIONS,
)

router = APIRouter(prefix="/api/assessment", tags=["职业测评"])

# 合法测评类型集合
_VALID_TYPES = set(ASSESSMENT_QUESTIONS.keys())


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
def get_questions(type: str = Query("holland", description="测评类型：holland|mbti|big_five|disc")):
    """获取指定类型的测评题目列表（无需认证）。

    不传 type 时默认返回霍兰德题目，保持向后兼容。
    """
    questions = ASSESSMENT_QUESTIONS.get(type)
    if questions is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的测评类型: {type}，可选值: {sorted(_VALID_TYPES)}",
        )
    return questions


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
    """提交答案，计算结果并保存到数据库。

    根据 body.assessment_type 调用对应的计算函数。
    """
    assessment_type = body.assessment_type
    calculator = ASSESSMENT_CALCULATORS.get(assessment_type)
    if calculator is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的测评类型: {assessment_type}，可选值: {sorted(_VALID_TYPES)}",
        )

    result = calculator(body.answers)
    assessment = Assessment(
        user_id=user.id,
        assessment_type=assessment_type,
        answers=body.answers,
        result_code=result["result_code"],
        result_summary=result["result_summary"],
        recommended_directions=result["recommended_directions"],
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    # 失效用户上下文缓存（build_user_context 依赖最新 Assessment）
    try:
        cache.delete(f"user_context:{user.id}")
    except Exception:
        pass
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
