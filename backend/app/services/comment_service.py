"""评论服务层。"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.models.comment import Comment
from app.models.experience_post import ExperiencePost
from app.models.notification import Notification, NotificationType


def _atomic_increment(
    db: Session, model_cls, item_id: UUID, column: str, delta: int = 1
) -> bool:
    """原子 UPDATE — 避免 read-modify-write 在高并发下丢失更新。

    SQL: UPDATE <table> SET <column> = <column> + :delta WHERE id = :id
    """
    col = getattr(model_cls, column)
    rows = (
        db.query(model_cls)
        .filter(model_cls.id == item_id)
        .update({col: col + delta})
    )
    return rows > 0


def create_comment(
    db: Session,
    user_id: UUID,
    post_id: UUID,
    content: str,
    parent_id: Optional[UUID] = None,
) -> Comment:
    """创建评论。"""
    post = db.query(ExperiencePost).filter(ExperiencePost.id == post_id).first()
    if not post:
        raise ValueError("帖子不存在")
    if parent_id:
        parent = db.query(Comment).filter(Comment.id == parent_id, Comment.is_deleted == False).first()
        if not parent or parent.post_id != post_id:
            raise ValueError("父评论不存在")
    comment = Comment(
        user_id=user_id,
        post_id=post_id,
        content=content,
        parent_id=parent_id,
    )
    db.add(comment)
    # C3: 原子 UPDATE 替换 post.comment_count += 1，避免高并发丢失更新
    _atomic_increment(db, ExperiencePost, post_id, "comment_count", 1)
    db.commit()
    db.refresh(comment)
    # 同步内存中的 post 对象（用于后续通知逻辑读取 post.title）
    db.refresh(post)

    # 触发通知：帖子作者收到新评论提醒（自己评论自己不通知）
    if post.user_id != user_id:
        db.add(
            Notification(
                user_id=post.user_id,
                type=NotificationType.comment,
                title="收到新评论",
                content=f"你的帖子《{post.title[:30]}》收到了一条新评论",
                link=f"/kaoyan/community/posts/{post_id}",
            )
        )
    # 嵌套回复：父评论作者收到回复提醒（自己回复自己不通知）
    if parent_id and parent and parent.user_id != user_id:
        db.add(
            Notification(
                user_id=parent.user_id,
                type=NotificationType.reply,
                title="收到回复",
                content=f"你的评论收到了一条回复：{content[:30]}",
                link=f"/kaoyan/community/posts/{post_id}",
            )
        )
    db.commit()

    return comment


def get_comments_by_post(
    db: Session,
    post_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Comment], int]:
    """获取帖子的评论列表（顶层 + 各自的回复）。"""
    total = (
        db.query(Comment)
        .filter(Comment.post_id == post_id, Comment.is_deleted == False, Comment.parent_id.is_(None))
        .count()
    )
    items = (
        db.query(Comment)
        .options(selectinload(Comment.author), selectinload(Comment.replies))
        .filter(Comment.post_id == post_id, Comment.is_deleted == False, Comment.parent_id.is_(None))
        .order_by(Comment.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_replies(db: Session, parent_id: UUID) -> list[Comment]:
    """获取某条评论的回复。"""
    return (
        db.query(Comment)
        .options(selectinload(Comment.author))
        .filter(Comment.parent_id == parent_id, Comment.is_deleted == False)
        .order_by(Comment.created_at.asc())
        .all()
    )


def soft_delete_comment(db: Session, comment_id: UUID, user_id: UUID) -> bool:
    """软删除评论（仅作者或管理员）。"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment or comment.is_deleted:
        return False
    comment.is_deleted = True
    db.commit()
    return True


def like_comment(db: Session, comment_id: UUID) -> Optional[Comment]:
    """点赞评论。"""
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.is_deleted == False).first()
    if not comment:
        return None
    # C3: 原子 UPDATE 替换 comment.like_count += 1
    _atomic_increment(db, Comment, comment_id, "like_count", 1)
    db.commit()
    db.refresh(comment)
    return comment
