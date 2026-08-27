"""考研经验贴模型 — 社区交流系统。

核心字段：
- 基础信息：标题/摘要/正文/分类/标签
- 作者信息：user_id / 是否匿名
- 互动统计：浏览数/点赞数/评论数
- 审核机制：待审核/已通过/已拒绝
- 来源信息：来源平台/来源链接/是否验证
"""

from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class ExperiencePost(UUIDMixin, TimestampMixin, Base):
    """考研经验贴主表 — 存储学长学姐经验分享内容。"""

    __tablename__ = "experience_posts"
    __table_args__ = (Index("ix_exp_post_pinned_created", "is_pinned", "created_at"),)

    # === 关联 ===
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # === 内容 ===
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general", index=True
    )  # general/初试/复试/调剂/择校/复习

    # === 互动统计 ===
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # === 外部平台统计（爬虫/第三方来源） ===
    external_view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    external_like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # === 排序与展示 ===
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # === 审核机制 ===
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )  # pending/approved/rejected

    # === 来源信息 ===
    source_platform: Mapped[str] = mapped_column(
        String(100), nullable=False, default="user"
    )  # user/crawler/zhihu/xiaohongshu
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # === 提纯与质量（Phase G 经验闭环核心） ===
    quality_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 0-100，规则打分器计算
    quality_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)  # A/B/C/D
    ai_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # LLM 可选增强摘要（未配置则 NULL，诚实降级）
    structured_meta: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # 结构化元信息 {subject/stage/school/target_score/methods/audience}
    is_promotion: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=False
    )  # 疑似软广标注（不下架；NULL=未检测）
    promotion_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=0.0
    )  # 软广置信度 0-1
    promotion_reason: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # 命中关键词说明
    quality_reasons: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, default=list
    )  # 质量分扣分原因逐条（可解释徽章，Phase I）：["内容完整度 24/30：…", "反软广 0/10：疑似软广(命中:课程)"]
