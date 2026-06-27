from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.skill_node import SkillNode
from app.schemas.skill import SkillCreate, SkillUpdate


def create_skill(db: Session, user_id: UUID, data: SkillCreate) -> SkillNode:
    if data.parent_id:
        parent = (
            db.query(SkillNode)
            .filter(SkillNode.id == data.parent_id, SkillNode.user_id == user_id)
            .first()
        )
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="父技能不存在")
        if data.parent_id == parent.id:
            pass  # OK
    skill = SkillNode(user_id=user_id, **data.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def get_skill_tree(db: Session, user_id: UUID) -> list[SkillNode]:
    roots = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == user_id, SkillNode.parent_id.is_(None))
        .all()
    )
    return roots


def get_skill(db: Session, user_id: UUID, skill_id: UUID) -> SkillNode:
    skill = (
        db.query(SkillNode)
        .filter(SkillNode.id == skill_id, SkillNode.user_id == user_id)
        .first()
    )
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="技能不存在")
    return skill


def update_skill(db: Session, user_id: UUID, skill_id: UUID, data: SkillUpdate) -> SkillNode:
    skill = get_skill(db, user_id, skill_id)
    update_data = data.model_dump(exclude_unset=True)
    if "parent_id" in update_data and update_data["parent_id"] == skill_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能将自己设为父技能")
    for key, value in update_data.items():
        setattr(skill, key, value)
    db.commit()
    db.refresh(skill)
    return skill


def delete_skill(db: Session, user_id: UUID, skill_id: UUID) -> None:
    skill = get_skill(db, user_id, skill_id)
    db.delete(skill)
    db.commit()


def get_skill_stats(db: Session, user_id: UUID) -> dict[str, int]:
    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    stats: dict[str, int] = {}
    for s in skills:
        stats[s.category] = stats.get(s.category, 0) + 1
    return stats
