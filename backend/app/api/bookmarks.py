"""收藏 API 路由。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.bookmark import Bookmark, BookmarkTargetType
from app.models.user import User
from app.schemas.bookmark import BookmarkCreate, BookmarkListResponse, BookmarkResponse

router = APIRouter(prefix="/api/bookmarks", tags=["收藏"])


@router.post("", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
def add_bookmark(
    body: BookmarkCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 修复 bug: 原先用 BookmarkTargetType(body.target_type) 直接构造，
    # 失败时抛 ValueError -> 500，应让 Pydantic 在 schema 层校验 -> 422
    target_type_enum = body.target_type
    if isinstance(target_type_enum, str):
        # Pydantic 已自动转换为枚举；这里兜底防御性处理
        try:
            target_type_enum = BookmarkTargetType(target_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效的 target_type: {target_type_enum}",
            )
    exists = (
        db.query(Bookmark)
        .filter(
            Bookmark.user_id == user.id,
            Bookmark.target_type == target_type_enum,
            Bookmark.target_id == body.target_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已收藏",
        )
    bookmark = Bookmark(
        user_id=user.id,
        target_type=target_type_enum,
        target_id=body.target_id,
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


@router.get("", response_model=BookmarkListResponse)
def list_bookmarks(
    target_type: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Bookmark).filter(Bookmark.user_id == user.id)
    if target_type:
        try:
            target_enum = BookmarkTargetType(target_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效的 target_type: {target_type}",
            )
        q = q.filter(Bookmark.target_type == target_enum)
    items = q.order_by(Bookmark.created_at.desc()).all()
    return BookmarkListResponse(items=items, total=len(items))


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_bookmark(
    bookmark_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.id == bookmark_id, Bookmark.user_id == user.id)
        .first()
    )
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在",
        )
    db.delete(bookmark)
    db.commit()
