"""成长档案中心 API — 全量做实（鉴权 + 幂等）。

路径与 DTO 对齐系统设计 §3.2.M3.2 接口清单；
user_id 一律由登录态 token 推断（get_current_user），不在请求体传。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.growth import (
    GrowthArchiveVO,
    GrowthStatsVO,
    GrowthTrajectoryCreateRequest,
    GrowthTrajectoryListVO,
    GrowthTrajectoryVO,
)
from app.services import growth_service

router = APIRouter(prefix="/api/growth", tags=["成长档案中心"])


@router.get("/trajectory", response_model=GrowthTrajectoryListVO)
def list_growth_trajectory(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取成长轨迹时间轴。"""
    items, total = growth_service.list_trajectory(db, user.id)
    return GrowthTrajectoryListVO(
        items=[growth_service.to_trajectory_vo(t) for t in items], total=total
    )


@router.post("/trajectory", response_model=GrowthTrajectoryVO)
def create_growth_trajectory(
    body: GrowthTrajectoryCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """记录成长轨迹事件（幂等：source_event_id 唯一索引，重复丢弃）。"""
    traj = growth_service.create_trajectory(db, user.id, body)
    return growth_service.to_trajectory_vo(traj)


@router.get("/archive", response_model=GrowthArchiveVO)
def get_growth_archive(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取档案聚合（缺失时自动聚合生成）。"""
    archive = growth_service.get_growth_archive(db, user.id)
    return growth_service.to_archive_vo(archive)


@router.put("/archive/refresh", response_model=GrowthArchiveVO)
def refresh_growth_archive(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动触发档案聚合刷新（当前用户，消除越权）。"""
    archive = growth_service.refresh_growth_archive(db, user.id)
    return growth_service.to_archive_vo(archive)


@router.get("/stats", response_model=GrowthStatsVO)
def get_growth_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取行动完成率与 Streak 统计（实时跨表聚合）。"""
    return GrowthStatsVO(**growth_service.get_growth_stats(db, user.id))
