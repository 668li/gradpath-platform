"""国考职位模型 — 对应 2026 国考招考简章职位表（fetch_gwy_positions.py 采集入库）。

列契约与采集器 fetch_gwy_positions.py 的 SHEET_COLUMNS 一致（勿改列名/类型），
主键为整行 sha256 摘要：官方 position_code 并非唯一（同一 code 对应多条专业/学历
不同的记录），故以整行哈希作为幂等 upsert 的依据。
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class GwyPosition(TimestampMixin, Base):
    """国考职位表 — 国家公务员局官方招考简章（sheet: 中央党群机关 / 中央国家行政机关本级 / 省级以下直属机构 / 参照公务员法管理事业单位）。"""

    __tablename__ = "gwy_position"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    exam_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # === 职位信息 ===
    dept_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dept_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bureau: Mapped[str | None] = mapped_column(String(200), nullable=True)
    agency_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position_attr: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position_distribution: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    position_code: Mapped[str] = mapped_column(String(50), nullable=False)
    org_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    exam_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recruit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    major_req: Mapped[str | None] = mapped_column(Text, nullable=True)
    education_req: Mapped[str | None] = mapped_column(String(100), nullable=True)
    degree_req: Mapped[str | None] = mapped_column(String(100), nullable=True)
    political_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    min_work_years: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grassroots_exp_req: Mapped[str | None] = mapped_column(String(50), nullable=True)
    professional_test: Mapped[str | None] = mapped_column(String(50), nullable=True)
    interview_ratio: Mapped[str | None] = mapped_column(String(50), nullable=True)
    work_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    settle_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    dept_website: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone1: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone2: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone3: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # === 来源信息 ===
    sheet_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # 列表筛选 + 统计的主查询路径：按年份 + 职位代码定位
        Index("ix_gwy_position_year_code", "year", "position_code"),
    )
