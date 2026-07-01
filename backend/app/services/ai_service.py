# backend/app/services/ai_service.py
"""统一 AI 服务层 — 封装 LLM 调用。

复用 ``config.py`` 的 ``LLM_API_KEY`` / ``LLM_MODEL`` / ``LLM_BASE_URL``，
调用方式与 ``pipeline/extractor.py`` 的 ``call_llm`` 一致（httpx POST，OpenAI 兼容接口）。

- 支持 system_prompt + context injection
- ``LLM_API_KEY`` 为空时抛出 ``AIServiceNotConfigured`` 异常，API 层返回 503
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AIServiceNotConfigured(Exception):
    """LLM_API_KEY 未配置时抛出。"""

    pass


class AIService:
    """LLM 调用服务（OpenAI 兼容接口）。"""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.base_url = settings.LLM_BASE_URL

    def _check_config(self):
        if not self.api_key:
            raise AIServiceNotConfigured("LLM_API_KEY 未配置")

    def chat(self, system_prompt: str, user_content: str, timeout: int = 30) -> str:
        """调用 LLM，返回文本响应。

        Args:
            system_prompt: 系统提示词（角色设定 + 输出格式约束）
            user_content: 用户消息内容（含 context 与请求）
            timeout: 请求超时秒数，默认 30

        Returns:
            LLM 返回的文本（通常是 JSON 字符串）

        Raises:
            AIServiceNotConfigured: LLM_API_KEY 未配置
            httpx.TimeoutException: 请求超时
            httpx.HTTPStatusError: HTTP 非 2xx
        """
        self._check_config()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.7,
        }
        logger.info("LLM 调用开始: model=%s", self.model)
        try:
            resp = httpx.post(
                f"{self.base_url}chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]
            logger.info("LLM 调用完成: %d 字符", len(result))
            return result
        except Exception as e:
            logger.error("LLM 调用失败: %s", e)
            raise
