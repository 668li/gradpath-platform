"""流量看板 VO（admin-only 只读）。"""

from pydantic import BaseModel


class TrafficDayVO(BaseModel):
    date: str  # YYYY-MM-DD（北京时间）
    pv: int
    uv: int
    blocked: int
    registrations: int
    human_uv: int  # 真人来源（UA 真实浏览器+打开过页面）
    human_pv: int  # 真人页面浏览
    machine_uv: int  # 剔除的脚本/扫描来源
    single_uv: int  # 单次来源（无法判定真人/脚本）
    conversion_rate: float  # registrations / uv，uv=0 时为 0.0


class TrafficDailyVO(BaseModel):
    days: list[TrafficDayVO]  # 按 date 升序
    summary: dict[str, float]
