# backend/app/api/chat.py
"""对话 API 路由 — Phase 11 AI 职业管家。

- POST /api/chat/conversations — 新建对话
- GET /api/chat/conversations — 分页列表
- GET /api/chat/conversations/{id}/messages — 消息列表
- POST /api/chat/conversations/{id}/messages — 发送消息（限流 20/min）
- PATCH /api/chat/conversations/{id} — 更新标题
- DELETE /api/chat/conversations/{id} — 删除对话
- GET /api/chat/skills — 列出可用 Skill
"""
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.main import limiter
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
    SkillInfo,
)
from app.schemas.common import PaginatedResponse
from app.services.ai_service import AIServiceNotConfigured
from app.services.chat_service import (
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
    list_messages,
    send_message,
    update_conversation_title,
)
from app.skills.registry import list_skills

router = APIRouter(prefix="/api/chat", tags=["AI 职业管家"])


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conv(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """新建对话。"""
    return create_conversation(db, user.id, body.title)


@router.get("/conversations", response_model=PaginatedResponse[ConversationResponse])
def list_conv(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """分页列出对话。"""
    items, total = list_conversations(db, user.id, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取对话消息（按时间升序）。"""
    conv = get_conversation(db, user.id, conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return list_messages(db, conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
)
@limiter.limit("20/minute")
def post_message(
    request: Request,
    response: Response,
    conversation_id: UUID,
    body: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """发送消息并获取 AI 回复。

    降级策略：
    - LLM_API_KEY 未配置 → 503
    - LLM 超时 → 504
    - 其他异常 → 500
    """
    conv = get_conversation(db, user.id, conversation_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    try:
        result = send_message(db, user.id, conversation_id, body.content, body.skill_hint)
    except AIServiceNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务未配置（LLM_API_KEY 缺失）",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 回复超时，请稍后重试",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"对话服务异常: {e}",
        )
    return result


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
def update_conv(
    conversation_id: UUID,
    body: ConversationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新对话标题。"""
    conv = update_conversation_title(db, user.id, conversation_id, body.title)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return conv


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conv(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除对话。"""
    if not delete_conversation(db, user.id, conversation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")


@router.get("/skills", response_model=list[SkillInfo])
def skills_endpoint(
    user: User = Depends(get_current_user),
):
    """列出可用 Skill。"""
    return list_skills()
