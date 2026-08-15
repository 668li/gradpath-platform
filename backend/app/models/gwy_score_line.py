"""国考进面分数线模型 — 对应 2026 国考面试人员名单（fetch_gwy_interview.py 采集入库）。

列契约与采集器一致（勿改列名/类型）。官方面试名单按"人"发布（每人一行，含准考证号/
姓名等个人信息），采集器已聚合为职位级记录：同一职位多名考生进面线一致，只存一行
min_score，个人字段一律不入库。batch 区分批次：首批 / 调剂 / 补充录用。
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class GwyScoreLine(TimestampMixin, Base):
    """国考进面分数线（职位级，无个人信息）— 面试名单聚合结果。"""

    __tablename__ = "gwy_score_line"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    batch: Mapped[str] = mapped_column(String(20), nullable=False)  # 首批 / 调剂 / 补充录用

    # === 职位信息 ===
    dept_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dept_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bureau: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position_code: Mapped[str] = mapped_column(String(50), nullable=False)
    min_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # === 来源信息 ===
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # 按职位关联分数线的主查询路径：年份 + 职位代码
        Index("ix_gwy_score_line_year_code", "year", "position_code"),
    )
