"""考研经验贴服务层 — 社区交流系统。"""

import logging
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.cursor_pagination import apply_cursor_filter, encode_cursor
from app.models.experience_post import ExperiencePost

logger = logging.getLogger(__name__)


def _atomic_increment(db: Session, model_cls, item_id: UUID, column: str, delta: int = 1) -> bool:
    """原子 UPDATE — 避免 read-modify-write 在高并发下丢失更新。"""
    col = getattr(model_cls, column)
    rows = db.query(model_cls).filter(model_cls.id == item_id).update({col: col + delta})
    return rows > 0


STATUS_CHOICES = {"pending", "approved", "rejected"}

# 主题相关度门禁（S1）：对普通用户隐藏 is_off_topic=True 的内容。
# 管理员显式请求（status 参数）或 include_unapproved 分支不走此过滤。
PUBLIC_OFF_TOPIC_FILTER = ~ExperiencePost.is_off_topic.is_(True)


def create_experience_post(
    db: Session,
    user_id: UUID,
    data: dict,
) -> ExperiencePost:
    """创建经验贴（默认待审核）。"""
    post = ExperiencePost(
        user_id=user_id,
        title=data["title"],
        summary=data.get("summary"),
        content=data["content"],
        tags=data.get("tags") or [],
        category=data.get("category", "general"),
        is_anonymous=data.get("is_anonymous", False),
        # 来源归属是服务端事实，不由客户端声明（对抗审查 B：schema 里
        # source_platform 客户端可控，可伪造 external/verified 供应链）
        source_platform="user",
        source_url=data.get("source_url"),
        status="pending",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_experience_post(
    db: Session, post_id: UUID, include_unapproved: bool = False
) -> ExperiencePost | None:
    """获取单个经验贴。安全修复 M1: 默认只返回已审核通过的帖子。"""
    query = db.query(ExperiencePost).filter(ExperiencePost.id == post_id)
    if not include_unapproved:
        query = query.filter(ExperiencePost.status == "approved")
        query = query.filter(PUBLIC_OFF_TOPIC_FILTER)
    return query.first()


def get_experience_posts(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
    tag: str | None = None,
    status: str | None = None,
    search: str | None = None,
    source_platform: str | None = None,
) -> tuple[list[ExperiencePost], int]:
    """获取经验贴列表（支持筛选）。

    默认只返回 approved 状态的内容；传入 status 可覆盖。
    传入 source_platform 可过滤来源平台："user" 表示用户发布，其他值表示外部爬取。
    """
    query = db.query(ExperiencePost)

    if status:
        query = query.filter(ExperiencePost.status == status)
    else:
        query = query.filter(ExperiencePost.status == "approved")
        query = query.filter(PUBLIC_OFF_TOPIC_FILTER)

    if source_platform == "user":
        query = query.filter(
            (ExperiencePost.source_platform == "user") | (ExperiencePost.source_platform.is_(None))
        )
    elif source_platform == "external":
        query = query.filter(
            (ExperiencePost.source_platform.isnot(None))
            & (ExperiencePost.source_platform != "user")
        )
    elif source_platform is None:
        query = query.filter(
            (ExperiencePost.source_platform == "user") | (ExperiencePost.source_platform.is_(None))
        )
    else:
        # 支持按具体来源平台过滤（如 trae_forum / crawler / xiaohongshu / v2ex）
        query = query.filter(ExperiencePost.source_platform == source_platform)

    if category:
        query = query.filter(ExperiencePost.category == category)
    if tag:
        query = query.filter(ExperiencePost.tags.contains([tag]))
    if search:
        query = query.filter(
            or_(
                ExperiencePost.title.ilike(f"%{search}%"),
                ExperiencePost.summary.ilike(f"%{search}%"),
                ExperiencePost.content.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    posts = (
        query.order_by(ExperiencePost.is_pinned.desc(), ExperiencePost.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return posts, total


def get_experience_posts_cursor(
    db: Session,
    *,
    page_size: int = 20,
    cursor: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    status: str | None = None,
    search: str | None = None,
    source_platform: str | None = None,
) -> tuple[list[ExperiencePost], str | None, bool]:
    """游标分页获取经验贴列表。

    Returns:
        (items, next_cursor, has_more)
    """
    query = db.query(ExperiencePost)

    if status:
        query = query.filter(ExperiencePost.status == status)
    else:
        query = query.filter(ExperiencePost.status == "approved")
        query = query.filter(PUBLIC_OFF_TOPIC_FILTER)

    if source_platform == "user":
        query = query.filter(
            (ExperiencePost.source_platform == "user") | (ExperiencePost.source_platform.is_(None))
        )
    elif source_platform == "external":
        query = query.filter(
            (ExperiencePost.source_platform.isnot(None))
            & (ExperiencePost.source_platform != "user")
        )
    elif source_platform is None:
        query = query.filter(
            (ExperiencePost.source_platform == "user") | (ExperiencePost.source_platform.is_(None))
        )
    else:
        # 支持按具体来源平台过滤（如 trae_forum / crawler / xiaohongshu / v2ex）
        query = query.filter(ExperiencePost.source_platform == source_platform)

    if category:
        query = query.filter(ExperiencePost.category == category)
    if tag:
        query = query.filter(ExperiencePost.tags.contains([tag]))
    if search:
        query = query.filter(
            or_(
                ExperiencePost.title.ilike(f"%{search}%"),
                ExperiencePost.summary.ilike(f"%{search}%"),
                ExperiencePost.content.ilike(f"%{search}%"),
            )
        )

    query = apply_cursor_filter(
        query,
        cursor,
        time_col=ExperiencePost.created_at,
        id_col=ExperiencePost.id,
    )

    query = query.order_by(ExperiencePost.is_pinned.desc(), ExperiencePost.created_at.desc())

    items = query.limit(page_size + 1).all()
    has_more = len(items) > page_size
    if has_more:
        items = items[:page_size]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.created_at, str(last.id))

    return items, next_cursor, has_more


def update_experience_post(
    db: Session,
    post_id: UUID,
    data: dict,
) -> ExperiencePost | None:
    """更新经验贴（作者/管理员对自身或待审帖操作，需 include_unapproved 直查）。"""
    post = get_experience_post(db, post_id, include_unapproved=True)
    if not post:
        return None

    for field in (
        "title",
        "summary",
        "content",
        "tags",
        "category",
        "is_anonymous",
        "source_url",
    ):
        if field in data and data[field] is not None:
            setattr(post, field, data[field])

    db.commit()
    db.refresh(post)
    return post


def delete_experience_post(db: Session, post_id: UUID) -> bool:
    """删除经验贴（作者/管理员删除自身或待审帖，需 include_unapproved 直查）。"""
    post = get_experience_post(db, post_id, include_unapproved=True)
    if not post:
        return False
    db.delete(post)
    db.commit()
    return True


def increment_experience_post_view(db: Session, post_id: UUID) -> bool:
    """增加经验贴浏览数。"""
    # C3: 原子 UPDATE 替换 post.view_count += 1
    return _atomic_increment(db, ExperiencePost, post_id, "view_count", 1) and (db.commit() or True)


def like_experience_post(db: Session, post_id: UUID) -> ExperiencePost | None:
    """点赞经验贴。"""
    post = get_experience_post(db, post_id)
    if not post:
        return None
    # C3: 原子 UPDATE 替换 post.like_count += 1
    _atomic_increment(db, ExperiencePost, post_id, "like_count", 1)
    db.commit()
    db.refresh(post)
    return post


def approve_experience_post(db: Session, post_id: UUID) -> ExperiencePost | None:
    """审核通过经验贴。

    修复（成熟化 A3）：此前经 get_experience_post（默认只查 approved）
    导致对 pending 帖 approve/reject 返回 404 —— 审核对象恰是待审帖。
    现在直查任意状态。
    """
    post = get_experience_post(db, post_id, include_unapproved=True)
    if not post:
        return None
    post.status = "approved"
    db.commit()
    db.refresh(post)
    return post


def reject_experience_post(db: Session, post_id: UUID) -> ExperiencePost | None:
    """拒绝经验贴（同上修复：直查任意状态）。"""
    post = get_experience_post(db, post_id, include_unapproved=True)
    if not post:
        return None
    post.status = "rejected"
    db.commit()
    db.refresh(post)
    return post


def set_experience_post_pin(db: Session, post_id: UUID, pinned: bool) -> ExperiencePost | None:
    """置顶/取消置顶经验贴（管理员）。"""
    post = get_experience_post(db, post_id, include_unapproved=True)
    if not post:
        return None
    post.is_pinned = pinned
    db.commit()
    db.refresh(post)
    return post
