from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.skill import SkillCreate, SkillResponse, SkillUpdate
from app.services.skill_service import (
    create_skill,
    delete_skill,
    get_skill,
    get_skill_stats,
    get_skill_tree,
    update_skill,
)

router = APIRouter(prefix="/api/skills", tags=["技能树"])


class SkillBatchRequest(BaseModel):
    """批量获取技能请求体。"""

    ids: list[str] = Field(
        ..., min_length=1, max_length=100, description="技能 ID 列表（最多 100 个）"
    )


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create(data: SkillCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_skill(db, user.id, data)


@router.get("", response_model=list[SkillResponse])
def list_tree(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_skill_tree(db, user.id)


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_skill_stats(db, user.id)


@router.post("/batch", response_model=list[SkillResponse])
def batch_skills(
    body: SkillBatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量获取技能（消除前端 N+1 调用，仅返回当前用户的技能）。

    前端在技能对比/详情页一次展示 N 个技能时，原需发 N 次
    `/skills/{id}` 请求；本接口一次返回所有技能信息。
    """
    from app.models.skill_node import SkillNode

    # 限制单次最多 100 个，防止滥用
    raw_ids = body.ids[:100]
    parsed_ids: list[UUID] = []
    for raw in raw_ids:
        try:
            parsed_ids.append(UUID(raw))
        except (ValueError, AttributeError):
            continue
    if not parsed_ids:
        return []
    # 安全约束：仅返回当前用户的技能，防止越权
    items = (
        db.query(SkillNode)
        .filter(SkillNode.id.in_(parsed_ids), SkillNode.user_id == user.id)
        .all()
    )
    return [SkillResponse.model_validate(s) for s in items]


@router.get("/{skill_id}", response_model=SkillResponse)
def get_one(skill_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_skill(db, user.id, skill_id)


@router.patch("/{skill_id}", response_model=SkillResponse)
def update(skill_id: UUID, data: SkillUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_skill(db, user.id, skill_id, data)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(skill_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_skill(db, user.id, skill_id)
