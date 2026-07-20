"""通知清理与归档服务 (C4)。

提供以下能力：
- archive_old_read_notifications: 自动归档已读且超过指定天数的通知
- archive_notification: 手动归档单条通知
- archive_user_notifications: 批量归档用户通知
- unarchive_notification: 恢复归档通知
- delete_old_archived: 物理删除已归档超过指定天数的通知
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.models.notification import Notification

logger = logging.getLogger(__name__)


def archive_notification(db: Session, user_id: UUID, notification_id: UUID) -> Notification:
    """归档单条通知。

    已归档的通知不会出现在主列表（默认 ?archived=false），
    但用户可在归档区查看与恢复。
    """
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not n:
        raise NotFoundError("通知不存在")
    if n.archived:
        # 幂等：已归档通知重复归档不报错
        return n
    n.archived = True
    n.archived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(n)
    logger.info("通知已归档: user_id=%s notification_id=%s", user_id, notification_id)
    return n


def unarchive_notification(db: Session, user_id: UUID, notification_id: UUID) -> Notification:
    """恢复归档通知到主列表。"""
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not n:
        raise NotFoundError("通知不存在")
    if not n.archived:
        return n
    n.archived = False
    n.archived_at = None
    db.commit()
    db.refresh(n)
    logger.info("通知已恢复: user_id=%s notification_id=%s", user_id, notification_id)
    return n


def archive_user_notifications(
    db: Session,
    user_id: UUID,
    notification_ids: Optional[list[UUID]] = None,
    only_read: bool = False,
) -> int:
    """批量归档用户通知。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        notification_ids: 指定通知 ID 列表；为 None 时归档用户全部已读通知
        only_read: 当 notification_ids=None 时，是否仅归档已读通知（默认全部）

    Returns:
        归档数量
    """
    q = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.archived == False,  # noqa: E712 — SQLAlchemy 比较需 ==
    )
    if notification_ids is not None:
        if not notification_ids:
            return 0
        q = q.filter(Notification.id.in_(notification_ids))
    elif only_read:
        q = q.filter(Notification.read == True)  # noqa: E712

    now = datetime.now(timezone.utc)
    count = q.update({"archived": True, "archived_at": now}, synchronize_session="fetch")
    db.commit()
    logger.info(
        "批量归档通知: user_id=%s count=%d only_read=%s",
        user_id,
        count,
        only_read,
    )
    return count


def archive_old_read_notifications(
    db: Session, user_id: Optional[UUID] = None, days_old: int = 30
) -> int:
    """自动归档已读且超过指定天数的通知。

    适用于定时任务（cron / Celery beat）每天执行：
    - days_old=30: 已读超过 30 天的通知自动归档
    - user_id=None: 处理所有用户

    Args:
        db: 数据库会话
        user_id: 指定用户 ID；None 表示全部用户
        days_old: 已读天数阈值

    Returns:
        归档数量
    """
    threshold = datetime.now(timezone.utc) - timedelta(days=days_old)
    q = db.query(Notification).filter(
        Notification.archived == False,  # noqa: E712
        Notification.read == True,  # noqa: E712
        Notification.updated_at < threshold,
    )
    if user_id is not None:
        q = q.filter(Notification.user_id == user_id)

    count = q.update(
        {"archived": True, "archived_at": datetime.now(timezone.utc)},
        synchronize_session="fetch",
    )
    db.commit()
    logger.info("自动归档旧通知: days_old=%s count=%d", days_old, count)
    return count


def delete_old_archived(db: Session, days_archived: int = 90) -> int:
    """物理删除已归档超过指定天数的通知。

    适用于定时任务，默认保留 90 天归档后删除。
    """
    threshold = datetime.now(timezone.utc) - timedelta(days=days_archived)
    q = db.query(Notification).filter(
        Notification.archived == True,  # noqa: E712
        Notification.archived_at < threshold,
    )
    count = q.count()
    if count == 0:
        return 0
    q.delete(synchronize_session="fetch")
    db.commit()
    logger.info("物理删除归档通知: days_archived=%s count=%d", days_archived, count)
    return count


def validate_archive_batch_limit(notification_ids: list[UUID]) -> None:
    """限制单次批量归档数量，防止误操作 / DoS。"""
    if len(notification_ids) > 200:
        raise BusinessError(
            "ARCHIVE_BATCH_TOO_LARGE",
            "单次批量归档不能超过 200 条",
            400,
            details={"limit": 200, "got": len(notification_ids)},
        )
