"""爬虫线状态表模型（数据地基④，spec 002 FR3）。

每条爬虫线一行的持久化状态：增量游标、最近成功时刻、连续失败计数、隔离位。
BaseCrawler 运行生命周期读写；调度器按 isolated 位跳过隔离线（地基⑥联动）。
"""

from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB


class CrawlerSourceState(Base):
    """爬虫线状态（t_crawler_source_state）。

    - cursor：增量游标（JSONB）——etag / last_modified / 最新发布时间 / known_urls 等，
      由各线自定义结构；运行前读、成功后写。
    - consecutive_fails：连续失败运行数（成功清零）；≥2 → isolated=True（地基⑥）。
    - isolated：隔离位。调度器跳过隔离线；解除是显式人工动作（admin 端点）。
    """

    __tablename__ = "t_crawler_source_state"

    source_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    cursor: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    etag: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consecutive_fails: Mapped[int] = mapped_column(
        default=0, server_default=text("0"), nullable=False
    )
    isolated: Mapped[bool] = mapped_column(default=False, server_default=text("0"), nullable=False)
    isolated_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CrawlerSourceState {self.source_name} fails={self.consecutive_fails} isolated={self.isolated}>"
