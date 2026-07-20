import logging
import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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
            return _deserialize_user(cached)
    except Exception as e:
        logger.debug("user cache get failed: %s", e)

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise creds_error

    # 写缓存（失败不阻塞业务）
    try:
        cache.set(cache_key, _serialize_user(user), ttl=USER_CACHE_TTL)
    except Exception as e:
        logger.debug("user cache set failed: %s", e)

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
