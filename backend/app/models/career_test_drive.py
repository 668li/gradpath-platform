# backend/app/models/career_test_drive.py
"""职业试驾模型 — 第一人称一日体验生成器。

用户在职业路径模拟器选定路径后可"试驾"一天：AI（或预设模板）生成
8-10 个时间段的一日体验（时间/活动/描述/情绪），并附一日总结、优点与挑战，
帮助用户在正式决策前切身感受每条路径。
"""

from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class CareerTestDrive(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "career_test_drives"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # 路径类型: kaoyan / employment / civil_service
    path_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # 目标角色，如 "互联网产品经理" / "考研计算机"
    target_role: Mapped[str] = mapped_column(String(100), nullable=False)
    # AI 生成的一日体验内容：{time_blocks, summary, pros, cons}
    experience_content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
