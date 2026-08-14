"""数据真实性接入层契约模型（系统设计 §4.2.8 ~ §4.2.10）。

MVP 方案 C：契约先行、实现延后 — 仅落库建表，业务逻辑后续实现。
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, BigIntPK, ContractAuditMixin


class DataSourceMeta(ContractAuditMixin, Base):
    """外部数据来源元数据（t_data_source）。

    source_system：yanzhao / school_official / bilibili / web / rss / user_reported / model_inferred。
    credibility：official_verified / user_reported / model_inferred。
    review_status：PENDING / APPROVED / REJECTED。
    """
    __tablename__ = "t_data_source"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    source_system: Mapped[str] = mapped_column(String(30), nullable=False)
    # yanzhao / school_official / bilibili / web / rss / user_reported / model_inferred
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    crawled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    credibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="model_inferred",
        server_default=text("'model_inferred'"),
    )
    # official_verified / user_reported / model_inferred
    verify_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    # PENDING / APPROVED / REJECTED

    __table_args__ = (
        UniqueConstraint("source_url", name="uk_data_source_source_url"),
        Index("idx_data_source_credibility", "credibility"),
        Index("idx_data_source_review_status", "review_status"),
    )


class ExternalResearchItem(ContractAuditMixin, Base):
    """外部调研条目（t_external_research_item）。

    item_type：experience_post / dark_knowledge / kaoyan_news。
    credibility：official_verified / user_reported / model_inferred。
    review_status：PENDING / APPROVED / REJECTED / DUPLICATED。
    """
    __tablename__ = "t_external_research_item"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    crawler_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 契约适配：系统设计 §4.2.9 定义为 BIGINT，但存量 CrawlerRun.id 是 UUID(GUID)。
    # 本表刚建且全空，将 crawler_run_id 改为 VARCHAR(64) 存 CrawlerRun.id 的 UUID 字符串，
    # 避免 UUID 无法写入 BIGINT 列（详见批次3报告）。
    crawler_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # experience_post / dark_knowledge / kaoyan_news
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_platform: Mapped[str] = mapped_column(String(30), nullable=False)
    external_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    credibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="model_inferred",
        server_default=text("'model_inferred'"),
    )
    # official_verified / user_reported / model_inferred
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    # PENDING / APPROVED / REJECTED / DUPLICATED

    __table_args__ = (
        UniqueConstraint("source_url", name="uk_external_research_item_source_url"),
        Index("idx_external_research_item_crawler_run_id", "crawler_run_id"),
        Index("idx_external_research_item_review_status", "review_status"),
    )


class ReviewQueueItem(ContractAuditMixin, Base):
    """审核队列条目（t_review_queue_item）。

    item_type：external_research / mentor_review。
    review_status：PENDING / APPROVED / REJECTED。
    """
    __tablename__ = "t_review_queue_item"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # external_research / mentor_review
    ref_item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    # PENDING / APPROVED / REJECTED
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    biz_req_no: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("biz_req_no", name="uk_review_queue_item_biz_req_no"),
        Index("idx_review_queue_item_status_created_time", "review_status", "created_time"),
        Index("idx_review_queue_item_type_ref", "item_type", "ref_item_id"),
    )


class DataFreshness(Base):
    """数据源新鲜度引擎（data_freshness，B4）。

    列契约与 app/api/data_freshness.py 的 raw SQL 一致（勿改列名/默认值）：
    - source_name 主键（渠道名，对应 SOURCES 字典键：yanzhao/kaoyan/offcn/...）
    - last_successful_crawl 最近一次成功抓取/确认时间
    - records_count 累计确认入库条数
    - status active / refreshing / unknown
    - updated_at 回写时间
    """

    __tablename__ = "data_freshness"

    source_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    last_successful_crawl: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    records_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unknown", server_default=text("'unknown'")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
