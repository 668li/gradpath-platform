"""AI 主动洞察 API — 跨数据模式识别，主动生成洞察。"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.proactive_insight import ProactiveInsightResponse, ProactiveInsightSummary
from app.services import proactive_insight_service

router = APIRouter(prefix="/api/proactive-insights", tags=["AI主动洞察"])


@router.get("/summary", response_model=ProactiveInsightSummary)
def get_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取洞察摘要（未读数 + 最新洞察）。"""
    summary = proactive_insight_service.get_summary(db, user.id)
    return ProactiveInsightSummary(
        unread_count=summary["unread_count"],
        total_count=summary["total_count"],
        latest_insights=[
            ProactiveInsightResponse.model_validate(i) for i in summary["latest_insights"]
        ],
    )


@router.get("/list", response_model=list[ProactiveInsightResponse])
def list_insights(
    unread_only: bool = False,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出用户的主动洞察。"""
    insights = proactive_insight_service.list_insights(db, user.id, limit=limit, unread_only=unread_only)
    return [ProactiveInsightResponse.model_validate(i) for i in insights]


@router.post("/generate", response_model=list[ProactiveInsightResponse], status_code=status.HTTP_201_CREATED)
def generate_insights(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """主动分析用户数据模式，生成洞察。"""
    insights = proactive_insight_service.generate_insights(db, user.id)
    return [ProactiveInsightResponse.model_validate(i) for i in insights]


@router.patch("/{insight_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_as_read(
    insight_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记洞察为已读。"""
    proactive_insight_service.mark_as_read(db, user.id, insight_id)
