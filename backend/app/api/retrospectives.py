from datetime import date
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.main import limiter
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.retrospective import (
    AIRetroDraftRequest,
    AIRetroDraftResponse,
    RetroCreate,
    RetroResponse,
    RetroUpdate,
)
from app.services.ai_service import AIServiceNotConfigured
from app.services.retro_ai_service import generate_ai_retro_draft
from app.services.retrospective_service import (
    create_retrospective,
    delete_retrospective,
    generate_draft,
    get_retrospective,
    list_retrospectives_paginated,
    update_retrospective,
)

router = APIRouter(prefix="/api/retrospectives", tags=["阶段复盘"])


@router.post("", response_model=RetroResponse, status_code=status.HTTP_201_CREATED)
def create(data: RetroCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_retrospective(db, user.id, data)


@router.get("", response_model=PaginatedResponse[RetroResponse])
def list_all(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items, total = list_retrospectives_paginated(db, user.id, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/draft")
def draft(
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return generate_draft(db, user.id, period_start, period_end)


@router.post("/ai-draft", response_model=AIRetroDraftResponse)
@limiter.limit("10/minute")
def ai_draft(
    request: Request,
    response: Response,
    body: AIRetroDraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI 复盘草稿 — 需登录。

    基于用户指定时段内的职业事件（含 STAR 细节）调用 LLM 生成结构化复盘草稿。
    不持久化，由前端决定是否保存为正式复盘。

    降级策略：
    - LLM_API_KEY 未配置 → 503
    - LLM 超时 → 504
    - 其他异常 → 500
    """
    try:
        return generate_ai_retro_draft(
            db, user.id, body.period_start, body.period_end
        )
    except AIServiceNotConfigured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 服务未配置（LLM_API_KEY 缺失）",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI 分析超时，请稍后重试",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 复盘草稿服务异常: {e}",
        )


@router.get("/{retro_id}", response_model=RetroResponse)
def get_one(retro_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_retrospective(db, user.id, retro_id)


@router.patch("/{retro_id}", response_model=RetroResponse)
def update(retro_id: UUID, data: RetroUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return update_retrospective(db, user.id, retro_id, data)


@router.delete("/{retro_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(retro_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    delete_retrospective(db, user.id, retro_id)
