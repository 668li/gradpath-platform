# backend/app/models/career_profile.py
"""用户职业画像模型 — 记录用户的教育背景、目标方向与自我评估。

每个用户最多拥有一份职业画像，用于个性化推荐与规划生成。
"""
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class CareerProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "career_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # 教育背景
    education_level: Mapped[str | None] = mapped_column(String(50), nullable=True)  # high_school, bachelor, master, phd, other
    major: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 专业
    school_name: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 学校名称
    school_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 985, 211, 双非, 海外, 其他
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 毕业年份

    # 目标方向
    target_direction: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 目标方向，如"大厂后端开发"
    target_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 目标行业

    # 自我评估 (1-5分)
    technical_skill: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 技术能力
    communication_skill: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 沟通能力
    leadership_skill: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 领导力
    creativity_skill: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 创造力

    # 其他
    self_introduction: Mapped[str | None] = mapped_column(Text, nullable=True)  # 自我介绍
