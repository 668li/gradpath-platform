# backend/app/api/feedback.py
"""用户反馈API — 可用性测试五类不适问题收集。

- POST /api/feedback  提交反馈（category: 卡顿/找不到入口/操作繁琐/提示模糊/逻辑别扭）
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user, get_current_user
from app.core.push_notify import notify_async
from app.core.rate_limit import rate_limits
from app.database import get_db
from app.main import limiter
from app.models.event import Feedback
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["反馈"])

VALID_CATEGORIES = ["卡顿", "找不到入口", "操作繁琐", "提示模糊", "逻辑别扭"]


class FeedbackCreate(BaseModel):
    category: str = Field(..., description="五大类: 卡顿/找不到入口/操作繁琐/提示模糊/逻辑别扭")
    content: str | None = Field(None, description="文字描述")
    screenshot: str | None = Field(None, description="截图(base64或URL)")
    page: str | None = Field(None, description="触发路由")
    session_id: str | None = Field(None, description="关联会话ID")


class FeedbackItem(BaseModel):
    id: int
    user_id: str | None
    session_id: str | None
    category: str
    content: str | None
    page: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=FeedbackItem)
@limiter.limit(rate_limits.QUALITY_FEEDBACK_CREATE)  # 复用 5/min 档：反馈不该被刷
def create_feedback(
    request: Request,
    response: Response,
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交用户反馈。"""
    if data.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的反馈分类，应为: {VALID_CATEGORIES}",
        )
    feedback = Feedback(
        user_id=user.id,
        session_id=data.session_id,
        category=data.category,
        content=data.content,
        screenshot=data.screenshot,
        page=data.page,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    # 新反馈即时触达（fire-and-forget，不阻塞响应；未配置 SERVERCHAN_URL 时静默跳过）
    notify_async(
        "📩 新用户反馈",
        f"[{data.category}] {data.content or '（无文字）'}\n页面: {data.page or '-'}",
    )

    return FeedbackItem(
        id=feedback.id,
        user_id=str(feedback.user_id) if feedback.user_id else None,
        session_id=feedback.session_id,
        category=feedback.category,
        content=feedback.content,
        page=feedback.page,
        created_at=feedback.created_at.isoformat() if feedback.created_at else "",
    )


# ----------------------------------------------------------------------
# 管理端（2026-09-06 反馈通道补全）：此前只有写入端，管理员看不到反馈
# ----------------------------------------------------------------------


class FeedbackAdminPage(BaseModel):
    items: list[FeedbackItem]
    total: int
    page: int
    page_size: int


@router.get("/admin/list", response_model=FeedbackAdminPage)
def admin_list_feedback(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None, description="按类目筛选"),
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """管理端：反馈列表（倒序分页，可按类目筛选）。"""
    query = db.query(Feedback)
    if category:
        query = query.filter(Feedback.category == category)
    total = query.count()
    rows = (
        query.order_by(Feedback.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        FeedbackItem(
            id=r.id,
            user_id=str(r.user_id) if r.user_id else None,
            session_id=r.session_id,
            category=r.category,
            content=r.content,
            page=r.page,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]
    return FeedbackAdminPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/admin/stats")
def admin_feedback_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """管理端：反馈统计（类目计数 + 近 7 天新增）。"""
    by_category = dict(
        db.query(Feedback.category, func.count(Feedback.id))
        .group_by(Feedback.category)
        .all()
    )
    from datetime import datetime, timedelta, timezone

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent = (
        db.query(func.count(Feedback.id)).filter(Feedback.created_at >= week_ago).scalar() or 0
    )
    return {"total": sum(by_category.values()), "by_category": by_category, "last_7d": recent}
