"""爬虫执行日志模型。"""
from sqlalchemy import Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class CrawlerRun(UUIDMixin, TimestampMixin, Base):
    """爬虫执行记录 — 记录每次爬取的状态和统计。

    注：t_crawler_runs 契约扩展（系统设计 §4.2.11）— 表名保留 crawler_runs，
    追加 stored_count / duplicate_count / source_meta 三个字段。
    """
    __tablename__ = "crawler_runs"

    source_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    # running / success / failed / not_found

    started_at: Mapped[str] = mapped_column(String(50), nullable=True)
    finished_at: Mapped[str] = mapped_column(String(50), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

    items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    items_stored: Mapped[int] = mapped_column(Integer, default=0)
    items_duplicates: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    log: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === t_crawler_runs 契约扩展（系统设计 §4.2.11）===
    # server_default 与迁移 e5a9c2f4b7d1 保持一致（存量表 ADD COLUMN NOT NULL 必须带默认值）
    stored_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    duplicate_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    source_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
