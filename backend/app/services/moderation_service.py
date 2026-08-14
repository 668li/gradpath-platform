"""社区治理核心逻辑：封禁/解封（联动用户缓存失效）。

封禁即时生效的关键：`get_current_user` 会缓存 user:{uuid}（TTL 60s），
若不主动删缓存，被封禁用户最长 60 秒内仍可继续通过受保护接口。
所有封禁/解封操作必须经本模块，统一在变更后删除缓存。
"""
import logging
from datetime import datetime, timezone

from app.core.deps import invalidate_user_cache
from app.models.user import User, UserStatus

logger = logging.getLogger("gradpath.moderation")


def ban_user(db, user: User, reason: str) -> None:
    """封禁用户：置 banned + 记录时间/原因 + 立即失效缓存。"""
    if user.is_admin:
        # 不允许封禁管理员（保护性护栏，避免自锁/越权）
        from fastapi import HTTPException
        raise HTTPException(403, "不能封禁管理员账户")
    user.status = UserStatus.banned
    user.banned_at = datetime.now(timezone.utc)
    user.ban_reason = reason
    db.add(user)
    db.flush()
    invalidate_user_cache(user.id)
    logger.info("用户封禁: user_id=%s reason=%s", user.id, reason)


def unban_user(db, user: User) -> None:
    """解封用户：恢复 active + 清空封禁记录 + 立即失效缓存。"""
    user.status = UserStatus.active
    user.banned_at = None
    user.ban_reason = None
    db.add(user)
    db.flush()
    invalidate_user_cache(user.id)
    logger.info("用户解封: user_id=%s", user.id)
