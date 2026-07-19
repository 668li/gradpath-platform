"""成长模式智能 API — 历史数据分析 + 预测校准 + 快照持久化。"""
from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.growth_snapshot import GrowthSnapshot
from app.models.user import User
from app.services import growth_pattern_service

router = APIRouter(prefix="/api/growth-patterns", tags=["成长模式智能"])


@router.get("/analyze")
def analyze_patterns(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """分析用户历史数据，发现成长模式，并落库为月度快照。"""
    result = growth_pattern_service.analyze_patterns(db, user.id)
    patterns = result.get("patterns", []) if isinstance(result, dict) else []
    # 计算成长得分：模式数 + 数据完整度启发式
    score = min(100, len(patterns) * 18 + result.get("data_points", {}).get("skill_count", 0) if isinstance(result, dict) else 0)

    period = datetime.now(timezone.utc).strftime("%Y-%m")
    # 同月只保留最新快照
    db.query(GrowthSnapshot).filter(
        GrowthSnapshot.user_id == user.id, GrowthSnapshot.period == period
    ).delete(synchronize_session=False)

    snap = GrowthSnapshot(
        user_id=user.id,
        period=period,
        growth_score=int(score),
        pattern_count=len(patterns),
        snapshot=json.dumps(result if isinstance(result, dict) else {"raw": str(result)}, ensure_ascii=False),
    )
    db.add(snap)
    db.commit()
    return {**result, "growth_score": int(score), "snapshot_saved": True} if isinstance(result, dict) else result


@router.get("/history")
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回该用户的成长快照历史（按时间升序），用于跨期对比。"""
    snaps = (
        db.query(GrowthSnapshot)
        .filter(GrowthSnapshot.user_id == user.id)
        .order_by(GrowthSnapshot.created_at.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": str(s.id),
                "period": s.period,
                "growth_score": s.growth_score,
                "pattern_count": s.pattern_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in snaps
        ]
    }
