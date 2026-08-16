"""考研外部资讯模型 — 聚合 RSS/爬虫获取的政策、调剂、招生简章、复试等新闻。"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin, _utcnow


class KaoyanNews(UUIDMixin, TimestampMixin, Base):
    """考研资讯表 — 存储从 RSS、新闻站点等外部来源抓取的考研相关信息。"""
    __tablename__ = "kaoyan_news"

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === 来源信息 ===
    source_platform: Mapped[str] = mapped_column(
        String(50), nullable=False, default="rss"
    )  # rss/crawler/official
    source_url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)

    # === 时间 ===
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # === 审核与分类 ===
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending/approved/rejected
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general", index=True
    )  # general/政策/调剂/招生简章/复试/复试线/推免/报录比/择校/备考

    # === 标签 ===
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # === 提纯与质量（信息差升级） ===
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI 摘要（LLM 可选增强）
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100
    quality_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)  # A/B/C/D
    key_dates: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )  # 关键时间点 [{label, date}]：报名/确认/考试/调剂窗口
    is_expired: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # 时效过期标记（关键时间点已过或超过 180 天）
    structured_meta: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # 决策数据卡 {enrollment_count/exam_subjects/reference_books/evidence/confidence/effective_year}（Phase G 规则抽取 + Phase I 证据链）
    quality_reasons: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, default=list
    )  # 质量分扣分原因逐条（可解释徽章，Phase I）
