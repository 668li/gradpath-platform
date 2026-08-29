"""内容/用户举报 API — 社区治理。

- POST   /api/reports                     提交举报（登录 + 防刷 5/min，不能举报自己）
- GET    /api/admin/reports               举报列表（状态/类型筛选，分页，最新在前）
- POST   /api/admin/reports/{id}/process  处理举报：
    * action=processed：举报成立 → 下架内容（post 置 hidden / 评论软删 /
      经验贴与问答置 rejected），可选联动封禁作者；target 为用户时即封禁该用户
    * action=rejected：举报不成立
  处理结果通过 push_notification（type=moderation）通知举报人，
  内容被下架时同步通知作者。
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.notifications import push_notification
from app.core.deps import get_admin_user, get_current_user
from app.core.rate_limit import rate_limits
from app.database import get_db
from app.main import limiter
from app.models.comment import Comment
from app.models.experience_post import ExperiencePost
from app.models.post import Post, PostStatus
from app.models.qa import QA
from app.models.qa_answer import QAAnswer
from app.models.report import Report, ReportStatus, ReportTargetType
from app.models.user import User
from app.schemas.report import (
    ReportCreateRequest,
    ReportListVO,
    ReportProcessRequest,
    ReportProcessResult,
    ReportVO,
)
from app.services.moderation_service import ban_user

router = APIRouter(prefix="/api", tags=["社区治理-举报"])

logger = logging.getLogger("gradpath.reports")

# target 类型 → 内容模型（作者字段统一为 user_id）
_TARGET_MODELS = {
    ReportTargetType.post: Post,
    ReportTargetType.experience_post: ExperiencePost,
    ReportTargetType.comment: Comment,
    ReportTargetType.qa: QA,
    ReportTargetType.qa_answer: QAAnswer,
    ReportTargetType.user: User,
}

# 内容类 target 下架时的状态处置（comment 用软删，其余置 status=rejected/hidden）
_HIDDEN_STATUS = "rejected"  # experience_post / qa / qa_answer 从公开展示移除


def _to_vo(r: Report) -> ReportVO:
    return ReportVO(
        id=r.id,
        reporter_id=r.reporter_id,
        target_type=r.target_type.value if hasattr(r.target_type, "value") else str(r.target_type),
        target_id=r.target_id,
        reason=r.reason,
        detail=r.detail,
        status=r.status.value if hasattr(r.status, "value") else str(r.status),
        processed_by=r.processed_by,
        processed_at=r.processed_at,
        processed_note=r.processed_note,
        created_at=r.created_at,
    )


def _resolve_target(db: Session, target_type: ReportTargetType, target_id: str):
    """按 target 类型解析被举报对象（不存在返回 None）。"""
    try:
        uid = uuid.UUID(target_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="target_id 格式错误")
    model = _TARGET_MODELS[target_type]
    return db.query(model).filter(model.id == uid).first()


def _notify_author(db: Session, author_id, report) -> None:
    """内容被下架时通知作者（异步端点内调用，失败不阻塞）。"""
    if author_id is None:
        return
    try:
        from app.api.notifications import push_notification as _push

        return _push(
            db,
            author_id,
            "moderation",
            "内容被下架",
            f"您发布的{_TARGET_LABELS.get(report.target_type, '内容')}因违反社区规范已被下架。",
        )
    except Exception:
        logger.debug("下架作者通知失败: author=%s", author_id, exc_info=True)


_TARGET_LABELS = {
    ReportTargetType.post: "讨论帖",
    ReportTargetType.experience_post: "经验贴",
    ReportTargetType.comment: "评论",
    ReportTargetType.qa: "提问",
    ReportTargetType.qa_answer: "回答",
}


def _apply_moderation(
    db: Session,
    report: Report,
    data: ReportProcessRequest,
) -> "uuid.UUID | None":
    """举报成立时的处置：下架内容（可选联动封禁作者）；target 为用户时直接封禁。

    返回内容类 target 的作者 id（供下架通知使用）；target 为用户或无作者时返回 None。
    """
    target = _resolve_target(db, report.target_type, report.target_id)

    if report.target_type == ReportTargetType.user:
        # 举报对象是用户：处理即封禁（需填写封禁原因）
        if target is None:
            return None
        if not data.ban_reason:
            raise HTTPException(status_code=400, detail="封禁用户需填写 ban_reason")
        ban_user(db, target, data.ban_reason)
        return None

    # 内容类：下架（目标已被删除则跳过下架，仍标记处理完成）
    if target is None:
        return None
    author_id = target.user_id
    if report.target_type == ReportTargetType.post:
        target.status = PostStatus.hidden
    elif report.target_type == ReportTargetType.comment:
        target.is_deleted = True
    else:  # experience_post / qa / qa_answer
        target.status = _HIDDEN_STATUS
    db.add(target)

    # 可选联动封禁作者
    if data.ban_author:
        if not data.ban_reason:
            raise HTTPException(status_code=400, detail="封禁作者需填写 ban_reason")
        author = db.query(User).filter(User.id == author_id).first()
        if author is not None:
            ban_user(db, author, data.ban_reason)
    return author_id


@router.post("/reports", response_model=ReportVO, status_code=status.HTTP_201_CREATED)
@limiter.limit(rate_limits.REPORT_CREATE)
def create_report(
    request: Request,
    response: Response,
    data: ReportCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交举报（防刷 5/min）。"""
    if data.target_type == ReportTargetType.user and data.target_id == str(current_user.id):
        raise HTTPException(status_code=400, detail="不能举报自己")
    if _resolve_target(db, data.target_type, data.target_id) is None:
        raise HTTPException(status_code=404, detail="举报目标不存在")

    report = Report(
        reporter_id=current_user.id,
        target_type=data.target_type,
        target_id=data.target_id,
        reason=data.reason,
        detail=data.detail,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info(
        "举报提交: reporter=%s target=%s:%s reason=%s",
        current_user.id,
        data.target_type.value,
        data.target_id,
        data.reason,
    )
    return _to_vo(report)


@router.get("/admin/reports", response_model=ReportListVO)
def list_reports(
    report_status: ReportStatus | None = Query(None, alias="status", description="按处理状态筛选"),
    target_type: ReportTargetType | None = Query(
        None, alias="target_type", description="按对象类型筛选"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = db.query(Report)
    if report_status is not None:
        q = q.filter(Report.status == report_status)
    if target_type is not None:
        q = q.filter(Report.target_type == target_type)
    total = q.count()
    rows = (
        q.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return ReportListVO(total=total, items=[_to_vo(r) for r in rows])


@router.post("/admin/reports/{report_id}/process", response_model=ReportProcessResult)
async def process_report(
    report_id: str,
    data: ReportProcessRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="举报 ID 格式错误")
    report = db.query(Report).filter(Report.id == rid).first()
    if report is None:
        raise HTTPException(status_code=404, detail="举报不存在")
    if report.status != ReportStatus.pending:
        raise HTTPException(status_code=409, detail="该举报已处理，不能重复操作")

    if data.action == "rejected":
        report.status = ReportStatus.rejected
        author_id = None
    else:
        # 先执行处置，成功后才标记处理完成；处置失败（如缺 ban_reason）时
        # 举报保持 pending，管理员可补充原因后重试，不会被误判为重复处理。
        author_id = _apply_moderation(db, report, data)
        report.status = ReportStatus.processed

    report.processed_by = admin.id
    report.processed_at = datetime.now(timezone.utc)
    report.processed_note = data.note
    db.commit()

    # 通知举报人（处理后统一推送，commit 后调用避免提前提交）
    if data.action == "rejected":
        await push_notification(
            db,
            report.reporter_id,
            "moderation",
            "举报处理结果",
            f"您举报的内容（{report.reason}）经审核不成立，暂未处理。",
        )
    else:
        await push_notification(
            db,
            report.reporter_id,
            "moderation",
            "举报处理结果",
            f"您举报的内容（{report.reason}）已核实并处理，感谢您的反馈。",
        )
        # 内容被下架时通知作者
        if author_id is not None and author_id != admin.id:
            await _notify_author(db, author_id, report)
    logger.info("举报处理: report=%s action=%s by=%s", report.id, data.action, admin.id)
    return ReportProcessResult(report_id=report.id, status=report.status.value, message="处理完成")
