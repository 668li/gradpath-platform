"""成长档案中心契约模型（系统设计 §4.2.5 ~ §4.2.6）。

MVP 方案 C：契约先行、实现延后 — 仅落库建表，业务逻辑后续实现。
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, BigIntPK, ContractAuditMixin


class GrowthTrajectory(ContractAuditMixin, Base):
    """成长轨迹事件流（t_growth_trajectory）。

    event_type：action_checkin / review_completed / milestone。
    event_payload：事件结构化载荷（JSONB）。
    """

    __tablename__ = "t_growth_trajectory"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # action_checkin / review_completed / milestone
    event_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_event_id", name="uk_growth_trajectory_source_event_id"),
        Index("idx_growth_trajectory_user_id_occurred_at", "user_id", "occurred_at"),
    )


class GrowthArchive(ContractAuditMixin, Base):
    """成长档案聚合快照（t_growth_archive）。

    archive_status：ACTIVE / STALE。
    """

    __tablename__ = "t_growth_archive"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    action_completion_rate: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default=text("0")
    )
    total_actions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    completed_actions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    streak_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    weighted_action_score: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default=text("0")
    )
    archive_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'")
    )
    # ACTIVE / STALE

    __table_args__ = (UniqueConstraint("user_id", name="uk_growth_archive_user_id"),)
