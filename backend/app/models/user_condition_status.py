"""用户报考条件状态 — 条件账本的勾选记录（技能树转型的落点）。

每个用户对某个目标职位的每条报考条件维护一个三态状态：
unmet（未满足）/ in_progress（进行中）/ met（已满足）。
条件清单本身由 gwy_position 行规则生成（condition_checklist_service），
本表只存用户的核对进度，条件定义不落库（跟职位表数据走）。
"""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

# 条件状态三态：未满足 → 进行中 → 已满足
CONDITION_STATUSES = ("unmet", "in_progress", "met")


class UserConditionStatus(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_condition_status"
    __table_args__ = (
        UniqueConstraint("user_id", "position_id", "condition_key", name="uq_user_condition_key"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # gwy_position.id（整行 sha256 摘要），不设外键：职位表按批次重建，
    # 历史勾选保留但清单以当前职位表为准
    position_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    condition_key: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unmet")
