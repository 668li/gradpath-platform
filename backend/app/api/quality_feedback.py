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
from app.models.quality_feedback import (
    QualityFeedback,
    QualityFeedbackTargetType,
)
from app.models.user import User
from app.schemas.quality_feedback import (
    QualityFeedbackCreate,
    QualityFeedbackResponse,
)

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
    return feedback
