# backend/app/api/user_llm_config.py
"""用户自带 LLM API 配置（BYOK）路由。

AgentChat（AI 对话）在服务器未配置 LLM_API_KEY 时处于关闭状态；
用户可在设置页填入自己的 OpenAI 兼容 API Key 启用对话。

- GET    /api/user-llm-config — 查询当前配置（Key 只回掩码）
- PUT    /api/user-llm-config — 保存配置（Key 加密落库）
- DELETE /api/user-llm-config — 删除配置
- POST   /api/user-llm-config/verify — 连通性验证（不落库）
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import rate_limits
from app.database import get_db
from app.main import limiter
from app.models.user import User
from app.schemas.user_llm_config import (
    PlatformLLMStatusResponse,
    UserLLMConfigResponse,
    UserLLMConfigSaveRequest,
    UserLLMVerifyRequest,
    UserLLMVerifyResponse,
)
from app.services.user_llm_service import (
    UserLLMConfigError,
    delete_user_llm_config,
    get_user_llm_config,
    save_user_llm_config,
    to_response,
    verify_user_llm,
)

router = APIRouter(prefix="/api/user-llm-config", tags=["AI 对话服务配置"])


@router.get("", response_model=UserLLMConfigResponse | None)
def get_config(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询当前用户的 LLM 配置；未配置时返回 null。"""
    cfg = get_user_llm_config(db, user.id)
    return to_response(cfg) if cfg else None


@router.get("/platform-status", response_model=PlatformLLMStatusResponse)
def get_platform_status(user: User = Depends(get_current_user)):
    """平台内置 LLM 可用性（供前端自适应文案，不暴露任何密钥信息）。"""
    from app.config import settings

    return PlatformLLMStatusResponse(
        enabled=bool(settings.LLM_API_KEY.strip()),
        model=settings.LLM_MODEL,
        daily_quota=settings.LLM_DAILY_QUOTA,
    )


@router.put("", response_model=UserLLMConfigResponse)
def save_config(
    body: UserLLMConfigSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """保存 LLM 配置；api_key 留空表示沿用已保存的 Key。"""
    try:
        cfg = save_user_llm_config(db, user.id, body)
    except UserLLMConfigError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return to_response(cfg)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除当前用户的 LLM 配置。"""
    if not delete_user_llm_config(db, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="尚未配置")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify", response_model=UserLLMVerifyResponse)
@limiter.limit(rate_limits.AI_CHAT)
async def verify_config(
    request: Request,
    response: Response,
    body: UserLLMVerifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """验证配置连通性（发一次最小 LLM 请求）；api_key 留空则用已保存的 Key。"""
    api_key = (body.api_key or "").strip()
    if not api_key:
        cfg = get_user_llm_config(db, user.id)
        if not cfg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="尚未保存 API Key，请先填写",
            )
        from app.core.secret_crypto import decrypt_secret

        api_key = decrypt_secret(cfg.api_key_encrypted)
    try:
        return await verify_user_llm(body.base_url, body.model, api_key)
    except UserLLMConfigError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except httpx.HTTPError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="无法连接目标服务")
