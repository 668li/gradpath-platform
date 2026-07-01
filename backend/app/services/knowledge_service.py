# backend/app/services/knowledge_service.py
"""知识库服务层 — Phase 11。

提供知识条目的分页查询、详情、关键词搜索与管理员 CRUD。
搜索使用 ILIKE 匹配 title/content，按相关度排序。
"""
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.knowledge_article import KnowledgeArticle
from app.services.employment_service import escape_like


def list_articles(
    db: Session,
    category: str | None = None,
    tags: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[KnowledgeArticle], int]:
    """分页查询知识条目，支持分类和标签过滤。

    Args:
        db: 数据库会话
        category: 分类过滤（精确匹配）
        tags: 标签过滤（条目需包含任一标签）
        page: 页码（从 1 开始）
        page_size: 每页条数

    Returns:
        (articles, total) — 当前页条目列表与总数
    """
    query = db.query(KnowledgeArticle)
    if category:
        query = query.filter(KnowledgeArticle.category == category)
    if tags:
        # JSON 数组包含任一标签即可（SQLite/PG 通用：逐标签 OR）
        tag_conditions = []
        for t in tags:
            tag_conditions.append(
                KnowledgeArticle.tags.like(f'%"{escape_like(t)}"%')
            )
        if tag_conditions:
            query = query.filter(or_(*tag_conditions))

    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(KnowledgeArticle.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return items, total


def get_article(db: Session, article_id: UUID) -> KnowledgeArticle | None:
    """获取单条知识。"""
    return db.query(KnowledgeArticle).filter(KnowledgeArticle.id == article_id).first()


def search_articles(db: Session, query: str, limit: int = 5) -> list[KnowledgeArticle]:
    """关键词搜索知识条目。使用 ILIKE 匹配 title 和 content，按相关度排序。

    相关度计算：title 命中权重高于 content 命中。
    """
    if not query or not query.strip():
        return []
    kw = escape_like(query.strip())
    like_kw = f"%{kw}%"

    items = (
        db.query(KnowledgeArticle)
        .filter(
            or_(
                KnowledgeArticle.title.ilike(like_kw, escape="\\"),
                KnowledgeArticle.content.ilike(like_kw, escape="\\"),
            )
        )
        .all()
    )

    def _score(a: KnowledgeArticle) -> int:
        score = 0
        if kw.lower() in (a.title or "").lower():
            score += 10
        if kw.lower() in (a.content or "").lower():
            score += 1
        return score

    items.sort(key=_score, reverse=True)
    return items[:limit]


def create_article(db: Session, data: dict) -> KnowledgeArticle:
    """创建知识条目（管理员）。"""
    article = KnowledgeArticle(
        category=data["category"],
        title=data["title"],
        content=data["content"],
        tags=data.get("tags") or [],
        source=data.get("source"),
        metadata_=data.get("metadata_") or data.get("metadata") or {},
        is_published=data.get("is_published", True),
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def update_article(db: Session, article_id: UUID, data: dict) -> KnowledgeArticle | None:
    """更新知识条目（管理员）。"""
    article = get_article(db, article_id)
    if not article:
        return None
    for field in ("category", "title", "content", "tags", "source", "is_published"):
        if field in data and data[field] is not None:
            setattr(article, field, data[field])
    # metadata_ 在 schema 中以 metadata_ 暴露
    meta = data.get("metadata_") if data.get("metadata_") is not None else data.get("metadata")
    if meta is not None:
        article.metadata_ = meta
    db.commit()
    db.refresh(article)
    return article


def delete_article(db: Session, article_id: UUID) -> None:
    """删除知识条目（管理员）。"""
    article = get_article(db, article_id)
    if article:
        db.delete(article)
        db.commit()
