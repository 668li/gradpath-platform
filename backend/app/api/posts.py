"""讨论帖 API 路由。"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.follow import Follow
from app.models.user import User
from app.schemas.post import (
    PostCreate,
    PostListResponse,
    PostQuery,
    PostResponse,
    PostUpdate,
)
from app.services.post_service import (
    create_post,
    delete_post,
    list_posts,
    list_public_posts,
    update_post,
)
from app.api.notifications import create_notification

router = APIRouter(prefix="/api/posts", tags=["讨论帖"])


@router.get("/public", response_model=PostListResponse)
def list_public(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    topic_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """公开信息流（社区广场），无需登录。"""
    return list_public_posts(db, page, page_size, topic_type)


@router.get("", response_model=PostListResponse)
def list(
    topic_type: str = Query(...),
    topic_key: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_posts(db, topic_type, topic_key, page, page_size)


@router.post("/list", response_model=PostListResponse)
def list_by_body(
    body: PostQuery,
    db: Session = Depends(get_db),
):
    """POST 方式查询帖子列表（避免 URL 编码中文参数问题）。"""
    return list_posts(db, body.topic_type, body.topic_key, body.page, body.page_size)


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create(
    body: PostCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resp = create_post(db, user, body)
    # 通知粉丝：有新帖子
    try:
        followers = (
            db.query(Follow)
            .filter(Follow.followee_id == str(user.id))
            .all()
        )
        for f in followers:
            create_notification(
                db,
                f.follower_id,
                type="new_post",
                title="你关注的人发了新帖",
                content=body.content[:80],
            )
        db.commit()
    except Exception:
        db.rollback()
    return resp


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
