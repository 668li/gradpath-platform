from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserStage
from app.schemas.path_comparison import (
    _EDUCATION_LEVELS,
    _FRESH_STATUSES,
    _GENDERS,
    _PARTY_STATUSES,
)


def _validate_identity_field(v: str | None, field_name: str) -> str | None:
    """身份包取值白名单 — 与 DecisionEngineRequest 同一套常量，防止脏值入库。

    脏值入库会在决策引擎预填时被其 validator 422 拒绝，用户卡死在 analyze。
    """
    if v is None:
        return v
    allowed = {
        "fresh_status": _FRESH_STATUSES,
        "party_status": _PARTY_STATUSES,
        "education": _EDUCATION_LEVELS,
        "gender": _GENDERS,
    }[field_name]
    if v not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(sorted(allowed))}")
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    # B3 合规：注册需明确同意《隐私政策》《用户协议》。
    # 默认 True 以保持与既有调用方兼容；service 层会显式拒绝 False。
    agree_terms: bool = True
    # 报考身份包（W1-D3/D4）：免费预览带回，注册即落库，登录后自动预填。
    # 白名单校验见 _validate_identity_fields（公开端点，防脏值入库+防超长 500）。
    fresh_status: str | None = Field(None, max_length=10, description="应届/非应届")
    party_status: str | None = Field(None, max_length=20, description="中共党员/党员或团员/群众")
    education: str | None = Field(None, max_length=10, description="博士/硕士/本科/大专")
    gender: str | None = Field(None, max_length=4, description="男/女")
    has_grassroots: bool | None = Field(None, description="是否已满足基层工作经历")

    @field_validator("fresh_status", "party_status", "education", "gender")
    @classmethod
    def _validate_identity_fields(cls, v, info):
        return _validate_identity_field(v, info.field_name)


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
    # 报考身份包
    fresh_status: str | None = None
    party_status: str | None = None
    education: str | None = None
    gender: str | None = None
    has_grassroots: bool | None = None

    model_config = {"from_attributes": True}


class UpdateMeRequest(BaseModel):
    """轻量设置页可编辑字段（C2；改密码/头像不在本轮范围）。

    全部可空：None 表示清除该字段，未传字段保持原值（exclude_unset）。
    身份包字段与决策引擎/免费预览共用同一取值口径。
    """

    nickname: str | None = Field(default=None, max_length=50)
    school: str | None = Field(default=None, max_length=255)
    major: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1970, le=2100)
    bio: str | None = Field(default=None, max_length=500)
    fresh_status: str | None = Field(default=None, max_length=10)
    party_status: str | None = Field(default=None, max_length=20)
    education: str | None = Field(default=None, max_length=10)
    gender: str | None = Field(default=None, max_length=4)
    has_grassroots: bool | None = Field(default=None)

    @field_validator("fresh_status", "party_status", "education", "gender")
    @classmethod
    def _validate_identity_fields(cls, v, info):
        return _validate_identity_field(v, info.field_name)


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
