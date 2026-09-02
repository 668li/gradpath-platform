# backend/app/api/learning_methods.py
"""学习方法 API 路由 — 基于 knowledge_articles(category='学习方法')。

- GET  /api/learning-methods              分页列表（tag过滤 + page/page_size）
- GET  /api/learning-methods/tags          tag分布统计
- GET  /api/learning-methods/{id}          单篇详情
- GET  /api/learning-methods/recommend     推荐文章（个性化AI推荐）
- POST /api/learning-methods/bookmark      收藏文章
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.assessment import Assessment
from app.models.bookmark import Bookmark, BookmarkTargetType
from app.models.knowledge_article import KnowledgeArticle
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learning-methods", tags=["学习方法"])

CATEGORY = "学习方法"


def _is_sqlite() -> bool:
    """检测当前数据库是否为 SQLite（开发环境，不支持 jsonb_array_elements_text）。"""
    return settings.DATABASE_URL.startswith("sqlite")


def _compute_tag_stats(db: Session, limit: int | None = None) -> list[tuple[str, int]]:
    """统计学习方法文章的 tag 分布。

    修复 bug: PostgreSQL 用 jsonb_array_elements_text，SQLite 不支持，
    改为查询所有文章后在 Python 端聚合统计。
    """
    if not _is_sqlite():
        # PostgreSQL: 使用 jsonb_array_elements_text 高效统计
        q = (
            db.query(
                func.jsonb_array_elements_text(KnowledgeArticle.tags).label("tag"),
                func.count(),
            )
            .filter(
                KnowledgeArticle.category == CATEGORY,
                KnowledgeArticle.is_published == True,  # noqa: E712
            )
            .group_by("tag")
            .order_by(func.count().desc())
        )
        if limit:
            q = q.limit(limit)
        return [(r[0], int(r[1])) for r in q.all()]

    # SQLite: Python 端聚合（兼容方案）
    articles = (
        db.query(KnowledgeArticle.tags)
        .filter(
            KnowledgeArticle.category == CATEGORY,
            KnowledgeArticle.is_published == True,  # noqa: E712
        )
        .all()
    )
    counter: dict[str, int] = {}
    for row in articles:
        tags = row[0] if isinstance(row, tuple) else row.tags
        if not tags:
            continue
        if isinstance(tags, str):
            try:
                import json as _json

                tags = _json.loads(tags)
            except Exception:
                continue
        for t in tags:
            if not isinstance(t, str):
                continue
            counter[t] = counter.get(t, 0) + 1
    sorted_tags = sorted(counter.items(), key=lambda x: x[1], reverse=True)
    if limit:
        sorted_tags = sorted_tags[:limit]
    return sorted_tags


# ---------- 学习方法 tag 体系（单一真源：app/services/recommender.py） ----------
# 避免两份 LEARNING_TAGS/_HOLLAND_TO_TAGS 漂移，统一从此处导入。
# 使用独立模块 app/services/recommender.py（抖音四层架构：召回→精排→重排→EE）
from app.services.recommender import _RULE_REASONS  # noqa: F401  保留导入，防止改一处漏一处
from app.services.recommender import LEARNING_TAGS  # noqa: F401
from app.services.recommender import (
    _DIRECTION_TO_TAGS,
    _HOLLAND_TO_TAGS,
    _KEYWORD_TO_TAG,
    random_recommend,
    recommend_personalized,
)


def _match_learning_tag(text: str) -> str | None:
    """从文本中匹配学习方法tag（关键词匹配，单一真源 _KEYWORD_TO_TAG）。"""
    for kw, tag in _KEYWORD_TO_TAG.items():
        if kw in text:
            return tag
    return None


def map_assessment_to_tags(assessment: Assessment) -> dict[str, int]:
    """根据评估结果映射到学习方法tag及权重。"""
    tag_weights: dict[str, int] = {}
    if assessment.result_code:
        all_dims = {"R", "I", "A", "S", "E", "C"}
        present = set(assessment.result_code.upper())
        missing = all_dims - present
        for dim in missing:
            for tag in _HOLLAND_TO_TAGS.get(dim, []):
                tag_weights[tag] = tag_weights.get(tag, 0) + 2
    if assessment.recommended_directions:
        for direction in assessment.recommended_directions:
            for keyword, tags in _DIRECTION_TO_TAGS.items():
                if keyword in direction:
                    for tag in tags:
                        tag_weights[tag] = tag_weights.get(tag, 0) + 3
    return tag_weights


# ---------- response schema ----------

from pydantic import BaseModel, field_validator


class ArticleBrief(BaseModel):
    id: str
    title: str
    content: str
    tags: list[str] = []
    source: str | None = None
    created_at: object

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v


class TagStat(BaseModel):
    tag: str
    count: int


class RecommendItem(BaseModel):
    id: str
    title: str
    content: str
    tags: list[str] = []
    source: str | None = None
    created_at: object
    reason: str = ""
    score: float = 0.0

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v


# ---------- endpoints ----------


@router.get("", response_model=dict)
def list_articles(
    tag: str | None = Query(None, description="按 tag 过滤 (jsonb @>)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """分页查询 category='学习方法' 的文章，支持单 tag 过滤。"""
    q = db.query(KnowledgeArticle).filter(
        KnowledgeArticle.category == CATEGORY,
        KnowledgeArticle.is_published == True,  # noqa: E712
    )
    if tag:
        if _is_sqlite():
            # SQLite: tags 是 JSON 字符串/列表，用 Python 端过滤
            q = q.all()
            q = [a for a in q if a.tags and tag in (a.tags if isinstance(a.tags, list) else [])]
            total = len(q)
            items = q[(page - 1) * page_size : (page - 1) * page_size + page_size]
        else:
            q = q.filter(KnowledgeArticle.tags.contains([tag]))
            total = q.count()
            items = (
                q.order_by(KnowledgeArticle.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
    else:
        total = q.count()
        items = (
            q.order_by(KnowledgeArticle.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    # tags_stats: 当前筛选范围内的 tag 分布
    tag_stats_raw = _compute_tag_stats(db)
    tags_stats = [{"tag": t, "count": c} for t, c in tag_stats_raw]

    return {
        "items": [ArticleBrief.model_validate(a) for a in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "tags_stats": tags_stats,
    }


@router.get("/tags", response_model=list[TagStat])
def get_tags(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """返回 category='学习方法' 的所有 tag 分布统计。"""
    tag_rows = _compute_tag_stats(db)
    return [TagStat(tag=t, count=c) for t, c in tag_rows]


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """返回学习方法的标签统计和总数。"""
    total = (
        db.query(func.count())
        .select_from(KnowledgeArticle)
        .filter(
            KnowledgeArticle.category == CATEGORY,
            KnowledgeArticle.is_published == True,  # noqa: E712
        )
        .scalar()
    )
    tag_rows = _compute_tag_stats(db, limit=10)
    return {
        "total": total or 0,
        "category_counts": [{"category": t, "count": c} for t, c in tag_rows],
    }


@router.get("/recommend", response_model=list[RecommendItem])
async def recommend(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """推荐学习方法文章 — 个性化AI推荐。

    1. 构建用户学习画像（收藏 + 评估 + 经验帖）
    2. 基于画像加权匹配文章
    3. AI生成个性化推荐理由（失败时规则fallback）
    4. 无画像数据时fallback到随机推荐
    """
    # 尝试个性化推荐
    personalized = await recommend_personalized(db, user.id, limit)
    if personalized:
        return [
            RecommendItem(
                id=str(a.id),
                title=a.title,
                content=a.content,
                tags=a.tags or [],
                source=a.source,
                created_at=a.created_at,
                reason=reason,
                score=round(score, 2),
            )
            for a, score, reason in personalized
        ]

    # Fallback: 随机推荐（无画像数据时）
    items = random_recommend(db, limit)
    return [
        RecommendItem(
            id=str(a.id),
            title=a.title,
            content=a.content,
            tags=a.tags or [],
            source=a.source,
            created_at=a.created_at,
            reason="为你推荐一篇优质学习方法文章",
            score=0.0,
        )
        for a in items
    ]


@router.get("/{article_id}", response_model=ArticleBrief)
def get_article(
    article_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """获取单篇文章详情。"""
    article = (
        db.query(KnowledgeArticle)
        .filter(
            KnowledgeArticle.id == article_id,
            KnowledgeArticle.category == CATEGORY,
        )
        .first()
    )
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在")
    return ArticleBrief.model_validate(article)


@router.post("/bookmark", status_code=status.HTTP_201_CREATED)
def bookmark_article(
    article_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """收藏学习方法文章。"""
    article = (
        db.query(KnowledgeArticle)
        .filter(
            KnowledgeArticle.id == article_id,
            KnowledgeArticle.category == CATEGORY,
        )
        .first()
    )
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在")

    exists = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == user.id,
            Bookmark.target_type == BookmarkTargetType.post,
            Bookmark.target_id == str(article_id),
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已收藏")

    bookmark = Bookmark(
        user_id=user.id,
        target_type=BookmarkTargetType.post,
        target_id=str(article_id),
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return {
        "id": str(bookmark.id),
        "target_type": "post",
        "target_id": str(article_id),
        "created_at": bookmark.created_at,
    }
