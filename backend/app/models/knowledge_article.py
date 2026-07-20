# backend/app/models/knowledge_article.py
"""知识库条目模型 — Phase 11 AI 职业管家的知识底座。

存储行业指南、岗位要求、技能图谱、面试指南、薪资参考、升学路径等结构化知识，
供 Skill 系统 RAG 检索使用。
"""
from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class KnowledgeArticle(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_articles"
    __table_args__ = (
        Index("ix_knowledge_articles_is_published", "is_published"),
        Index("ix_knowledge_articles_category_published", "category", "is_published"),
    )

    # industry_guide / job_requirement / skill_map / interview_guide / salary_reference / education_path
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)  # 搜索字段，B-tree 索引
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown
    tags: Mapped[list] = mapped_column(JSONB, default=list)  # ["后端", "Python", "大厂"]
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)  # company, position, city...
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
