import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, UUIDMixin


class SnapshotSource(str, enum.Enum):
    report = "report"
    community = "community"


class ReferenceSnapshot(UUIDMixin, Base):
    __tablename__ = "reference_snapshots"

    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_type: Mapped[SnapshotSource] = mapped_column(Enum(SnapshotSource), nullable=False)
    query_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
