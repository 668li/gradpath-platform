"""省考职位模型 — 对应各省公务员考试招录职位表（首例：广东省 2026 考试录用公务员职位表，
由 fetch_gd_shengkao_positions.py 采集入库）。

列契约与采集器保持一致（勿改列名/类型）：广东职位表 6 个 sheet（县以上机关/公安/法院/
检察院/监狱戒毒/乡镇机关），各 sheet 表头行与列数略有差异（15~17 列），采集器按列名映射，
缺列置 NULL。主键为整行 sha256 摘要（官方职位表同一 position_code 可能对应多行不同
专业/学历要求），保证官方每一行都入库且重复运行幂等。后续扩充其他省份/历年共用此表，
以 (province, year, position_code) 复合索引支撑筛选统计。
"""

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class GwyProvincePosition(TimestampMixin, Base):
    """省考职位表 — 各省考试录用公务员招录职位（sheet: 县以上机关 / 公安 / 法院 / 检察院 / 监狱戒毒 / 乡镇机关）。"""

    __tablename__ = "gwy_province_position"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    province: Mapped[str] = mapped_column(String(20), nullable=False)

    # === 职位信息（广东 2026 列名映射）===
    dept_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dept_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position_code: Mapped[str] = mapped_column(String(50), nullable=False)
    position_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    position_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recruit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education_req: Mapped[str | None] = mapped_column(String(100), nullable=True)
    degree_req: Mapped[str | None] = mapped_column(String(100), nullable=True)
    major_req_grad: Mapped[str | None] = mapped_column(Text, nullable=True)
    major_req_undergrad: Mapped[str | None] = mapped_column(Text, nullable=True)
    major_req_junior: Mapped[str | None] = mapped_column(Text, nullable=True)
    grassroots_exp_req: Mapped[str | None] = mapped_column(String(10), nullable=True)
    psych_test: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fresh_grad_only: Mapped[str | None] = mapped_column(String(10), nullable=True)
    other_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    exam_region: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # === 来源信息 ===
    sheet_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # 列表筛选 + 统计的主查询路径：按年份 + 省份 + 职位代码定位
        Index("ix_gwy_province_position_year_prov_code", "year", "province", "position_code"),
    )
