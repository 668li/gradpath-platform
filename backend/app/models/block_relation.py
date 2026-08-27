"""用户屏蔽关系模型 — 社区治理。"""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class BlockRelation(UUIDMixin, TimestampMixin, Base):
    """blocker_id 屏蔽 blocked_id（单向）。"""

    __tablename__ = "block_relations"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_block_relation_pair"),)

    blocker_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    blocked_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )

    blocker = relationship("User", foreign_keys=[blocker_id])
    blocked = relationship("User", foreign_keys=[blocked_id])
