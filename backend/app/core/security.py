from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from jose import jwt
from jose.exceptions import JWTError

from app.config import settings

# 密码重置令牌有效期（分钟）
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30

# 修复: FASTAPI-AUTH-003 — 显式拒绝 ALGORITHM="none"，
# 防御层：即使配置错误也不会签发无签名 token。
_ALLOWED_ALGORITHMS = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512",
                       "ES256", "ES384", "ES512", "EdDSA"}
if settings.ALGORITHM not in _ALLOWED_ALGORITHMS:
    raise RuntimeError(
        f"ALGORITHM={settings.ALGORITHM!r} 不在允许列表 (FASTAPI-AUTH-003)。"
        f"允许: {sorted(_ALLOWED_ALGORITHMS)}"
    )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def verify_refresh_token(token: str) -> UUID | None:
    """验证 refresh_token，返回 user_id 或 None。

    refresh_token 在签发时携带 ``type=refresh`` 声明，此处校验该声明并解析
    用户 ID；任何解码失败、类型不符或格式异常都返回 None。
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        user_id = UUID(payload.get("sub"))
        return user_id
    except (JWTError, ValueError):
        return None


def create_password_reset_token(subject: str) -> str:
    """生成密码重置令牌（30 分钟有效）。"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire, "type": "password_reset"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str) -> UUID | None:
    """验证密码重置令牌，返回 user_id 或 None。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return UUID(payload.get("sub"))
    except (JWTError, ValueError):
        return None
