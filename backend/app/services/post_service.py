"""讨论帖服务层 — 发帖、回复、编辑、删除、列表查询。"""
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.models.post import Post, PostTopicType
from app.models.user import User
from app.schemas.post import PostCreate, PostListResponse, PostResponse, PostUpdate


def _to_response(post: Post, author: User | None = None) -> PostResponse:
    """将 Post ORM 对象转为 PostResponse，附带作者信息。"""
    author_name = author.name if author else "未知用户"
    replies = [
        _to_reply_dict(r) for r in sorted(post.replies, key=lambda x: x.created_at)
    ]
    return PostResponse(
        id=str(post.id),
        topic_type=post.topic_type.value if hasattr(post.topic_type, "value") else post.topic_type,
        topic_key=post.topic_key,
        title=post.title,
        content=post.content,
        author_id=str(post.user_id),
        author_name=author_name,
        parent_id=str(post.parent_id) if post.parent_id else None,
        created_at=post.created_at,
        updated_at=post.updated_at,
        replies=replies,
    )


def _to_reply_dict(reply: Post) -> dict:
    """将回复帖转为 dict（不含嵌套 replies）。"""
    return {
        "id": str(reply.id),
        "topic_type": reply.topic_type.value if hasattr(reply.topic_type, "value") else reply.topic_type,
        "topic_key": reply.topic_key,
        "content": reply.content,
        "author_id": str(reply.user_id),
        "author_name": "回复者",
        "parent_id": str(reply.parent_id) if reply.parent_id else None,
        "created_at": reply.created_at,
        "updated_at": reply.updated_at,
        "replies": [],
    }


def _resolve_author_name(db: Session, user_id: UUID) -> str:
    """查询用户名。"""
    user = db.query(User).filter(User.id == user_id).first()
    return user.name if user else "未知用户"


def list_posts(
    db: Session,
    topic_type: str,
    topic_key: str,
    page: int = 1,
    page_size: int = 20,
) -> PostListResponse:
    """按主题查询顶层帖列表，每帖附带回复。"""
    try:
        tt = PostTopicType(topic_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的 topic_type: {topic_type}",
        )

    base_q = db.query(Post).filter(
        Post.topic_type == tt,
        Post.topic_key == topic_key,
        Post.parent_id.is_(None),
    )
    total = base_q.count()
    offset = (page - 1) * page_size
    top_posts = (
        base_q.options(selectinload(Post.replies))
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # 批量查询作者名
    user_ids = {p.user_id for p in top_posts}
    for p in top_posts:
        user_ids.update(r.user_id for r in p.replies)
    users = (
        db.query(User).filter(User.id.in_(list(user_ids))).all()
        if user_ids else []
    )
    user_map = {u.id: u.name for u in users}

    items = []
    for p in top_posts:
        resp = _to_response(p)
        resp.author_name = user_map.get(p.user_id, "未知用户")
        for r in resp.replies:
            r.author_name = user_map.get(
                uuid.UUID(r.author_id), "未知用户"
            )
        items.append(resp)

    return PostListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


def create_post(db: Session, user: User, data: PostCreate) -> PostResponse:
    """发帖或回复。"""
    try:
        tt = PostTopicType(data.topic_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的 topic_type: {data.topic_type}",
        )

    parent_id: UUID | None = None
    if data.parent_id:
        try:
            parent_id = uuid.UUID(data.parent_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无效的 parent_id 格式",
            )
        parent = db.query(Post).filter(Post.id == parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="父帖不存在",
            )
        if parent.topic_type != tt or parent.topic_key != data.topic_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="回复帖的 topic_type 和 topic_key 必须与父帖一致",
            )
        if parent.parent_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="不支持多级回复，只能回复顶层帖",
            )

    post = Post(
        topic_type=tt,
        topic_key=data.topic_key,
        title=data.title,
        content=data.content,
        user_id=user.id,
        parent_id=parent_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    resp = _to_response(post, user)
    return resp


def update_post(
    db: Session, user: User, post_id: str, data: PostUpdate
) -> PostResponse:
    """编辑帖子内容（仅作者）。"""
    try:
        pid = uuid.UUID(post_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在"
        )

    post = db.query(Post).filter(Post.id == pid).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在"
        )
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能编辑自己的帖子",
        )

    post.content = data.content
    db.commit()
    db.refresh(post)

    author_name = _resolve_author_name(db, post.user_id)
    resp = _to_response(post)
    resp.author_name = author_name
    return resp


def delete_post(db: Session, user: User, post_id: str) -> None:
    """删除帖子（仅作者）。顶层帖级联删除所有回复。"""
    try:
        pid = uuid.UUID(post_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在"
        )

    post = db.query(Post).filter(Post.id == pid).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在"
        )
    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能删除自己的帖子",
        )

    db.delete(post)
    db.commit()


def list_public_posts(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    topic_type: str | None = None,
) -> PostListResponse:
    """公开信息流：跨主题的最新顶层帖（社区广场）。"""
    q = db.query(Post).filter(Post.parent_id.is_(None))
    if topic_type:
        try:
            q = q.filter(Post.topic_type == PostTopicType(topic_type))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效的 topic_type: {topic_type}",
            )
    total = q.count()
    offset = (page - 1) * page_size
    top_posts = (
        q.order_by(Post.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    user_ids = {p.user_id for p in top_posts}
    users = (
        db.query(User).filter(User.id.in_(list(user_ids))).all()
        if user_ids else []
    )
    user_map = {u.id: (u.nickname or u.username or u.name) for u in users}

    items = []
    for p in top_posts:
        resp = _to_response(p)
        resp.author_name = user_map.get(p.user_id, "未知用户")
        items.append(resp)

    return PostListResponse(
        items=items, total=total, page=page, page_size=page_size
    )
