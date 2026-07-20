"""讨论帖 API 路由。"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from app.core.cursor_pagination import apply_cursor_filter, encode_cursor
from app.core.deps import get_current_user
from app.database import get_db
from app.models.follow import Follow
from app.models.post import Post, PostTopicType
from app.models.user import User
from app.schemas.common import CursorPaginatedResponse
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


class PostBatchRequest(BaseModel):
    """批量获取帖子请求体。"""

    ids: list[str] = Field(
        ..., min_length=1, max_length=100, description="帖子 ID 列表（最多 100 个）"
    )


@router.get("/public", response_model=PostListResponse)
def list_public(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    topic_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """公开信息流（社区广场），无需登录。"""
    return list_public_posts(db, page, page_size, topic_type)


@router.get("/public/cursor", response_model=CursorPaginatedResponse[PostResponse])
def list_public_cursor(
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    cursor: Optional[str] = Query(None, description="游标（cursor 分页）"),
    topic_type: str | None = Query(None, description="主题类型过滤"),
    db: Session = Depends(get_db),
):
    """游标分页获取公开信息流（适合无限滚动，避免深页性能退化）。"""
    query = db.query(Post).filter(Post.parent_id.is_(None))
    if topic_type:
        try:
            query = query.filter(Post.topic_type == PostTopicType(topic_type))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效的 topic_type: {topic_type}",
            )
    query = apply_cursor_filter(
        query, cursor, time_col=Post.created_at, id_col=Post.id
    )
    items = (
        query.options(selectinload(Post.replies))
        .order_by(Post.created_at.desc())
        .limit(page_size + 1)
        .all()
    )
    has_more = len(items) > page_size
    if has_more:
        items = items[:page_size]
    next_cursor = encode_cursor(items[-1].created_at, str(items[-1].id)) if has_more and items else None
    # 批量查询作者名（与 list_public_posts 一致），避免 PostResponse 校验失败
    user_ids = {p.user_id for p in items}
    users = (
        db.query(User).filter(User.id.in_(list(user_ids))).all()
        if user_ids else []
    )
    user_map = {u.id: (u.nickname or u.username or u.name) for u in users}
    from app.services.post_service import _to_response
    resp_items = []
    for p in items:
        resp = _to_response(p)
        resp.author_name = user_map.get(p.user_id, "未知用户")
        resp_items.append(resp)
    return CursorPaginatedResponse(
        items=resp_items,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("", response_model=PostListResponse)
def list_posts_endpoint(
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


@router.post("/batch", response_model=list[PostResponse])
def batch_posts(
    body: PostBatchRequest,
    db: Session = Depends(get_db),
):
    """批量获取帖子（消除前端 N+1 调用，最多 100 个）。

    前端在主题详情页一次展示 N 个帖子时，原需发 N 次 `/posts/{id}` 请求；
    本接口一次返回所有帖子信息。
    """
    raw_ids = body.ids[:100]
    parsed_ids: list[UUID] = []
    for raw in raw_ids:
        try:
            parsed_ids.append(UUID(raw))
        except (ValueError, AttributeError):
            continue
    if not parsed_ids:
        return []
    items = (
        db.query(Post)
        .options(selectinload(Post.replies))
        .filter(Post.id.in_(parsed_ids))
        .all()
    )
    # PostResponse 需要 author_id/author_name，但 Post ORM 没有 author_name 字段。
    # 直接 model_validate 会触发 2 validation errors（缺 author_id/author_name）。
    # 这里与 list_public_cursor 一致：批量查 User，调用 _to_response 填充 author_name。
    user_ids = {p.user_id for p in items}
    users = (
        db.query(User).filter(User.id.in_(list(user_ids))).all()
        if user_ids else []
    )
    user_map = {u.id: (u.nickname or u.username or u.name) for u in users}
    from app.services.post_service import _to_response
    resp_items = []
    for p in items:
        resp = _to_response(p)
        resp.author_name = user_map.get(p.user_id, "未知用户")
        resp_items.append(resp)
    return resp_items


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
