# backend/app/models/conversation.py
"""对话与消息模型 — Phase 11 AI 职业管家的会话底座。

Conversation 记录一个对话主题与激活的 Skill 集合；
Message 记录每轮 user/assistant 消息，含 skill_used 与 context_snapshot 快照。
"""
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class Conversation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    active_skills: Mapped[list] = mapped_column(JSONB, default=list)


class Message(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    skill_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    context_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
