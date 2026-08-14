import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, invalidate_user_cache
from app.core.exceptions import BusinessError
from app.core.security import create_access_token, verify_refresh_token
from app.database import get_db
from app.main import limiter
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordChangeRequest,
    PasswordResetConfirm,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
    UpdateMeRequest,
    UserResponse,
)
from app.services.auth_service import (
    change_password,
    confirm_password_reset,
    login,
    register,
    request_password_reset,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])

audit_logger = logging.getLogger("gradpath.audit")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def register_endpoint(
    request: Request,
    response: Response,
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    # B3 合规：双重校验（schema 默认 True，此处显式拒绝 False）
    if not data.agree_terms:
        raise BusinessError(
            "TERMS_NOT_AGREED",
            "注册需同意《隐私政策》和《用户协议》",
            400,
            details={"field": "agree_terms"},
        )
    user = register(db, data)
    audit_logger.info(
        "user_registered",
        extra={
            "event": "user_registered",
            "user_id": str(user.id),
            "email": data.email,
            "ip": request.client.host if request.client else "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login_endpoint(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    tokens = login(db, data.email, data.password)
    audit_logger.info(
        "user_login_success",
        extra={
            "event": "user_login_success",
            "email": data.email,
            "ip": request.client.host if request.client else "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return tokens


@router.get("/me", response_model=UserResponse)
def me_endpoint(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me_endpoint(
    data: UpdateMeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """轻量设置页（C2）：更新昵称/学校/专业/毕业年份/简介。

    - 只更新显式传入的字段（exclude_unset），None 表示清除该字段
    - 更新后主动失效 get_current_user 的 60s 缓存，避免旧资料滞留
    - 不覆盖 name/email/password（改密码不在本轮范围）
    """
    updates = data.model_dump(exclude_unset=True)
    if updates:
        # get_current_user 可能命中缓存返回脱管实例，这里按 id 重查绑定会话
        db_user = db.query(User).filter(User.id == current_user.id).first()
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在",
            )
        for field, value in updates.items():
            setattr(db_user, field, value)
        db.commit()
        db.refresh(db_user)
        invalidate_user_cache(current_user.id)
        return db_user
    return current_user


@router.post("/refresh", response_model=RefreshResponse)
@limiter.limit("10/minute")
def refresh_token(
    request: Request,
    response: Response,
    body: RefreshRequest,
):
    """用 refresh_token 换取新的 access_token。

    修复: FASTAPI-LIMITS-001 — 加 rate limit 防止 refresh 滥用（无限刷新绕过 access_token 过期）。
    """
    user_id = verify_refresh_token(body.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="refresh_token 无效或已过期")
    new_access_token = create_access_token(str(user_id))
    return RefreshResponse(access_token=new_access_token)


# ===== 密码重置 =====
@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    response: Response,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Request password reset.

    Returns the same message regardless of email existence (prevents enumeration).
    In development, returns the token directly for testing.
    """
    token = request_password_reset(db, data.email)
    audit_logger.info(
        "password_reset_requested",
        extra={
            "event": "password_reset_requested",
            "email": data.email,
            "ip": request.client.host if request.client else "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    from app.config import settings

    # 安全修复 H1: 重置令牌绝不在 HTTP 响应中返回（任何环境）
    # 开发模式下仅记录到服务端日志供调试
    if settings.ENVIRONMENT == "development" and token:
        audit_logger.info("DEV password reset token for %s: %s", data.email, token)
    return MessageResponse(message="若该邮箱已注册，重置链接将发送至您的邮箱")


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    response: Response,
    data: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """Reset password using a reset token."""
    confirm_password_reset(db, data.token, data.new_password)
    audit_logger.info(
        "password_reset_completed",
        extra={
            "event": "password_reset_completed",
            "ip": request.client.host if request.client else "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return MessageResponse(message="密码重置成功，请使用新密码登录")


@router.post("/change-password", response_model=MessageResponse)
@limiter.limit("5/minute")
def change_password_endpoint(
    request: Request,
    response: Response,
    data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change password (requires current password verification).

    修复: FASTAPI-LIMITS-001 — 加 rate limit 防止暴力尝试当前密码。
    """
    change_password(db, current_user, data.current_password, data.new_password)
    audit_logger.info(
        "password_changed",
        extra={
            "event": "password_changed",
            "user_id": str(current_user.id),
            "ip": request.client.host if request.client else "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return MessageResponse(message="密码修改成功")
