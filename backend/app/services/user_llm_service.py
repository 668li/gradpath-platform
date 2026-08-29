# backend/app/services/user_llm_service.py
"""用户自带 LLM 配置服务（BYOK）。

- 配置增删查（api_key 加密落库）
- resolve：解密出可用的 LLMOverride，供 chat 链路覆盖服务器默认配置
- verify：向用户的 OpenAI 兼容端点发一次最小请求验证连通性
"""

import logging
import re
import time
from dataclasses import dataclass
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.secret_crypto import decrypt_secret, encrypt_secret, mask_secret
from app.models.user_llm_config import UserLLMConfig
from app.schemas.user_llm_config import (
    UserLLMConfigResponse,
    UserLLMConfigSaveRequest,
    UserLLMVerifyResponse,
)

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


class UserLLMConfigError(ValueError):
    """配置参数不合法。"""


@dataclass
class LLMOverride:
    """按用户覆盖的 LLM 调用参数。"""

    api_key: str
    model: str
    base_url: str


def _validate(base_url: str, model: str, api_key: str) -> None:
    if not _URL_RE.match(base_url or ""):
        raise UserLLMConfigError("Base URL 必须是合法的 http(s) 地址")
    if len(base_url) > 500:
        raise UserLLMConfigError("Base URL 过长（最多 500 字符）")
    if not (model or "").strip():
        raise UserLLMConfigError("模型名称不能为空")
    if len(model) > 100:
        raise UserLLMConfigError("模型名称过长（最多 100 字符）")
    if not (api_key or "").strip():
        raise UserLLMConfigError("API Key 不能为空")
    if len(api_key) > 500:
        raise UserLLMConfigError("API Key 过长（最多 500 字符）")


def get_user_llm_config(db: Session, user_id: UUID) -> UserLLMConfig | None:
    return db.execute(
        select(UserLLMConfig).where(UserLLMConfig.user_id == user_id)
    ).scalar_one_or_none()


def to_response(cfg: UserLLMConfig) -> UserLLMConfigResponse:
    """转为对外响应 — 不回传明文 Key，只回掩码。"""
    return UserLLMConfigResponse(
        provider=cfg.provider,
        base_url=cfg.base_url,
        model=cfg.model,
        api_key_masked=mask_secret(decrypt_secret(cfg.api_key_encrypted)),
        is_enabled=cfg.is_enabled,
        updated_at=cfg.updated_at,
    )


def save_user_llm_config(
    db: Session, user_id: UUID, body: UserLLMConfigSaveRequest
) -> UserLLMConfig:
    cfg = get_user_llm_config(db, user_id)
    api_key = (body.api_key or "").strip()
    if cfg and not api_key:
        # 未填新 Key 时沿用已保存的 Key
        api_key = decrypt_secret(cfg.api_key_encrypted)
    _validate(body.base_url, body.model, api_key)

    if cfg:
        cfg.provider = body.provider
        cfg.base_url = body.base_url.rstrip("/")
        cfg.model = body.model.strip()
        cfg.api_key_encrypted = encrypt_secret(api_key)
        cfg.is_enabled = body.is_enabled
    else:
        cfg = UserLLMConfig(
            user_id=user_id,
            provider=body.provider,
            base_url=body.base_url.rstrip("/"),
            model=body.model.strip(),
            api_key_encrypted=encrypt_secret(api_key),
            is_enabled=body.is_enabled,
        )
        db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def delete_user_llm_config(db: Session, user_id: UUID) -> bool:
    cfg = get_user_llm_config(db, user_id)
    if not cfg:
        return False
    db.delete(cfg)
    db.commit()
    return True


def resolve_user_llm_override(db: Session, user_id: UUID) -> LLMOverride | None:
    """解密出用户自带的 LLM 调用参数；未配置或已停用时返回 None（走服务器默认）。"""
    cfg = get_user_llm_config(db, user_id)
    if not cfg or not cfg.is_enabled:
        return None
    api_key = decrypt_secret(cfg.api_key_encrypted)
    if not api_key:
        # SECRET_KEY 轮换导致解密失败：视为配置失效，回退服务器默认
        logger.warning("用户 %s 的 LLM Key 解密失败，回退服务器默认配置", user_id)
        return None
    return LLMOverride(api_key=api_key, model=cfg.model, base_url=cfg.base_url)


async def verify_user_llm(
    base_url: str, model: str, api_key: str, timeout: float = 15.0
) -> UserLLMVerifyResponse:
    """向 OpenAI 兼容端点发一次最小请求验证连通性。

    不落库、不写配额，仅用于设置页「测试连接」按钮。
    """
    _validate(base_url, model, api_key)
    url = base_url.rstrip("/") + "/chat/completions"
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
    except httpx.TimeoutException:
        return UserLLMVerifyResponse(ok=False, message="连接超时，请检查 Base URL 与网络")
    except httpx.HTTPError as e:
        return UserLLMVerifyResponse(ok=False, message=f"连接失败：{type(e).__name__}")
    latency_ms = int((time.monotonic() - start) * 1000)
    if resp.status_code == 200:
        return UserLLMVerifyResponse(ok=True, message="连接成功", latency_ms=latency_ms)
    if resp.status_code in (401, 403):
        return UserLLMVerifyResponse(ok=False, message="API Key 无效或无权限（401/403）")
    if resp.status_code == 404:
        return UserLLMVerifyResponse(
            ok=False, message="端点不存在（404），请检查 Base URL 是否包含版本路径"
        )
    detail = ""
    try:
        detail = str(resp.json().get("error", {}).get("message", ""))[:200]
    except Exception:
        pass
    return UserLLMVerifyResponse(
        ok=False,
        message=(
            f"服务返回 {resp.status_code}：{detail}" if detail else f"服务返回 {resp.status_code}"
        ),
    )
