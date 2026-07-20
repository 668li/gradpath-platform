"""用户上下文 API — 决策副驾驶核心数据接口。

GET /api/user-context: 获取聚合用户上下文（画像+诊断+记忆+决策+统计）
GET /api/user-context/prompt: 获取 AI 注入用 prompt 文本
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.user_context_service import build_context_prompt, get_user_context

router = APIRouter(prefix="/api/user-context", tags=["用户上下文"])


@router.get("")
def get_context(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取用户聚合上下文（结构化 dict）。"""
    return get_user_context(db, user.id)


@router.get("/prompt")
def get_context_prompt(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取 AI 注入用上下文 prompt 文本。"""
    return {"prompt": build_context_prompt(db, user.id)}
