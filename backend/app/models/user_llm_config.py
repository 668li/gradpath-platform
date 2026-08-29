# backend/app/models/user_llm_config.py
"""用户自带 LLM API 配置 — BYOK（Bring Your Own Key）。

服务器未配置 LLM_API_KEY 时，用户可在设置页填入自己的
OpenAI 兼容 API（base_url / model / api_key）启用 AI 对话。
api_key 经 Fernet 加密后落库（见 app.core.secret_crypto）。
"""

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class UserLLMConfig(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_llm_configs"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="custom")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
