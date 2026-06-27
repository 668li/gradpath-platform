from uuid import UUID

from fastapi import APIRouter, Depends, status
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


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create(data: SkillCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_skill(db, user.id, data)


@router.get("", response_model=list[SkillResponse])
def list_tree(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_skill_tree(db, user.id)


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_skill_stats(db, user.id)


@router.get("/{skill_id}", response_model=SkillResponse)
def get_one(skill_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_skill(db, user.id, skill_id)


@router.patch("/{skill_id}", response_model=SkillResponse)
def update(skill_id: UUID, data: SkillUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_skill(db, user.id, skill_id, data)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(skill_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_skill(db, user.id, skill_id)
