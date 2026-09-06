"""业务时间工具 — 全部日界逻辑统一走北京日历。

生产 backend 容器时区是 UTC，date.today()/datetime.now() 拿到的是 UTC 日期，
对全部中国用户会把北京时间 0-8 点的行动记到前一天。凡涉及"今天/昨天/周界"的
业务判断一律用 BEIJING_TZ / beijing_today()，不要新增裸 date.today()。
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def beijing_today() -> date:
    """北京日历的今天。"""
    return datetime.now(BEIJING_TZ).date()
