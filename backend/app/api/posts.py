"""讨论帖 API 路由。"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.post import (
    PostCreate,
    PostListResponse,
    PostResponse,
    PostUpdate,
)
from app.services.post_service import (
    create_post,
    delete_post,
    list_posts,
    update_post,
)

router = APIRouter(prefix="/api/posts", tags=["讨论帖"])


@router.get("", response_model=PostListResponse)
def list(
    topic_type: str = Query(...),
    topic_key: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_posts(db, topic_type, topic_key, page, page_size)


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create(
    body: PostCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_post(db, user, body)


@router.put("/{post_id}", response_model=PostResponse)
def update(
    post_id: str,
    body: PostUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_post(db, user, post_id, body)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    post_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_post(db, user, post_id)
