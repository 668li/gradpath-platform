"""用户记忆 API — AI 长期记忆事实库接口。

GET /api/user-memory: 检索记忆事实
POST /api/user-memory: 用户主动添加事实
POST /api/user-memory/{fact_id}/feedback: 用户反馈
DELETE /api/user-memory/{fact_id}: 删除事实
POST /api/user-memory/extract: 从对话中抽取事实（管理员触发）
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.user_memory import MemoryFactType
from app.services.user_memory_service import (
    add_user_provided_fact,
    delete_memory_fact,
    extract_memory_facts,
    get_user_memory,
    update_memory_feedback,
)

router = APIRouter(prefix="/api/user-memory", tags=["用户记忆"])


class AddFactRequest(BaseModel):
    fact_type: str = Field(..., max_length=50, description="事实类型")
    fact_key: str = Field(..., max_length=100, description="事实键")
    fact_value: str = Field(..., max_length=500, description="事实值")


class FeedbackRequest(BaseModel):
    feedback: str = Field(..., max_length=20, description="positive / negative")


class ExtractRequest(BaseModel):
    conversation_id: UUID | None = Field(None, description="关联对话 ID")
    messages: list[dict] = Field(..., min_length=1, max_length=50, description="对话消息列表")


@router.get("")
def list_memory(
    fact_type: str | None = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """检索用户记忆事实。"""
    ft = None
    if fact_type:
        try:
            ft = MemoryFactType(fact_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的 fact_type")
    facts = get_user_memory(db, user.id, fact_type=ft, limit=limit)
    return {
        "items": [
            {
                "id": str(f.id),
                "fact_type": f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type),
                "fact_key": f.fact_key,
                "fact_value": f.fact_value,
                "confidence": f.confidence,
                "source": f.source,
                "use_count": f.use_count,
                "user_feedback": f.user_feedback,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "last_used_at": f.last_used_at.isoformat() if f.last_used_at else None,
            }
            for f in facts
        ],
        "total": len(facts),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def add_fact(
    req: AddFactRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用户主动添加记忆事实。"""
    try:
        ft = MemoryFactType(req.fact_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的 fact_type")

    fact = add_user_provided_fact(db, user.id, ft, req.fact_key, req.fact_value)
    return {
        "id": str(fact.id),
        "fact_type": fact.fact_type.value if hasattr(fact.fact_type, "value") else str(fact.fact_type),
        "fact_key": fact.fact_key,
        "fact_value": fact.fact_value,
        "confidence": fact.confidence,
        "source": fact.source,
    }


@router.post("/{fact_id}/feedback")
def feedback(
    fact_id: UUID,
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用户反馈调整置信度。"""
    if req.feedback not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="feedback 必须为 positive 或 negative")

    fact = update_memory_feedback(db, user.id, fact_id, req.feedback)
    if not fact:
        raise HTTPException(status_code=404, detail="记忆事实不存在")
    return {
        "id": str(fact.id),
        "confidence": fact.confidence,
        "is_active": fact.is_active,
        "user_feedback": fact.user_feedback,
    }


@router.delete("/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    fact_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除记忆事实（软删除）。"""
    if not delete_memory_fact(db, user.id, fact_id):
        raise HTTPException(status_code=404, detail="记忆事实不存在")


@router.post("/extract")
async def extract(
    req: ExtractRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从对话消息中抽取记忆事实（触发 LLM）。"""
    facts = await extract_memory_facts(db, user.id, req.conversation_id, req.messages)
    return {
        "extracted_count": len(facts),
        "items": [
            {
                "id": str(f.id),
                "fact_type": f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type),
                "fact_key": f.fact_key,
                "fact_value": f.fact_value,
                "confidence": f.confidence,
            }
            for f in facts
        ],
    }
