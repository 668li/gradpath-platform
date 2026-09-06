"""质量分反馈闭环 API（Phase I，P0 仅采集存储）。

用户对经验贴/资讯的质量分与证据链点「👍有帮助 / 👎不准确」（双键快捷反馈 +
选填原因）。P0 仅采集存储：同用户同条目 upsert 只留最新一条（可切换），
管理端统计/处理留 P1。目标条目不存在返回 404，未登录返回 401，超限流 429。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import rate_limits
from app.database import get_db
from app.main import limiter
from app.models.experience_post import ExperiencePost
from app.models.kaoyan_news import KaoyanNews
from app.models.quality_feedback import QualityFeedback, QualityFeedbackTargetType
from app.models.user import User
from app.schemas.quality_feedback import QualityFeedbackCreate, QualityFeedbackResponse

router = APIRouter(prefix="/api/kaoyan", tags=["质量反馈"])

# 反馈目标 → 业务表（存在性校验；target_id 为该表主键）
_TARGET_MODELS = {
    QualityFeedbackTargetType.experience_post: ExperiencePost,
    QualityFeedbackTargetType.kaoyan_news: KaoyanNews,
}


def _parse_target_id(target_id: str) -> str:
    """目标条目主键规范化（hex / 带连字符均可）→ hex；非法格式返回空串。"""
    try:
        return uuid.UUID(str(target_id)).hex
    except (ValueError, AttributeError):
        return ""


@router.post(
    "/quality-feedback",
    response_model=QualityFeedbackResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(rate_limits.QUALITY_FEEDBACK_CREATE)
def submit_quality_feedback(
    request: Request,
    response: Response,
    data: QualityFeedbackCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交质量反馈（需登录，5 次/分钟限流）。

    upsert：同用户对同条目已有反馈 → 替换为最新（feedback_type/reason 可切换，
    如 👎 → 👍 会覆盖旧反馈）。P0 仅采集存储，不做业务侧处理。
    """
    target_hex = _parse_target_id(data.target_id)
    model = _TARGET_MODELS[data.target_type]
    exists = db.query(model.id).filter(model.id == target_hex).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目标条目不存在")

    feedback = (
        db.query(QualityFeedback)
        .filter(
            QualityFeedback.user_id == user.id,
            QualityFeedback.target_type == data.target_type,
            QualityFeedback.target_id == target_hex,
        )
        .first()
    )
    if feedback is None:
        feedback = QualityFeedback(
            user_id=user.id,
            target_type=data.target_type,
            target_id=target_hex,
        )
        db.add(feedback)
    feedback.feedback_type = data.feedback_type
    feedback.reason = data.reason
    db.commit()
    db.refresh(feedback)

    # 仅 👎（不准确）即时触达管理员——👍 属高频正向信号，推送即噪音
    if feedback.feedback_type == "unhelpful":
        notify_async(
            "👎 内容质量反馈",
            f"类型: {data.target_type.value}\n原因: {data.reason or '（未填）'}",
        )
    return feedback


# ----------------------------------------------------------------------
# 管理端（2026-09-06 反馈通道补全，原 P1 欠账）：质量反馈统计
# ----------------------------------------------------------------------
from collections import Counter  # noqa: E402

from pydantic import BaseModel  # noqa: E402

from app.core.deps import get_admin_user  # noqa: E402
from app.core.push_notify import notify_async  # noqa: E402


class QualityFeedbackStats(BaseModel):
    total: int
    helpful: int
    unhelpful: int
    by_target_type: dict[str, int]


@router.get(
    "/quality-feedback/admin/stats",
    response_model=QualityFeedbackStats,
)
def admin_quality_feedback_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """管理端：质量反馈统计（👍/👎 总量与目标类型分布）。"""
    rows = db.query(QualityFeedback).all()
    by_type = Counter(
        r.target_type.value if hasattr(r.target_type, "value") else str(r.target_type)
        for r in rows
    )
    helpful = sum(1 for r in rows if r.feedback_type == "helpful")
    return QualityFeedbackStats(
        total=len(rows),
        helpful=helpful,
        unhelpful=len(rows) - helpful,
        by_target_type=dict(by_type),
    )
