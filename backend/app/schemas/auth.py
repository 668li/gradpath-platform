from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserStage


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    # B3 合规：注册需明确同意《隐私政策》《用户协议》。
    # 默认 True 以保持与既有调用方兼容；service 层会显式拒绝 False。
    agree_terms: bool = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    nickname: str | None = None
    bio: str | None = None
    current_stage: UserStage | None = None
    school: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateMeRequest(BaseModel):
    """轻量设置页可编辑字段（C2；改密码/头像不在本轮范围）。

    全部可空：None 表示清除该字段，未传字段保持原值（exclude_unset）。
    """

    nickname: str | None = Field(default=None, max_length=50)
    school: str | None = Field(default=None, max_length=255)
    major: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1970, le=2100)
    bio: str | None = Field(default=None, max_length=500)


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ===== 密码重置 =====
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, description="密码重置令牌")
    new_password: str = Field(min_length=8, max_length=128, description="新密码（至少8位）")


class PasswordChangeRequest(BaseModel):
    """已登录用户修改密码（需提供当前密码验证）。"""

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    """通用消息响应。"""

    message: str
