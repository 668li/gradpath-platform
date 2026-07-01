# backend/app/api/knowledge.py
"""知识库 API 路由 — Phase 11。

- GET /api/knowledge — 分页列表（可选 category/tags 过滤）
- GET /api/knowledge/{id} — 详情
- POST /api/knowledge/search — 关键词搜索（top 5）
- POST /api/knowledge — 创建（管理员）
- PUT /api/knowledge/{id} — 更新（管理员）
- DELETE /api/knowledge/{id} — 删除（管理员）
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.knowledge import (
    KnowledgeArticleCreate,
    KnowledgeArticleResponse,
    KnowledgeArticleUpdate,
    KnowledgeSearchRequest,
)
from app.services.knowledge_service import (
    create_article,
    delete_article,
    get_article,
    list_articles,
    search_articles,
    update_article,
)

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.get("", response_model=PaginatedResponse[KnowledgeArticleResponse])
def list_all(
    category: str | None = Query(None, description="分类过滤"),
    tags: list[str] | None = Query(None, description="标签过滤（多个为 OR）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """分页查询知识条目（需登录）。"""
    items, total = list_articles(db, category=category, tags=tags, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{article_id}", response_model=KnowledgeArticleResponse)
def get_one(
    article_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单条知识（需登录）。"""
    article = get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
    return article


@router.post("/search", response_model=list[KnowledgeArticleResponse])
def search(
    body: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """关键词搜索知识条目（需登录），返回 top 5 结果。"""
    return search_articles(db, body.query, limit=5)


@router.post(
    "",
    response_model=KnowledgeArticleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(
    data: KnowledgeArticleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """创建知识条目（仅管理员）。"""
    return create_article(db, data.model_dump())


@router.put("/{article_id}", response_model=KnowledgeArticleResponse)
def update(
    article_id: UUID,
    data: KnowledgeArticleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """更新知识条目（仅管理员）。"""
    article = update_article(db, article_id, data.model_dump(exclude_unset=True))
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    article_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """删除知识条目（仅管理员）。"""
    article = get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识条目不存在")
    delete_article(db, article_id)
