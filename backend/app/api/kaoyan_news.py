"""考研外部资讯 API。"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.kaoyan_news import KaoyanNews
from app.schemas.kaoyan_news import KaoyanNewsListResponse, KaoyanNewsResponse

router = APIRouter(prefix="/api/kaoyan-news", tags=["考研资讯"])


@router.get("", response_model=KaoyanNewsListResponse)
def list_kaoyan_news(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(None, description="分类过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    """获取考研资讯列表（默认只展示已审核内容）。"""
    query = db.query(KaoyanNews).filter(KaoyanNews.status == "approved")

    if category:
        query = query.filter(KaoyanNews.category == category)
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
