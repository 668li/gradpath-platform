"""失败案例库模型 — 对冲幸存者偏差的真实失败叙事。

设计理念：
- 匿名性优先：不存 user_id 关联，只存 author_role（在校生/毕业生/工作3年内等）
- 真实第一人称叙事，附具体教训与"如果重来"建议
- 按路径 / 阶段 / 教训分类，支持筛选
- 用户可匿名分享自己的失败经历（默认 pending，需审核）
"""

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class FailureCase(UUIDMixin, TimestampMixin, Base):
    """失败案例主表 — 匿名存储真实失败叙事。"""

    __tablename__ = "failure_cases"
    __table_args__ = (
        Index("ix_failure_case_path_status", "path_type", "status"),
        Index("ix_failure_case_stage", "stage"),
    )

    # === 匿名性：不存 user_id 关联，只存 author_role ===
    author_role: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 在校生/毕业生/工作3年内 等
    path_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # kaoyan/civil_service/employment/study_abroad
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # preparation/interview/final_year1/year2_plus

    # === 内容 ===
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    story: Mapped[str] = mapped_column(Text, nullable=False)  # 第一人称叙事
    lessons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 教训列表
    regrets: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 后悔的事
    what_would_i_do: Mapped[str] = mapped_column(Text, nullable=False)  # 如果重来会怎么做

    # === 审核状态 ===
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending/approved/rejected

    # === 互动 ===
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
