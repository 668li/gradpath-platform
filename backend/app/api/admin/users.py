"""管理端用户管理 API — 社区治理。

- GET  /api/admin/users 用户列表（关键词/状态筛选，分页）
- POST /api/admin/users/{user_id}/ban   封禁（必填原因；联动清缓存即时生效）
- POST /api/admin/users/{user_id}/unban 解封（恢复 active）

封禁安全护栏：不能封禁管理员账户（moderation_service 兜底）。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.database import get_db
from app.models.user import User, UserStatus
from app.schemas.admin_user import AdminUserListVO, AdminUserVO, BanRequest, BanResponse
from app.services.moderation_service import ban_user, unban_user

router = APIRouter(prefix="/api/admin/users", tags=["社区治理-用户管理"])


def _resolve_user(db: Session, user_id: str) -> User:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="用户 ID 格式错误")
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _to_vo(user: User) -> AdminUserVO:
    return AdminUserVO(
        id=user.id,
        email=user.email,
        name=user.name,
        nickname=user.nickname,
        school=user.school,
        major=user.major,
        graduation_year=user.graduation_year,
        is_admin=bool(user.is_admin),
        status=user.status.value if user.status else UserStatus.active.value,
        banned_at=user.banned_at,
        ban_reason=user.ban_reason,
        created_at=user.created_at,
    )


@router.get("", response_model=AdminUserListVO)
def list_users(
    keyword: str | None = Query(None, max_length=100, description="搜索邮箱/昵称/姓名"),
    status_filter: UserStatus | None = Query(None, alias="status", description="按账户状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = db.query(User)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            or_(User.email.ilike(like), User.name.ilike(like), User.nickname.ilike(like))
        )
    if status_filter is not None:
        q = q.filter(User.status == status_filter)
    total = q.count()
    rows = (
        q.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AdminUserListVO(total=total, items=[_to_vo(u) for u in rows])


@router.post("/{user_id}/ban", response_model=BanResponse)
def ban_user_endpoint(
    user_id: str,
    data: BanRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    target = _resolve_user(db, user_id)
    ban_user(db, target, data.reason)
    db.commit()
    db.refresh(target)
    return BanResponse(
        id=target.id,
        status="banned",
        banned_at=target.banned_at,
        ban_reason=target.ban_reason,
        message="用户已封禁",
    )


@router.post("/{user_id}/unban", response_model=BanResponse)
def unban_user_endpoint(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    target = _resolve_user(db, user_id)
    unban_user(db, target)
    db.commit()
    db.refresh(target)
    return BanResponse(
        id=target.id,
        status="active",
        banned_at=None,
        ban_reason=None,
        message="用户已解封",
    )
