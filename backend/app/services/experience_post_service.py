"""考研经验贴服务层 — 社区交流系统。"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.cursor_pagination import apply_cursor_filter, encode_cursor
from app.models.experience_post import ExperiencePost
from app.models.outcome_report import OutcomeReport, OutcomeType

logger = logging.getLogger(__name__)


def _atomic_increment(
    db: Session, model_cls, item_id: UUID, column: str, delta: int = 1
) -> bool:
    """原子 UPDATE — 避免 read-modify-write 在高并发下丢失更新。"""
    col = getattr(model_cls, column)
    rows = (
        db.query(model_cls)
        .filter(model_cls.id == item_id)
        .update({col: col + delta})
    )
    return rows > 0


STATUS_CHOICES = {"pending", "approved", "rejected"}


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
        source_platform=data.get("source_platform", "user"),
        source_url=data.get("source_url"),
        status="pending",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_experience_post(db: Session, post_id: UUID) -> Optional[ExperiencePost]:
    """获取单个经验贴。"""
    return db.query(ExperiencePost).filter(ExperiencePost.id == post_id).first()


def get_experience_posts(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[ExperiencePost], int]:
    """获取经验贴列表（支持筛选）。

    默认只返回 approved 状态的内容；传入 status 可覆盖。
    """
    query = db.query(ExperiencePost)

    if status:
        query = query.filter(ExperiencePost.status == status)
    else:
        query = query.filter(ExperiencePost.status == "approved")

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
    cursor: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[ExperiencePost], Optional[str], bool]:
    """游标分页获取经验贴列表。

    Returns:
        (items, next_cursor, has_more)
    """
    query = db.query(ExperiencePost)

    if status:
        query = query.filter(ExperiencePost.status == status)
    else:
        query = query.filter(ExperiencePost.status == "approved")

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
) -> Optional[ExperiencePost]:
    """更新经验贴。"""
    post = get_experience_post(db, post_id)
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
    """删除经验贴。"""
    post = get_experience_post(db, post_id)
    if not post:
        return False
    db.delete(post)
    db.commit()
    return True


def increment_experience_post_view(db: Session, post_id: UUID) -> bool:
    """增加经验贴浏览数。"""
    # C3: 原子 UPDATE 替换 post.view_count += 1
    return _atomic_increment(db, ExperiencePost, post_id, "view_count", 1) and (
        db.commit() or True
    )


def like_experience_post(db: Session, post_id: UUID) -> Optional[ExperiencePost]:
    """点赞经验贴。"""
    post = get_experience_post(db, post_id)
    if not post:
        return None
    # C3: 原子 UPDATE 替换 post.like_count += 1
    _atomic_increment(db, ExperiencePost, post_id, "like_count", 1)
    db.commit()
    db.refresh(post)
    return post


def approve_experience_post(db: Session, post_id: UUID) -> Optional[ExperiencePost]:
    """审核通过经验贴。"""
    post = get_experience_post(db, post_id)
    if not post:
        return None
    post.status = "approved"
    db.commit()
    db.refresh(post)
    return post


def reject_experience_post(db: Session, post_id: UUID) -> Optional[ExperiencePost]:
    """拒绝经验贴。"""
    post = get_experience_post(db, post_id)
    if not post:
        return None
    post.status = "rejected"
    db.commit()
    db.refresh(post)
    return post


def create_from_outcome_report(
    db: Session,
    report: OutcomeReport,
) -> Optional[ExperiencePost]:
    """从上岸报告自动生成经验贴草稿（飞轮护城河）。

    设计：
    - 仅当 outcome_type 为 grad_civil_career 或 adjustment 时生成（failed 不生成）
    - 经验贴状态为 pending，需用户审核后发布
    - 自动填充标题、摘要、内容、tags、category
    - 关联 source_url 为 outcome_report 的内部链接

    失败时不阻断上岸报告提交流程，仅记录日志。
    """
    try:
        # 失败的报告不生成经验贴
        if report.outcome_type == OutcomeType.failed:
            return None

        # 构建标题
        school = report.actual_school or report.target_school or "目标院校"
        major = report.actual_major or report.target_major or ""
        title = f"{school} {major} 上岸经验分享".strip()

        # 构建摘要
        summary_parts = []
        if report.score_total:
            summary_parts.append(f"总分 {report.score_total}")
        if report.admission_path:
            path_str = report.admission_path.value if hasattr(report.admission_path, "value") else str(report.admission_path)
            summary_parts.append(f"录取途径: {path_str}")
        if report.satisfaction_after is not None:
            summary_parts.append(f"满意度 {report.satisfaction_after}/5")
        summary = " | ".join(summary_parts) if summary_parts else "上岸经验分享"

        # 构建内容
        content_sections = []
        content_sections.append(f"# {title}\n")
        content_sections.append(f"## 基本信息\n- 目标院校: {report.target_school or '未指定'}\n- 实际院校: {report.actual_school or '未指定'}\n- 目标专业: {report.target_major or '未指定'}\n- 实际专业: {report.actual_major or '未指定'}\n- 年份: {report.year}\n")

        if report.score_total:
            scores = []
            if report.score_politics:
                scores.append(f"政治 {report.score_politics}")
            if report.score_english:
                scores.append(f"英语 {report.score_english}")
            if report.score_major1:
                scores.append(f"专业课1 {report.score_major1}")
            if report.score_major2:
                scores.append(f"专业课2 {report.score_major2}")
            scores_str = " / ".join(scores) if scores else "无明细"
            content_sections.append(f"## 成绩\n- 总分: {report.score_total}\n- 明细: {scores_str}\n")

        if report.what_i_would_do_differently:
            content_sections.append(f"## 如果重来我会这样做\n{report.what_i_would_do_differently}\n")

        if report.advice_for_others:
            content_sections.append(f"## 给学弟学妹的建议\n{report.advice_for_others}\n")

        if report.confidence_before is not None:
            content_sections.append(f"## 备考信心\n考前信心度: {report.confidence_before}/10\n")

        content = "\n".join(content_sections)

        # 构建 tags
        tags = []
        if report.actual_school:
            tags.append(report.actual_school)
        if report.actual_major:
            tags.append(report.actual_major)
        path_str = report.admission_path.value if hasattr(report.admission_path, "value") else str(report.admission_path)
        if path_str == "adjustment":
            tags.append("调剂")
        tags.append(f"{report.year}年")

        # category 基于路径
        category = "adjustment" if path_str == "adjustment" else "general"

        post = ExperiencePost(
            user_id=report.user_id,
            title=title[:200],  # 限制长度
            summary=summary[:500],
            content=content,
            tags=tags[:10],  # 限制 tags 数量
            category=category,
            is_anonymous=False,
            source_platform="outcome_report",
            source_url=f"/api/outcome-report/{report.id}",
            status="pending",  # 需用户审核
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        logger.info("从上岸报告 %s 生成经验贴草稿 %s", report.id, post.id)
        return post
    except Exception as e:
        logger.warning("从上岸报告生成经验贴失败 report_id=%s: %s", report.id, e)
        db.rollback()
        return None
