"""学习资源 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.learning_resource import LearningResource
from app.schemas.learning_resource import (
    LearningResourceCreate,
    LearningResourceUpdate,
    LearningResourceResponse,
)

router = APIRouter(prefix="/api/learning-resources", tags=["学习资源"])


@router.post("/", response_model=LearningResourceResponse)
def create_resource(
    resource: LearningResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建学习资源"""
    db_resource = LearningResource(**resource.model_dump(), user_id=current_user.id)
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource


@router.get("/", response_model=list[LearningResourceResponse])
def list_resources(
    skip: int = 0,
    limit: int = 100,
    subject: str | None = None,
    difficulty: str | None = None,
    resource_type: str | None = None,
    db: Session = Depends(get_db),
):
    """获取学习资源列表（支持筛选）"""
    query = db.query(LearningResource)
    
    if subject:
        query = query.filter(LearningResource.subject == subject)
    if difficulty:
        query = query.filter(LearningResource.difficulty == difficulty)
    if resource_type:
        query = query.filter(LearningResource.resource_type == resource_type)
    
    return query.offset(skip).limit(limit).all()


@router.get("/seed-system", response_model=dict)
def seed_system_resources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """灌入系统推荐学习资源（首次运行生效，重复调用幂等）。"""
    from app.crawlers.real_data.learning_resource_seed import seed

    n = seed(str(current_user.id))
    return {"seeded": n, "message": f"已灌入 {n} 条系统资源" if n else "已存在系统资源，跳过"}


@router.get("/{resource_id}", response_model=LearningResourceResponse)
def get_resource(
    resource_id: UUID,
    db: Session = Depends(get_db),
):
    """获取单个学习资源"""
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    
    # 增加浏览次数
    resource.view_count += 1
    db.commit()
    db.refresh(resource)
    return resource


@router.put("/{resource_id}", response_model=LearningResourceResponse)
def update_resource(
    resource_id: UUID,
    resource_update: LearningResourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新学习资源"""
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    if resource.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改")
    
    update_data = resource_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(resource, key, value)
    
    db.commit()
    db.refresh(resource)
    return resource


@router.delete("/{resource_id}")
def delete_resource(
    resource_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除学习资源"""
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    if resource.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除")
    
    db.delete(resource)
    db.commit()
    return {"message": "资源已删除"}
