"""导师主表模型 — 考研导师信息。

核心字段：
- 基础信息：姓名/院校/院系/职称/研究方向
- 学术信息：论文数/项目数/引用数/学术主页链接
- 招生信息：招生状态/招生方向/联系方式
- 评价统计：平均评分/评价数/各维度评分
"""
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class Mentor(UUIDMixin, TimestampMixin, Base):
    """导师主表 — 存储导师基础信息和学术信息。"""
    __tablename__ = "mentors"
    __table_args__ = (
        Index("ix_mentors_university_rating", "university", "avg_rating"),
        Index("ix_mentors_university_department", "university", "department"),
    )

    # === 基础信息 ===
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    university: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)  # 教授/副教授/讲师/博导/硕导
    research_directions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # ["机器学习", "深度学习"]
    
    # === 学术信息 ===
    paper_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 论文数
    project_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 项目数
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 引用数
    h_index: Mapped[int | None] = mapped_column(Integer, nullable=True)  # h-index
    academic_homepage: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 学术主页链接
    google_scholar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cnki_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # === 招生信息 ===
    enrollment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")  # accepting/not_accepting/unknown
    enrollment_directions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 当前招生方向
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # === 评价统计（冗余字段，定期更新）===
    avg_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 平均评分 1-5
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 评价总数
    
    # 6 维评分（冗余字段，定期更新）
    rating_academic: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 学术水平
    rating_guidance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 指导风格
    rating_relationship: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 师生关系
    rating_funding: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 科研经费
    rating_workload: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 工作强度
    rating_career: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 毕业前景
    
    # === 数据来源 ===
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 数据来源 URL
    source_platform: Mapped[str] = mapped_column(String(100), nullable=False, default="official")  # official/crawler/user
    
    # === 元数据 ===
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # 是否已验证
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 标签 ["985", "211", "热门"]
