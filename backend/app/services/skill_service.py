from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.models.skill_node import SkillNode
from app.schemas.skill import SkillCreate, SkillUpdate


def _invalidate_user_context_cache(user_id: UUID) -> None:
    """技能 CRUD 后失效用户上下文缓存（build_user_context 依赖 SkillNode）。"""
    for key in (
        f"user_context:{user_id}",
        f"skill_tree:{user_id}",
        f"skill_stats:{user_id}",
    ):
        try:
            cache.delete(key)
        except Exception:
            pass


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
    _invalidate_user_context_cache(user_id)
    return skill


def get_skill_tree(db: Session, user_id: UUID) -> list[SkillNode]:
    # 注意：ORM 对象不可安全序列化到 Redis（json.dumps 会 stringify），
    # 因此不对 skill_tree 做缓存。stats 和 overview 返回 dict 可安全缓存。
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
    _invalidate_user_context_cache(user_id)
    return skill


def delete_skill(db: Session, user_id: UUID, skill_id: UUID) -> None:
    skill = get_skill(db, user_id, skill_id)
    db.delete(skill)
    db.commit()
    _invalidate_user_context_cache(user_id)


def get_skill_stats(db: Session, user_id: UUID) -> dict[str, int]:
    cache_key = f"skill_stats:{user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    from sqlalchemy import func
    rows = (
        db.query(SkillNode.category, func.count(SkillNode.id))
        .filter(SkillNode.user_id == user_id)
        .group_by(SkillNode.category)
        .all()
    )
    stats = {cat: cnt for cat, cnt in rows}
    cache.set(cache_key, stats, ttl=60)
    return stats
