# backend/app/services/ai_service.py
"""统一 AI 服务层 — 封装 LLM 调用。

复用 ``config.py`` 的 ``LLM_API_KEY`` / ``LLM_MODEL`` / ``LLM_BASE_URL``，
调用方式与 ``pipeline/extractor.py`` 的 ``call_llm`` 一致（httpx POST，OpenAI 兼容接口）。

- 支持 system_prompt + context injection
- ``LLM_API_KEY`` 为空时抛出 ``AIServiceNotConfigured`` 异常，API 层返回 503
- B8: 使用 tenacity 对超时/网络错误重试 3 次（指数退避，最大 10s），
  HTTPStatusError 不重试（避免对 4xx 浪费额度）
- A14: 在 chat 方法入口/出口埋点 LLM_CALL_COUNT / LLM_CALL_LATENCY 指标
"""
import logging
import time

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)


class AIServiceNotConfigured(Exception):
    """LLM_API_KEY 未配置时抛出。"""

    pass


class AIServiceRetryExhausted(Exception):
    """tenacity 重试耗尽后抛出（包装最后一次原始异常）。

    API 层据此返回 504，区分「超时/网络抖动重试耗尽」与「LLM 业务错误」。
    """

    def __init__(self, last_exception: BaseException):
        self.last_exception = last_exception
        super().__init__(
            f"AI 服务重试耗尽: {type(last_exception).__name__}: {last_exception}"
        )


# B8: tenacity 重试策略
# - 最多 3 次（含首次）
# - 指数退避：1s, 2s, 4s, ... 最大 10s
# - 只重试超时与网络错误；HTTPStatusError（4xx/5xx 业务响应）不重试
RETRYABLE_EXCEPTIONS = (httpx.TimeoutException, httpx.NetworkError)


def _build_retry_config() -> AsyncRetrying:
    """构造 tenacity AsyncRetrying 实例。

    使用 AsyncRetrying 而非 @retry 装饰器，便于：
    - 在 chat 内部捕获 RetryError 并包装为 AIServiceRetryExhausted
    - reraise=True 保证最终抛出原始异常而非 RetryError
    """
    return AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True,
    )


class AIService:
    """LLM 调用服务（OpenAI 兼容接口）。"""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.base_url = settings.LLM_BASE_URL

    def _check_config(self):
        if not self.api_key:
            raise AIServiceNotConfigured("LLM_API_KEY 未配置")

    async def chat(self, system_prompt: str, user_content: str, timeout: int = 30) -> str:
        """调用 LLM，返回文本响应。

        Args:
            system_prompt: 系统提示词（角色设定 + 输出格式约束）
            user_content: 用户消息内容（含 context 与请求）
            timeout: 请求超时秒数，默认 30

        Returns:
            LLM 返回的文本（通常是 JSON 字符串）

        Raises:
            AIServiceNotConfigured: LLM_API_KEY 未配置
            AIServiceRetryExhausted: 超时/网络错误重试耗尽（包装原始异常）
            httpx.HTTPStatusError: HTTP 非 2xx（不重试，直接抛出）
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

        # A14: 记录 LLM 调用延迟与计数（成功/失败分别打标）
        _start_ts = time.monotonic()
        _status_label = "success"

        async def _do_call() -> str:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.base_url}chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()["choices"][0]["message"]["content"]
                logger.info("LLM 调用完成: %d 字符", len(result))
                return result

        # B8: tenacity 重试只针对超时/网络错误；HTTPStatusError 直接抛出
        try:
            async for attempt in _build_retry_config():
                with attempt:
                    return await _do_call()
        except RETRYABLE_EXCEPTIONS as e:
            # 重试耗尽：tenacity reraise=True 会抛出最后一次的原始异常
            logger.error("LLM 调用重试耗尽: %s", e)
            _status_label = "timeout"
            raise AIServiceRetryExhausted(e)
        except Exception as e:
            # 其他异常（如 HTTPStatusError）原样抛出，不包装
            logger.error("LLM 调用失败: %s", e)
            _status_label = "error"
            raise
        finally:
            # A14: 不论成功/失败都记录指标
            try:
                from app.metrics import record_llm_call
                record_llm_call(
                    model=self.model or "unknown",
                    status=_status_label,
                    duration_seconds=time.monotonic() - _start_ts,
                )
            except Exception:
                pass
