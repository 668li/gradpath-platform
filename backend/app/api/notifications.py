"""通知 API 路由。"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.exceptions import BusinessError, NotFoundError
from app.core.websocket_manager import manager as ws_manager
from app.database import get_db
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.schemas.notification import (
    NotificationArchiveResponse,
    NotificationCountResponse,
    NotificationListResponse,
    NotificationResponse,
)
from app.services.notification_cleanup_service import (
    archive_notification,
    archive_user_notifications,
    unarchive_notification,
    validate_archive_batch_limit,
)

router = APIRouter(prefix="/api/notifications", tags=["通知"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = False,
    archived: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出通知。

    Args:
        unread_only: 仅返回未读通知（仍受 archived 过滤影响）
        archived: 是否查询归档区（默认 false，仅返回未归档通知）
    """
    q = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.archived == archived,  # noqa: E712
    )
    if unread_only:
        q = q.filter(Notification.read == False)  # noqa: E712

    total = q.count()
    # unread_count 始终统计未归档通知中的未读数（归档通知不参与未读计数）
    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.read == False,  # noqa: E712
            Notification.archived == False,  # noqa: E712
        )
        .count()
    )
    items = (
        q.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return NotificationListResponse(
        items=items, total=total, unread_count=unread_count
    )


@router.get("/unread-count", response_model=NotificationCountResponse)
def get_unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取未读通知数（仅统计未归档通知）。"""
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.read == False,  # noqa: E712
            Notification.archived == False,  # noqa: E712
        )
        .count()
    )
    return NotificationCountResponse(unread_count=count)


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )
    if not n:
        raise NotFoundError("通知不存在")
    n.read = True
    db.commit()
    db.refresh(n)
    return n


@router.post("/read-all", status_code=status.HTTP_200_OK)
def mark_all_as_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """全部标记为已读（仅影响未归档通知）。"""
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read == False,  # noqa: E712
        Notification.archived == False,  # noqa: E712
    ).update({"read": True})
    db.commit()
    return {"message": "已全部标记为已读"}


# ===== C8 批量操作 API =====

class NotificationBatchDeleteRequest(BaseModel):
    """批量删除通知请求体。"""
    ids: list[str] = Field(
        ...,
        description="要删除的通知 ID 列表（最多 100 个）",
        max_length=100,
    )


@router.delete("/batch", status_code=status.HTTP_200_OK)
def batch_delete_notifications(
    body: NotificationBatchDeleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量删除通知（仅删除当前用户的通知，最多 100 个）。"""
    raw_ids = body.ids[:100]
    parsed_ids: list[UUID] = []
    for raw in raw_ids:
        try:
            parsed_ids.append(UUID(raw))
        except (ValueError, AttributeError):
            continue
    if not parsed_ids:
        return {"deleted": 0}
    deleted = (
        db.query(Notification)
        .filter(
            Notification.id.in_(parsed_ids),
            Notification.user_id == user.id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted": deleted}


# ===== C4 通知归档 API =====

class ArchiveBatchRequest(BaseModel):
    """批量归档请求体。"""
    notification_ids: Optional[list[str]] = Field(
        None,
        # 注意: max_length=500 是 schema 层 DoS 防护上限（高于业务上限 200）。
        # 业务上限 200 由 validate_archive_batch_limit 检查并返回 400 +
        # ARCHIVE_BATCH_TOO_LARGE，便于前端按业务错误码处理；超过 500 的
        # 异常请求直接被 Pydantic 拦截为 422，防止内存/解析 DoS。
        description="要归档的通知 ID 列表（业务上限 200 个，schema 上限 500 个）；为空时归档全部已读通知",
        max_length=500,
    )
    only_read: bool = Field(
        True,
        description="当 notification_ids 为空时，是否仅归档已读通知",
    )


@router.post("/{notification_id}/archive", response_model=NotificationResponse)
def archive_single(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """归档单条通知。"""
    return archive_notification(db, user.id, notification_id)


@router.post("/{notification_id}/unarchive", response_model=NotificationResponse)
def unarchive_single(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """恢复归档的通知到主列表。"""
    return unarchive_notification(db, user.id, notification_id)


@router.post("/archive", response_model=NotificationArchiveResponse)
def archive_batch(
    body: ArchiveBatchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量归档通知。

    - 传 notification_ids: 归档指定通知（最多 200 个）
    - 不传 notification_ids + only_read=true: 归档用户全部已读通知
    - 不传 notification_ids + only_read=false: 归档用户全部通知
    """
    ids: Optional[list[UUID]] = None
    if body.notification_ids is not None:
        ids = []
        for raw in body.notification_ids:
            try:
                ids.append(UUID(raw))
            except (ValueError, AttributeError):
                # 跳过无效 ID
                continue
        validate_archive_batch_limit(ids)

    count = archive_user_notifications(
        db,
        user.id,
        notification_ids=ids,
        only_read=body.only_read,
    )
    return NotificationArchiveResponse(
        message="归档完成",
        archived_count=count,
    )


@router.post("/archive-old", response_model=NotificationArchiveResponse)
def archive_old(
    days_old: int = Query(30, ge=1, le=365, description="已读通知归档阈值（天）"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """自动归档当前用户已读且超过 days_old 天的通知。

    通常由前端在用户访问通知页时调用，或由定时任务触发。
    """
    from app.services.notification_cleanup_service import (
        archive_old_read_notifications,
    )
    count = archive_old_read_notifications(db, user_id=user.id, days_old=days_old)
    return NotificationArchiveResponse(
        message="自动归档完成",
        archived_count=count,
    )


# 内部工具函数 — 供其他模块创建通知后通过 WebSocket 推送
def create_notification(
    db: Session,
    user_id: uuid.UUID,
    type: str = "system",
    title: str = "",
    content: str = "",
) -> Notification:
    """创建通知并返回实例（不自动 commit）。"""
    n = Notification(
        user_id=user_id,
        type=NotificationType(type),
        title=title,
        content=content,
    )
    db.add(n)
    db.flush()
    return n


async def push_notification(
    db: Session,
    user_id: uuid.UUID,
    type: str = "system",
    title: str = "",
    content: str = "",
) -> Notification:
    """创建通知并实时推送给用户（自动 commit）。"""
    n = create_notification(db, user_id, type, title, content)
    db.commit()
    db.refresh(n)
    # 实时推送到 WebSocket
    await ws_manager.send_personal(str(user_id), {
        "type": "new_notification",
        "notification": {
            "id": str(n.id),
            "type": n.type.value if hasattr(n.type, "value") else str(n.type),
            "title": n.title,
            "content": n.content,
            "read": n.read,
            "archived": n.archived,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        },
    })
    return n
