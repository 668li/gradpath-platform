"""同路人洞察 API — 创意功能端点。

把平台的真实数据护城河转化为改变信念的洞察：
- GET /api/peer-insights/mirror             同路人镜像（相似群体去向分布 + 上岸率 + 过来人建议）
- GET /api/peer-insights/procrastination    决策拖延成本（量化犹豫的代价）
- GET /api/peer-insights/dark-knowledge-gap 暗知识缺口雷达（你还没看到的关键信息）
- GET /api/peer-insights/regret-lessons     前车之鉴（过来人的后悔与教训）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services import peer_insight_service

router = APIRouter(prefix="/api/peer-insights", tags=["同路人洞察"])


@router.get("/mirror")
def peer_mirror(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """同路人镜像：和你同阶段的人怎么选、结果如何。"""
    return peer_insight_service.get_peer_mirror(db, user.id)


@router.get("/procrastination")
def procrastination_cost(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """决策拖延成本：量化你停留在'计划中'的决策的真实代价。"""
    return peer_insight_service.get_procrastination_cost(db, user.id)


@router.get("/dark-knowledge-gap")
def dark_knowledge_gap(
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """暗知识缺口雷达：你还没看到、但同路人都在看的高重要性暗知识。"""
    return peer_insight_service.get_dark_knowledge_gap(db, user.id, limit=limit)


@router.get("/regret-lessons")
def regret_lessons(
    limit_per_type: int = Query(2, ge=1, le=5),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """前车之鉴：已经走过这条路的人，最后悔什么、最想提醒你什么。"""
    return peer_insight_service.get_regret_lessons(db, limit_per_type=limit_per_type)
