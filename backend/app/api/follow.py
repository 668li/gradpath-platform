"""关注关系 API — 社区社交图谱的核心。"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.follow import Follow
from app.models.user import User
from app.api.notifications import create_notification

router = APIRouter(prefix="/api/follow", tags=["关注"])


@router.post("", status_code=status.HTTP_201_CREATED)
def follow(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """关注某用户。body: { followee_id: str }"""
    followee_id = body.get("followee_id") if isinstance(body, dict) else None
    if not followee_id:
        raise HTTPException(status_code=400, detail="followee_id 必填")
    try:
        fid = str(UUID(followee_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="followee_id 格式错误")
    if fid == user.id:
        raise HTTPException(status_code=400, detail="不能关注自己")

    exists = (
        db.query(Follow)
        .filter(Follow.follower_id == user.id, Follow.followee_id == fid)
        .first()
    )
    if exists:
        return {"ok": True, "followed": True, "already": True}

    f = Follow(follower_id=user.id, followee_id=fid)
    db.add(f)
    # 通知被关注者
    create_notification(
        db, UUID(fid), type="new_follower",
        title="有人关注了你",
        content=f"{user.nickname or user.username or user.name} 关注了你",
    )
    db.commit()
    return {"ok": True, "followed": True}


@router.delete("")
def unfollow(
    followee_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """取消关注。query: followee_id"""
    f = (
        db.query(Follow)
        .filter(Follow.follower_id == user.id, Follow.followee_id == followee_id)
        .first()
    )
    if f:
        db.delete(f)
        db.commit()
    return {"ok": True, "followed": False}


@router.get("/list")
def list_follow(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回当前用户的关注/粉丝列表。"""
    following = (
        db.query(Follow).filter(Follow.follower_id == user.id).all()
    )
    followers = (
        db.query(Follow).filter(Follow.followee_id == user.id).all()
    )
    uid = user.id

    def _load(pairs, me_is_follower: bool):
        out = []
        for f in pairs:
            other_id = f.followee_id if me_is_follower else f.follower_id
            u = db.query(User).filter(User.id == other_id).first()
            if not u:
                continue
            out.append({
                "user_id": other_id,
                "nickname": u.nickname or u.username or u.name,
                "school": u.school,
                "major": u.major,
                "is_following": me_is_follower
                or db.query(Follow)
                .filter(Follow.follower_id == uid, Follow.followee_id == other_id)
                .first()
                is not None,
            })
        return out

    return {
        "following": _load(following, True),
        "followers": _load(followers, False),
    }


@router.get("/status")
def follow_status(
    followee_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询是否已关注某用户。"""
    f = (
        db.query(Follow)
        .filter(Follow.follower_id == user.id, Follow.followee_id == followee_id)
        .first()
    )
    return {"is_following": f is not None}
