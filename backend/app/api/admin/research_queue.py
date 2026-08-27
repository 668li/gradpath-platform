"""管理员审核队列 API — 统一走 t_review_queue_item（P1 修理）。

审核链路唯一入口：
- GET  /api/admin/research-queue/pending      待审核列表（JOIN 外部调研条目）
- POST /api/admin/research-queue/{id}/approve  通过 → 落业务表（research_promote）
- POST /api/admin/research-queue/{id}/reject   驳回（填原因）
- POST /api/admin/research-queue/{id}/duplicate 标记重复

旧 /api/admin/research 的 pending/approve/reject 端点保留不动
（社区 UGC 审核语义，向前兼容）。
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.database import get_db
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.models.user import User
from app.schemas.research_queue import (
    QueueActionResponse,
    QueueApproveRequest,
    QueueDuplicateRequest,
    QueueRejectRequest,
    ResearchQueueItemVO,
    ResearchQueueListResponse,
)
from app.services.research_promote import promote_external_item

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/research-queue", tags=["管理员-审核队列"])


def _get_pending_queue_item(db: Session, queue_id: int) -> ReviewQueueItem:
    """取队列条目并校验处于待审核状态（重复审核返回 409）。"""
    queue_item = db.query(ReviewQueueItem).filter(ReviewQueueItem.id == queue_id).first()
    if not queue_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="队列条目不存在",
        )
    if queue_item.review_status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"该条目已审核（当前状态: {queue_item.review_status}），不可重复审核",
        )
    return queue_item


def _get_external_item(db: Session, queue_item: ReviewQueueItem) -> ExternalResearchItem | None:
    """取队列引用的 t_external_research_item。"""
    return (
        db.query(ExternalResearchItem)
        .filter(ExternalResearchItem.id == queue_item.ref_item_id)
        .first()
    )


def _apply_review(
    db: Session,
    queue_item: ReviewQueueItem,
    ext_item: ExternalResearchItem | None,
    new_status: str,
    admin: User,
    reject_reason: str | None = None,
) -> None:
    """统一回填：队列条目 + 外部调研条目 状态同步（不 commit，由调用方提交）。"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # 与 audit 列 naive 风格一致
    queue_item.review_status = new_status
    queue_item.reviewed_by = admin.email
    queue_item.reviewed_time = now
    if reject_reason is not None:
        queue_item.reject_reason = reject_reason
    if ext_item is not None:
        ext_item.review_status = new_status


@router.get("/pending", response_model=ResearchQueueListResponse)
def list_pending_queue(
    item_type: str | None = Query(None, description="条目类型: external_research"),
    source_platform: str | None = Query(None, description="来源平台: bilibili / web / rss"),
    review_status: str | None = Query("PENDING", description="审核状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """待审核列表 — JOIN t_external_research_item 带出标题/内容/URL/可信度。"""
    query = db.query(ReviewQueueItem, ExternalResearchItem).join(
        ExternalResearchItem,
        ExternalResearchItem.id == ReviewQueueItem.ref_item_id,
    )
    if item_type:
        query = query.filter(ReviewQueueItem.item_type == item_type)
    if source_platform:
        query = query.filter(ExternalResearchItem.source_platform == source_platform)
    if review_status:
        query = query.filter(ReviewQueueItem.review_status == review_status)

    total = query.count()
    rows = (
        query.order_by(ReviewQueueItem.created_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        ResearchQueueItemVO(
            queue_id=q.id,
            item_type=q.item_type,
            ref_item_id=q.ref_item_id,
            biz_req_no=q.biz_req_no,
            source_url=q.source_url,
            review_status=q.review_status,
            reject_reason=q.reject_reason,
            reviewed_by=q.reviewed_by,
            reviewed_time=q.reviewed_time,
            created_time=q.created_time,
            title=e.title,
            content=e.content,
            crawler_name=e.crawler_name,
            source_platform=e.source_platform,
            credibility=e.credibility,
            external_meta=e.external_meta,
        )
        for q, e in rows
    ]
    return ResearchQueueListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/{queue_id}/approve", response_model=QueueActionResponse)
def approve_queue_item(
    queue_id: int,
    body: QueueApproveRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """审核通过 → 调 promote 服务落业务表（ExperiencePost/KaoyanNews），幂等去重。"""
    queue_item = _get_pending_queue_item(db, queue_id)
    ext_item = _get_external_item(db, queue_item)
    if not ext_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="队列引用的外部调研条目不存在，无法通过审核",
        )

    try:
        result = promote_external_item(db, ext_item, admin.email)
        _apply_review(db, queue_item, ext_item, "APPROVED", admin)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("[research_queue] approve 失败 queue_id=%s", queue_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="审核通过失败，请查看服务器日志",
        )

    logger.info(
        "[research_queue] admin=%s approve queue_id=%s ref=%s item_type=%s promoted=%d",
        admin.id,
        queue_id,
        ext_item.id,
        ext_item.item_type,
        result["promoted"],
    )
    return QueueActionResponse(
        message="审核通过，已落业务数据",
        queue_id=queue_id,
        review_status="APPROVED",
        ref_item_id=ext_item.id,
        promoted=result["promoted"],
    )


@router.post("/{queue_id}/reject", response_model=QueueActionResponse)
def reject_queue_item(
    queue_id: int,
    body: QueueRejectRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """驳回：填原因，回填队列 + 外部调研条目为 REJECTED。"""
    queue_item = _get_pending_queue_item(db, queue_id)
    ext_item = _get_external_item(db, queue_item)

    try:
        _apply_review(
            db,
            queue_item,
            ext_item,
            "REJECTED",
            admin,
            reject_reason=body.reject_reason,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("[research_queue] reject 失败 queue_id=%s", queue_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="驳回失败，请查看服务器日志",
        )

    logger.info(
        "[research_queue] admin=%s reject queue_id=%s reason=%s",
        admin.id,
        queue_id,
        body.reject_reason,
    )
    return QueueActionResponse(
        message="已驳回",
        queue_id=queue_id,
        review_status="REJECTED",
        ref_item_id=queue_item.ref_item_id,
    )


@router.post("/{queue_id}/duplicate", response_model=QueueActionResponse)
def duplicate_queue_item(
    queue_id: int,
    body: QueueDuplicateRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """标记重复：回填队列 + 外部调研条目为 DUPLICATED。"""
    queue_item = _get_pending_queue_item(db, queue_id)
    ext_item = _get_external_item(db, queue_item)

    try:
        _apply_review(db, queue_item, ext_item, "DUPLICATED", admin)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("[research_queue] duplicate 失败 queue_id=%s", queue_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="标记重复失败，请查看服务器日志",
        )

    logger.info(
        "[research_queue] admin=%s duplicate queue_id=%s duplicate_of=%s",
        admin.id,
        queue_id,
        body.duplicate_of,
    )
    return QueueActionResponse(
        message="已标记为重复",
        queue_id=queue_id,
        review_status="DUPLICATED",
        ref_item_id=queue_item.ref_item_id,
    )
