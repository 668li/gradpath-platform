"""行动任务中心契约模型（系统设计 §4.2.1 ~ §4.2.4）。

MVP 方案 C：契约先行、实现延后 — 仅落库建表，业务逻辑后续实现。
"""
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, BigIntPK, ContractAuditMixin


class DailyAction(ContractAuditMixin, Base):
    """每日行动任务（t_action）。

    状态机：PENDING → DONE / EXPIRED / CANCELED。
    唯一约束：同一用户同一天同一类型只能存在一条行动（UK_user_id_action_type_due_date）。
    """
    __tablename__ = "t_action"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_decision_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    weight: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    # PENDING / DONE / EXPIRED / CANCELED
    biz_req_no: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "action_type", "due_date",
            name="uk_action_user_id_action_type_due_date",
        ),
        Index("idx_action_user_id_due_date", "user_id", "due_date"),
        Index("idx_action_user_id_status", "user_id", "status"),
    )


class ActionCheckin(ContractAuditMixin, Base):
    """行动打卡记录（t_action_checkin）。"""
    __tablename__ = "t_action_checkin"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    action_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    biz_req_no: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("biz_req_no", name="uk_action_checkin_biz_req_no"),
        Index("idx_action_checkin_user_id_completed_at", "user_id", "completed_at"),
        Index("idx_action_checkin_action_id", "action_id"),
    )


class ActionStreak(ContractAuditMixin, Base):
    """行动连续打卡统计（t_action_streak）。

    streak_status：ACTIVE / BROKEN / NEVER。
    """
    __tablename__ = "t_action_streak"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    current_streak_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    longest_streak_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    last_checkin_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    streak_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="NEVER", server_default=text("'NEVER'")
    )
    # ACTIVE / BROKEN / NEVER

    __table_args__ = (
        UniqueConstraint("user_id", name="uk_action_streak_user_id"),
    )


class ActionWeight(ContractAuditMixin, Base):
    """行动类型权重配置（t_action_weight）。"""
    __tablename__ = "t_action_weight"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    weight: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    weight_label: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("TRUE")
    )

    __table_args__ = (
        UniqueConstraint("action_type", name="uk_action_weight_action_type"),
    )
