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
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.assessment import Assessment
from app.models.bookmark import Bookmark, BookmarkTargetType
from app.models.experience_post import ExperiencePost
from app.models.knowledge_article import KnowledgeArticle
from app.models.user import User
from app.schemas.common import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learning-methods", tags=["学习方法"])

CATEGORY = "学习方法"

# ---------- 学习方法 tag 体系 ----------

LEARNING_TAGS = {
    "记忆科学": ["记忆", "遗忘曲线", "间隔重复", "艾宾浩斯"],
    "时间管理": ["番茄", "专注", "日程", "碎片时间"],
    "学习策略": ["费曼", "主动学习", "输出", "深度学习"],
    "习惯养成": ["习惯", "21天", "坚持", "打卡"],
    "笔记方法": ["思维导图", "笔记", "卡片", "整理"],
    "认知科学": ["认知", "元认知", "注意力", "大脑"],
    "身心调节": ["睡眠", "运动", "心态", "焦虑"],
    "备考策略": ["考试", "备考", "复习", "冲刺"],
}

# 反向索引：关键词 → 学习tag
_KEYWORD_TO_TAG = {}
for _tag, _keywords in LEARNING_TAGS.items():
    for _kw in _keywords:
        _KEYWORD_TO_TAG[_kw] = _tag

# Holland维度 → 学习方法tag映射
_HOLLAND_TO_TAGS = {
    "R": ["学习策略", "笔记方法"],       # Realistic: 动手型，适合实践学习
    "I": ["认知科学", "学习策略"],       # Investigative: 研究型，适合深度学习
    "A": ["笔记方法", "认知科学"],       # Artistic: 创意型，适合视觉化笔记
    "S": ["习惯养成", "身心调节"],       # Social: 社交型，适合协作与习惯
    "E": ["时间管理", "备考策略"],       # Enterprising: 领导型，适合目标管理
    "C": ["时间管理", "笔记方法"],       # Conventional: 常规型，适合结构化学习
}

# 职业方向 → 学习方法tag映射
_DIRECTION_TO_TAGS = {
    "开发": ["认知科学", "学习策略"],
    "数据": ["认知科学", "学习策略"],
    "产品": ["时间管理", "学习策略"],
    "设计": ["笔记方法", "认知科学"],
    "运营": ["时间管理", "习惯养成"],
    "教育": ["记忆科学", "学习策略"],
    "金融": ["备考策略", "时间管理"],
    "医学": ["记忆科学", "备考策略"],
    "法律": ["记忆科学", "备考策略"],
    "管理": ["时间管理", "习惯养成"],
}

# ---------- 规则理由生成 ----------

_RULE_REASONS = {
    "记忆科学": "这篇文章介绍记忆科学原理，帮你更高效地记住知识点",
    "时间管理": "你的时间管理需求较高，这篇文章提供实用的时间规划技巧",
    "学习策略": "这篇文章讲解高效学习策略，适合提升你的学习效率",
    "习惯养成": "养成良好学习习惯是进步的基础，这篇文章提供科学方法",
    "笔记方法": "好的笔记方法能事半功倍，这篇文章分享实用的笔记技巧",
    "认知科学": "了解大脑运作原理，帮你更聪明地学习",
    "身心调节": "身心状态影响学习效果，这篇文章教你如何调节状态",
    "备考策略": "科学的备考策略能大幅提升考试成绩",
}


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


# ---------- 个性化推荐引擎 ----------
# 使用独立模块 app/services/recommender.py（抖音四层架构：召回→精排→重排→EE）
from app.services.recommender import (
    recommend_personalized,
    random_recommend,
    build_user_profile,
    _generate_rule_reason,
    _generate_ai_reason,
)


def _match_learning_tag(text: str) -> str | None:
    """从文本中匹配学习方法tag（关键词匹配）。"""
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
        q = q.filter(KnowledgeArticle.tags.contains([tag]))

    total = q.count()
    items = (
        q.order_by(KnowledgeArticle.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # tags_stats: 当前筛选范围内的 tag 分布
    tag_rows = (
        db.query(
            func.jsonb_array_elements_text(KnowledgeArticle.tags).label("tag"),
        )
        .filter(
            KnowledgeArticle.category == CATEGORY,
            KnowledgeArticle.is_published == True,  # noqa: E712
        )
        .group_by("tag")
        .order_by(func.count().desc())
        .all()
    )
    tags_stats = [{"tag": r.tag, "count": r[0]} for r in tag_rows]

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
    tag_rows = (
        db.query(
            func.jsonb_array_elements_text(KnowledgeArticle.tags).label("tag"),
        )
        .filter(
            KnowledgeArticle.category == CATEGORY,
            KnowledgeArticle.is_published == True,  # noqa: E712
        )
        .group_by("tag")
        .order_by(func.count().desc())
        .all()
    )
    return [TagStat(tag=r.tag, count=r[0]) for r in tag_rows]


@router.get("/recommend", response_model=list[RecommendItem])
def recommend(
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
    personalized = recommend_personalized(db, user.id, limit)
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
    return {"id": str(bookmark.id), "target_type": "post", "target_id": str(article_id), "created_at": bookmark.created_at}
