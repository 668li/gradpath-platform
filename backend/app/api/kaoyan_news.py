"""考研外部资讯 API — 资讯中心（信息差聚合展示）。

Phase D1 扩展：quality 排序、质量等级/来源筛选、分类列表，供资讯中心页
（分类 tab / 质量徽章 / 关键日期）使用。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.kaoyan_news import KaoyanNews
from app.schemas.kaoyan_news import KaoyanNewsListResponse, KaoyanNewsResponse

router = APIRouter(prefix="/api/kaoyan-news", tags=["考研资讯"])


@router.get("/categories")
def list_news_categories(db: Session = Depends(get_db)):
    """已审核资讯的全部分类（按出现次数降序，供资讯中心分类 tab）。"""
    rows = (
        db.query(KaoyanNews.category, func.count(KaoyanNews.id))
        .filter(
            KaoyanNews.status == "approved",
            KaoyanNews.category != "general",
        )
        .group_by(KaoyanNews.category)
        .order_by(func.count(KaoyanNews.id).desc())
        .all()
    )
    return {"categories": [r[0] for r in rows]}


@router.get("", response_model=KaoyanNewsListResponse)
def list_kaoyan_news(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    category: str | None = Query(None, description="分类过滤"),
    search: str | None = Query(None, description="搜索关键词"),
    sort: str = Query(
        "latest", pattern="^(latest|quality)$", description="排序：latest 最新 / quality 质量分降序"
    ),
    quality_grade: str | None = Query(None, description="质量等级过滤（A/B/C/D）"),
    source_platform: str | None = Query(None, description="来源过滤（rss/eol/official 等）"),
    db: Session = Depends(get_db),
):
    """获取考研资讯列表（默认只展示已审核内容；支持质量排序与筛选）。"""
    query = db.query(KaoyanNews).filter(KaoyanNews.status == "approved")

    if category:
        query = query.filter(KaoyanNews.category == category)
    if quality_grade:
        query = query.filter(KaoyanNews.quality_grade == quality_grade.upper())
    if source_platform:
        query = query.filter(KaoyanNews.source_platform == source_platform)
    if search:
        query = query.filter(
            or_(
                KaoyanNews.title.ilike(f"%{search}%"),
                KaoyanNews.summary.ilike(f"%{search}%"),
                KaoyanNews.content.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    if sort == "quality":
        # 质量分降序（无质量分的历史数据排最后），同分按发布时间倒序
        items = (
            query.order_by(
                KaoyanNews.quality_score.desc().nullslast(),
                KaoyanNews.published_at.desc().nullslast(),
                KaoyanNews.created_at.desc(),
            )
            .offset(offset)
            .limit(page_size)
            .all()
        )
    else:
        items = (
            query.order_by(KaoyanNews.published_at.desc().nullslast(), KaoyanNews.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

    return KaoyanNewsListResponse(
        items=[KaoyanNewsResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{news_id}", response_model=KaoyanNewsResponse)
def get_kaoyan_news_detail(
    news_id: UUID,
    db: Session = Depends(get_db),
):
    """获取考研资讯详情。"""
    news = db.query(KaoyanNews).filter(KaoyanNews.id == news_id).first()
    if not news:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资讯不存在")
    return KaoyanNewsResponse.model_validate(news)
