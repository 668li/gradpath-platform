import logging

from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_password_reset_token,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest

logger = logging.getLogger(__name__)


def _invalidate_user_cache(user_id) -> None:
    """用户信息变更后失效 user 与 user_context 缓存。"""
    try:
        cache.delete(f"user:{user_id}")
        cache.delete(f"user_context:{user_id}")
    except Exception:
        pass


def register(db: Session, data: RegisterRequest) -> User:
    # B3 合规：用户必须明确同意条款才允许注册
    if not data.agree_terms:
        raise ConflictError(
            "注册需同意《隐私政策》和《用户协议》",
            details={"field": "agree_terms"},
        )
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise ConflictError("该邮箱已注册", details={"field": "email"})
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("新用户注册: email=%s", data.email)
    return user


def login(db: Session, email: str, password: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        logger.warning("登录失败: email=%s", email)
        raise AuthenticationError("邮箱或密码错误")
    logger.info("用户登录: email=%s", email)
    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }


def request_password_reset(db: Session, email: str) -> str | None:
    """请求密码重置，返回重置令牌（或 None 当用户不存在时）。

    出于安全考虑，即使用户不存在也不返回错误，避免邮箱枚举攻击。
    实际发送邮件的逻辑由调用方处理（当前仅记录日志）。
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        logger.info("密码重置请求：邮箱 %s 不存在（静默忽略）", email)
        return None

    token = create_password_reset_token(str(user.id))
    logger.info("密码重置令牌已生成: email=%s", email)
    # TODO: 集成邮件发送服务（SMTP/SendGrid），将重置链接发送给用户
    # 当前开发阶段仅返回令牌，由前端处理跳转
    return token


def confirm_password_reset(db: Session, token: str, new_password: str) -> User:
    """确认密码重置：验证令牌并更新密码。"""
    from app.core.exceptions import BusinessError

    user_id = verify_password_reset_token(token)
    if user_id is None:
        raise BusinessError(
            "INVALID_RESET_TOKEN", "重置令牌无效或已过期", 400,
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise BusinessError("USER_NOT_FOUND", "用户不存在", 400)

    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    _invalidate_user_cache(user.id)
    logger.info("密码已重置: email=%s", user.email)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> User:
    """已登录用户修改密码（需验证当前密码）。"""
    from app.core.exceptions import BusinessError

    if not verify_password(current_password, user.password_hash):
        raise BusinessError(
            "CURRENT_PASSWORD_INVALID", "当前密码不正确", 400,
        )

    # user 可能来自 get_current_user 缓存（detached），重新查询以确保附加到 session
    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user is None:
        raise BusinessError("USER_NOT_FOUND", "用户不存在", 400)
    db_user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(db_user)
    _invalidate_user_cache(db_user.id)
    logger.info("用户修改密码: email=%s", db_user.email)
    return db_user
