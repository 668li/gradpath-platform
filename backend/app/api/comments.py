"""评论 API。"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import rate_limits
from app.database import get_db
from app.main import limiter
from app.models.comment import Comment
from app.models.experience_post import ExperiencePost
from app.models.user import User
from app.schemas.comment import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
)
from app.services.comment_service import (
    create_comment,
    get_comments_by_post,
    get_replies,
    like_comment,
    soft_delete_comment,
)
from app.api.notifications import create_notification

router = APIRouter(prefix="/api/comments", tags=["评论系统"])


def _comment_to_response(c) -> CommentResponse:
    nickname = "匿名用户"
    if hasattr(c, "author") and c.author:
        nickname = getattr(c.author, "nickname", None) or getattr(c.author, "username", None) or "匿名用户"
    return CommentResponse(
        id=c.id,
        post_id=c.post_id,
        user_id=c.user_id,
        content=c.content,
        parent_id=c.parent_id,
        like_count=c.like_count,
        is_deleted=c.is_deleted,
        author_nickname=nickname,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(rate_limits.COMMENT_CREATE)
def create_comment_endpoint(
    request: Request,
    response: Response,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建评论（需登录）。"""
    try:
        comment = create_comment(
            db,
            user_id=user.id,
            post_id=data.post_id,
            content=data.content,
            parent_id=data.parent_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 通知闭环：评论经验贴 → 通知帖子作者；回复评论 → 通知父评论作者
    try:
        if data.parent_id:
            parent = db.query(Comment).filter(Comment.id == data.parent_id).first()
            if parent and str(parent.user_id) != str(user.id):
                create_notification(
                    db, parent.user_id, type="reply",
                    title="有人回复了你的评论",
                    content=data.content[:80],
                )
        else:
            post = db.query(ExperiencePost).filter(ExperiencePost.id == data.post_id).first()
            if post and str(post.user_id) != str(user.id):
                create_notification(
                    db, post.user_id, type="comment",
                    title="有人评论了你的经验贴",
                    content=data.content[:80],
                )
        db.commit()
    except Exception:
        db.rollback()

    return _comment_to_response(comment)


@router.get("/post/{post_id}", response_model=CommentListResponse)
def list_comments(
    post_id: UUID,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """获取帖子评论列表。"""
    items, total = get_comments_by_post(db, post_id, offset=offset, limit=limit)
    result = []
    for c in items:
        resp = _comment_to_response(c)
        reply_list = get_replies(db, c.id)
        result.append(resp)
    return CommentListResponse(items=result, total=total)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment_endpoint(
    comment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除评论（软删除，仅作者或管理员）。"""
    deleted = soft_delete_comment(db, comment_id, user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    return None


@router.post("/{comment_id}/like")
@limiter.limit(rate_limits.COMMUNITY_LIKE)
def like_comment_endpoint(
    request: Request,
    response: Response,
    comment_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """点赞评论（需登录）。"""
    comment = like_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    return {"message": "点赞成功", "like_count": comment.like_count}
