"""站点流量日聚合模型 — 流量看板（/admin/traffic）数据源。

可借鉴模式：宿主侧只读聚合（monitoring/traffic_pipeline.sh）→ 日聚合宽表落库 →
admin 只读 API → 前端看板。转化率/留存等其他指标可在此宽表加列，走同一管道，
不必各起炉灶。口径与微信日报 visitors.sh 完全一致（同一套 window_stats）。
"""

from datetime import date as date_cls

from sqlalchemy import Date, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin


class TrafficDaily(TimestampMixin, Base):
    """每日一行：pv/uv/blocked 来自 nginx 日志（444 单列，机器人已滤），
    registrations 来自 users 表按北京时间日聚合。幂等 upsert，当日行为部分快照，
    次日起稳定。"""

    __tablename__ = "t_traffic_daily"

    date: Mapped[date_cls] = mapped_column(Date, primary_key=True)  # 北京时间日
    pv: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uv: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registrations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 真人口径（09-06 用户拍板"要实际真的"）：
    # human_uv/human_pv = UA 真实浏览器且打开过页面的来源/页面；
    # machine_uv = 伪装扫描器剔除数；single_uv = 单次来源(无法判定)。
    human_uv: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    human_pv: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    machine_uv: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    single_uv: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
