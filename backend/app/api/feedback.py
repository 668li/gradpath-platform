# backend/app/api/feedback.py
"""用户反馈API — 可用性测试五类不适问题收集。

- POST /api/feedback  提交反馈（category: 卡顿/找不到入口/操作繁琐/提示模糊/逻辑别扭）
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
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

    @classmethod
    def validate_user_id(cls, v):
        return str(v) if hasattr(v, "hex") else v

    @classmethod
    def validate_created_at(cls, v):
        return v.isoformat() if hasattr(v, "isoformat") else str(v)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=FeedbackItem)
def create_feedback(
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
    return FeedbackItem(
        id=feedback.id,
        user_id=str(feedback.user_id) if feedback.user_id else None,
        session_id=feedback.session_id,
        category=feedback.category,
        content=feedback.content,
        page=feedback.page,
        created_at=feedback.created_at.isoformat() if feedback.created_at else "",
    )
