# backend/app/models/dataset_info.py
"""GitHub 开源数据集元信息模型 — 记录可接入的外部开源数据集描述与缓存状态。

供 github_datasets 爬虫写入，便于后续按领域检索并下载开源数据集补充决策数据。
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class DatasetInfo(UUIDMixin, TimestampMixin, Base):
    """开源数据集元信息 — 描述一个可下载的外部数据集。"""

    __tablename__ = "dataset_info"

    user_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    dataset_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 就业 / 教育 / 经济 / 人口 / 行业
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # 来源仓库，如 "awesome-jobs" / "china-edu-data"
    source_repo: Mapped[str] = mapped_column(String(200), nullable=False)
    github_url: Mapped[str] = mapped_column(Text, nullable=False)
    # json / csv / parquet
    file_format: Mapped[str] = mapped_column(String(20), nullable=False, default="csv")
    # 预估文件大小（人类可读，如 "12.5MB"）
    file_size_estimate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    license: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 数据集记录条数估计
    record_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 字段列表 JSON，如 [{"name": "year", "type": "int"}, ...]
    field_schema: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 本地缓存路径（未下载时为空）
    local_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_downloaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
