import logging
import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User, UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
# 匿名友好版：不带 token 返回 None 而非 401，用于"登录后可看更多"的公开端点
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

logger = logging.getLogger(__name__)

# 缓存 TTL（秒）
USER_CACHE_TTL = 60


def _serialize_user(user: User) -> dict:
    """将 User 对象序列化为可 JSON 化的 dict。

    只缓存下游常用的字段，避免 SQLAlchemy 实例的 _sa_instance_state 等不可序列化字段。
    datetime 转为 ISO 字符串以便 JSON 序列化。
    """
    return {
        "id": str(user.id),
        "email": user.email,
        "password_hash": user.password_hash,
        "name": user.name,
        "nickname": user.nickname,
        "username": user.username,
        "current_stage": user.current_stage.value if user.current_stage else None,
        "school": user.school,
        "major": user.major,
        "graduation_year": user.graduation_year,
        "is_admin": bool(user.is_admin),
        "status": user.status.value if user.status else UserStatus.active.value,
        "banned_at": user.banned_at.isoformat() if user.banned_at else None,
        "ban_reason": user.ban_reason,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _deserialize_user(data: dict) -> User:
    """从 dict 重建 User 对象。

    注意：返回的 User 实例未附加到 SQLAlchemy session（detached），
    仅供读取属性使用。如需修改并持久化，调用方需重新查询 DB。
    """
    payload = dict(data)
    if "id" in payload and payload["id"] is not None:
        payload["id"] = uuid.UUID(payload["id"])
    # created_at / updated_at 由 ISO 字符串还原为 datetime
    for field in ("created_at", "updated_at"):
        val = payload.get(field)
        if isinstance(val, str):
            payload[field] = datetime.fromisoformat(val)
    # current_stage 是 str enum，直接传字符串即可
    return User(**payload)


def _ensure_active(user: User) -> None:
    """封禁校验：banned 用户拒绝所有受保护请求（403）。

    缓存命中与 DB 直查两条路径都调用，保证封禁即时生效
    （配合封禁时主动 invalidate_user_cache 清缓存）。
    """
    if user.status == UserStatus.banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁，请联系管理员",
        )


def invalidate_user_cache(user_id: uuid.UUID) -> None:
    """封禁/解封后立即失效用户缓存，保证状态即时生效。"""
    try:
        cache.delete(f"user:{user_id}")
    except Exception as e:
        logger.debug("user cache delete failed: %s", e)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    creds_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        # 安全修复：必须校验 token 类型为 access，
        # 防止 refresh_token / password_reset_token 被用作 access_token
        if payload.get("type") != "access":
            raise creds_error
        user_id = payload.get("sub")
        if user_id is None:
            raise creds_error
        user_uuid = uuid.UUID(user_id)
    except Exception:
        raise creds_error

    cache_key = f"user:{user_uuid}"
    # 尝试命中缓存（失败不阻塞业务）
    try:
        cached = cache.get(cache_key)
        if cached:
            cached_user = _deserialize_user(cached)
            _ensure_active(cached_user)
            return cached_user
    except Exception as e:
        logger.debug("user cache get failed: %s", e)

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise creds_error
    _ensure_active(user)

    # 写缓存（失败不阻塞业务）
    try:
        cache.set(cache_key, _serialize_user(user), ttl=USER_CACHE_TTL)
    except Exception as e:
        logger.debug("user cache set failed: %s", e)

    return user


def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """匿名请求返回 None；带有效 token 返回用户；无效/封禁 token 一律 None（不 401）。

    仅用于公开端点上"登录后可看更多"的场景（如审核状态过滤收归管理员）。
    需要强制鉴权的端点仍用 get_current_user，不要用本依赖替代。
    """
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        user_uuid = uuid.UUID(user_id)
    except Exception:
        return None

    # 复用用户缓存，未命中落库（与 get_current_user 同一套缓存键）
    try:
        cached = cache.get(f"user:{user_uuid}")
        if cached:
            cached_user = _deserialize_user(cached)
            if cached_user.status != UserStatus.banned:
                return cached_user
            return None
    except Exception as e:
        logger.debug("optional user cache get failed: %s", e)

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None or user.status == UserStatus.banned:
        return None
    return user


def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
