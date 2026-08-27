"""用户屏蔽 API — 社区治理。

- POST   /api/users/{user_id}/block   屏蔽用户（幂等：重复屏蔽返回成功）
- DELETE /api/users/{user_id}/block   取消屏蔽（不存在也返回成功）
- GET    /api/users/me/blocks         我屏蔽的用户列表（分页，最新在前）

屏蔽只影响调用方视角（列表过滤在被屏蔽端查询实现），
不做跨用户强制隔离，避免破坏既有查询性能与缓存。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.block_relation import BlockRelation
from app.models.user import User
from app.schemas.block import BlockedUserVO, BlockListVO, BlockResult

router = APIRouter(prefix="/api/users", tags=["社区治理-屏蔽"])


def _resolve_user(db: Session, user_id: str) -> User:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="用户 ID 格式错误")
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/{user_id}/block", response_model=BlockResult)
def block_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = _resolve_user(db, user_id)
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能屏蔽自己")
    existing = (
        db.query(BlockRelation)
        .filter(
            BlockRelation.blocker_id == current_user.id,
            BlockRelation.blocked_id == target.id,
        )
        .first()
    )
    if existing is None:
        db.add(BlockRelation(blocker_id=current_user.id, blocked_id=target.id))
        db.commit()
    return BlockResult(blocked_id=target.id, message="已屏蔽")


@router.delete("/{user_id}/block", response_model=BlockResult)
def unblock_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = _resolve_user(db, user_id)
    rel = (
        db.query(BlockRelation)
        .filter(
            BlockRelation.blocker_id == current_user.id,
            BlockRelation.blocked_id == target.id,
        )
        .first()
    )
    if rel is not None:
        db.delete(rel)
        db.commit()
    return BlockResult(blocked_id=target.id, message="已取消屏蔽")


@router.get("/me/blocks", response_model=BlockListVO)
def list_blocks(
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(BlockRelation).filter(BlockRelation.blocker_id == current_user.id)
    total = q.count()
    rows = (
        q.order_by(BlockRelation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    blocked_ids = [r.blocked_id for r in rows]
    users = {}
    if blocked_ids:
        users = {u.id: u for u in db.query(User).filter(User.id.in_(blocked_ids)).all()}
    items = []
    for r in rows:
        u = users.get(r.blocked_id)
        if u is not None:
            items.append(
                BlockedUserVO(
                    blocked_id=u.id,
                    name=u.name,
                    nickname=u.nickname,
                    school=u.school,
                    major=u.major,
                    blocked_at=r.created_at,
                )
            )
    return BlockListVO(total=total, items=items)
