# backend/app/models/company_review.py
"""公司评价模型 — 员工/前员工匿名分享的公司评价，覆盖工作生活平衡、薪资满意度等维度。"""
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class CompanyReview(UUIDMixin, TimestampMixin, Base):
    """公司评价 — 来自看准网/脉脉等平台的公司匿名评价数据。

    核心字段对应求职者最关心的 4 个维度：
    - 工作生活平衡 (work_life_balance)
    - 薪资满意度 (salary_satisfaction)
    - 企业文化评分 (culture_score)
    - 职业成长空间 (career_growth)
    """
    __tablename__ = "company_reviews"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "company", "title",
            name="uq_user_company_review_title",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 公司名（与 Company/SalaryBenchmark/InterviewReport 一致，使用字符串而非 FK）
    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    # 总体评分 1-5
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 是否推荐入职
    is_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 工作生活平衡 1-5
    work_life_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    # 薪资满意度 1-5
    salary_satisfaction: Mapped[int] = mapped_column(Integer, nullable=False)
    # 企业文化评分 1-5
    culture_score: Mapped[int] = mapped_column(Integer, nullable=False)
    # 职业成长空间 1-5
    career_growth: Mapped[int] = mapped_column(Integer, nullable=False)
    # 评价来源链接
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 来源平台（如 看准网/脉脉）
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
