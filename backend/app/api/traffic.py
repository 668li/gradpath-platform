"""流量看板 API（admin-only）— t_traffic_daily 只读聚合。

数据由宿主侧 monitoring/traffic_pipeline.sh 每日 21:50 幂等 upsert，
本 API 不做任何计算以外的写操作。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.database import get_db
from app.models.traffic_daily import TrafficDaily
from app.schemas.traffic import TrafficDailyVO, TrafficDayVO

router = APIRouter(prefix="/api/traffic", tags=["traffic"])


@router.get("/daily", response_model=TrafficDailyVO)
def daily(
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
    _admin: object = Depends(get_admin_user),
):
    rows = db.query(TrafficDaily).order_by(TrafficDaily.date.desc()).limit(days).all()
    items = sorted(rows, key=lambda r: r.date)
    day_vos = [
        TrafficDayVO(
            date=r.date.isoformat(),
            pv=r.pv,
            uv=r.uv,
            blocked=r.blocked,
            registrations=r.registrations,
            human_uv=r.human_uv,
            human_pv=r.human_pv,
            machine_uv=r.machine_uv,
            single_uv=r.single_uv,
            conversion_rate=(r.registrations / r.uv) if r.uv else 0.0,
        )
        for r in items
    ]
    total_uv = sum(d.uv for d in day_vos)
    total_reg = sum(d.registrations for d in day_vos)
    return TrafficDailyVO(
        days=day_vos,
        summary={
            "total_uv": total_uv,
            "total_pv": sum(d.pv for d in day_vos),
            "total_human_uv": sum(d.human_uv for d in day_vos),
            "total_human_pv": sum(d.human_pv for d in day_vos),
            "total_machine_uv": sum(d.machine_uv for d in day_vos),
            "total_single_uv": sum(d.single_uv for d in day_vos),
            "total_blocked": sum(d.blocked for d in day_vos),
            "total_registrations": total_reg,
            "conversion_rate": (total_reg / total_uv) if total_uv else 0.0,
        },
    )
