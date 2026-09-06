"""流量看板 VO（admin-only 只读）。"""

from pydantic import BaseModel


class TrafficDayVO(BaseModel):
    date: str  # YYYY-MM-DD（北京时间）
    pv: int
    uv: int
    blocked: int
    registrations: int
    conversion_rate: float  # registrations / uv，uv=0 时为 0.0


class TrafficDailyVO(BaseModel):
    days: list[TrafficDayVO]  # 按 date 升序
    summary: dict[str, float]
