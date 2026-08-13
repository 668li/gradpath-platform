"""路径冲突调解模型 — 当测评结果与用户现状冲突时记录调解过程。

竞品调研发现的高 ROI 差异化功能：当用户的测评结果(如 Holland RIASEC 推荐技术岗)
与用户当前现状(如已在准备考公)冲突时，不是强制推荐，而是提供 3 条路径让用户自主选择：
1. 坚持现状
2. 转向推荐
3. 折中方案
"""
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class PathConflictResolution(UUIDMixin, TimestampMixin, Base):
    """路径冲突调解记录 — 一次完整的冲突检测 + 用户选择 + 行动计划。"""

    __tablename__ = "path_conflict_resolutions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 冲突类型，如 "assessment_vs_current"（测评结果 vs 用户现状）
    conflict_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # 测评结果摘要，如 {"type": "holland", "code": "RIA", "directions": [...]}
    assessment_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # 用户现状摘要，如 {"destination_type": "civil_service", "status": "planned", ...}
    current_situation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # 3 条路径选项数组，每项含 id/title/description/pros/cons/estimated_timeline/risk_level
    options: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 用户选择的选项索引：0=坚持现状, 1=转向推荐, 2=折中方案
    selected_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 用户选择的理由（自由文本）
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 系统根据用户选择生成的行动计划
    action_plan: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
