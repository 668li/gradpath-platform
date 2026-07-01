# backend/app/services/career_plan_service.py
"""职业规划服务层 — Phase 11。

提供用户职业规划的列表、详情与里程碑状态更新。
"""
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.career_plan import CareerPlan


def list_plans(db: Session, user_id: UUID) -> list[CareerPlan]:
    """列出用户的规划（按创建时间倒序）。"""
    return (
        db.query(CareerPlan)
        .filter(CareerPlan.user_id == user_id)
        .order_by(CareerPlan.created_at.desc())
        .all()
    )


def get_plan(db: Session, user_id: UUID, plan_id: UUID) -> CareerPlan | None:
    """获取规划详情（验证所有权）。"""
    return (
        db.query(CareerPlan)
        .filter(CareerPlan.id == plan_id, CareerPlan.user_id == user_id)
        .first()
    )


def update_milestone(
    db: Session, user_id: UUID, plan_id: UUID, milestone_idx: int, status: str
) -> CareerPlan | None:
    """更新里程碑状态。

    Args:
        milestone_idx: 里程碑在 milestones 列表中的索引（从 0 开始）
        status: 新状态（pending/in_progress/done）

    Returns:
        更新后的 CareerPlan，若规划不存在或索引越界则返回 None
    """
    plan = get_plan(db, user_id, plan_id)
    if not plan:
        return None

    milestones = plan.milestones or []
    if milestone_idx < 0 or milestone_idx >= len(milestones):
        return None

    # 构建新的里程碑列表（深拷贝以避免原地修改不被追踪）
    new_milestones = []
    for i, m in enumerate(milestones):
        if i == milestone_idx:
            new_m = dict(m) if isinstance(m, dict) else m
            if isinstance(new_m, dict):
                new_m["status"] = status
            new_milestones.append(new_m)
        else:
            new_milestones.append(m)

    plan.milestones = new_milestones
    flag_modified(plan, "milestones")
    db.commit()
    db.refresh(plan)
    return plan
