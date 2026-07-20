"""考研社区 — 经验贴 API。"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session, selectinload

from app.core.cache import cache
from app.core.cursor_pagination import encode_cursor
from app.core.deps import get_admin_user, get_current_user
from app.core.rate_limit import rate_limits
from app.database import get_db
from app.main import limiter
from app.models.experience_post import ExperiencePost
from app.models.user import User
from app.schemas.common import CursorPaginatedResponse
from app.schemas.experience_post import (
    ExperiencePostCreate,
    ExperiencePostListResponse,
    ExperiencePostResponse,
    ExperiencePostUpdate,
)
from app.services.experience_post_service import (
    approve_experience_post,
    create_experience_post,
    delete_experience_post,
    get_experience_post,
    get_experience_posts,
    get_experience_posts_cursor,
    increment_experience_post_view,
    like_experience_post,
    reject_experience_post,
    update_experience_post,
)

router = APIRouter(prefix="/api/kaoyan/experience-posts", tags=["考研社区-经验贴"])


def _check_post_owner(post: ExperiencePost, user: User) -> None:
    if not user.is_admin and post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作该经验贴",
        )


@router.get("", response_model=ExperiencePostListResponse | CursorPaginatedResponse[ExperiencePostResponse])
def list_experience_posts(
    page: int = Query(1, ge=1, description="页码（offset 分页）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    cursor: Optional[str] = Query(None, description="游标（cursor 分页，传则忽略 page）"),
    category: Optional[str] = Query(None, description="分类过滤"),
    tag: Optional[str] = Query(None, description="标签过滤"),
    status: Optional[str] = Query(None, description="审核状态过滤（默认 approved）"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    """获取经验贴列表（默认展示已通过的内容）。

    支持两种分页模式：
    - offset 分页：传 page + page_size（默认）
    - cursor 分页：传 cursor + page_size（高性能，适合无限滚动）
    """
    # 生成缓存键
    cache_key = f"exp_posts:list:{page}:{page_size}:{category}:{tag}:{status}:{search}"

    # 尝试从缓存获取
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    if cursor:
        items, next_cursor, has_more = get_experience_posts_cursor(
            db,
            page_size=page_size,
            cursor=cursor,
            category=category,
            tag=tag,
            status=status,
            search=search,
        )
        result = CursorPaginatedResponse(
            items=[ExperiencePostResponse.model_validate(p) for p in items],
            next_cursor=next_cursor,
            has_more=has_more,
        )
    else:
        posts, total = get_experience_posts(
            db,
            page=page,
            page_size=page_size,
            category=category,
            tag=tag,
            status=status,
            search=search,
        )
        result = ExperiencePostListResponse(
            items=[ExperiencePostResponse.model_validate(p) for p in posts],
            total=total,
            page=page,
            page_size=page_size,
        )

    # 缓存结果（2分钟）
    cache.set(cache_key, result, ttl=120)
    return result


@router.get("/{post_id}", response_model=ExperiencePostResponse)
def get_experience_post_detail(
    post_id: UUID,
    db: Session = Depends(get_db),
):
    """获取经验贴详情（自动增加浏览数）。"""
    post = get_experience_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="经验贴不存在")
    increment_experience_post_view(db, post_id)
    return ExperiencePostResponse.model_validate(post)


@router.post(
    "",
    response_model=ExperiencePostResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(rate_limits.EXPERIENCE_POST_CREATE)
def create_experience_post_endpoint(
    request: Request,
    response: Response,
    data: ExperiencePostCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建经验贴（需登录）。"""
    post = create_experience_post(db, user.id, data.model_dump())
    return ExperiencePostResponse.model_validate(post)


@router.put("/{post_id}", response_model=ExperiencePostResponse)
def update_experience_post_endpoint(
    post_id: UUID,
    data: ExperiencePostUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新经验贴（作者或管理员）。"""
    post = get_experience_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="经验贴不存在")
    _check_post_owner(post, user)

    updated = update_experience_post(db, post_id, data.model_dump(exclude_unset=True))
    return ExperiencePostResponse.model_validate(updated)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience_post_endpoint(
    post_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除经验贴（作者或管理员）。"""
    post = get_experience_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="经验贴不存在")
    _check_post_owner(post, user)

    delete_experience_post(db, post_id)
    return None


@router.post("/{post_id}/like")
@limiter.limit(rate_limits.COMMUNITY_LIKE)
def like_experience_post_endpoint(
    request: Request,
    response: Response,
    post_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """点赞经验贴（需登录）。"""
    post = like_experience_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="经验贴不存在")
    return {"message": "点赞成功", "like_count": post.like_count}


@router.post("/{post_id}/approve")
def approve_experience_post_endpoint(
    post_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """审核通过经验贴（管理员）。"""
    post = approve_experience_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="经验贴不存在")
    return {"message": "审核通过", "post_id": str(post.id)}


@router.post("/{post_id}/reject")
def reject_experience_post_endpoint(
    post_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """拒绝经验贴（管理员）。"""
    post = reject_experience_post(db, post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="经验贴不存在")
    return {"message": "已拒绝", "post_id": str(post.id)}
