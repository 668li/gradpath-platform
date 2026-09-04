# backend/app/schemas/user_llm_config.py
"""用户自带 LLM API 配置（BYOK）请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserLLMConfigSaveRequest(BaseModel):
    provider: str = Field(
        "custom", max_length=30, description="供应商标识：zhipu/deepseek/moonshot/openai/custom"
    )
    base_url: str = Field(
        ...,
        max_length=500,
        description="OpenAI 兼容接口根地址，如 https://open.bigmodel.cn/api/paas/v4/",
    )
    model: str = Field(..., max_length=100, description="模型名称，如 glm-4-flash")
    api_key: str = Field("", max_length=500, description="API Key；留空表示沿用已保存的 Key")
    is_enabled: bool = Field(True, description="是否启用自带配置（关闭则回退服务器默认）")


class UserLLMConfigResponse(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key_masked: str = Field(..., description="掩码后的 Key，如 ****abcd")
    is_enabled: bool
    updated_at: datetime | None = None


class UserLLMVerifyRequest(BaseModel):
    provider: str = Field("custom", max_length=30)
    base_url: str = Field(..., max_length=500)
    model: str = Field(..., max_length=100)
    api_key: str = Field("", max_length=500, description="留空则用已保存的 Key 验证")


class UserLLMVerifyResponse(BaseModel):
    ok: bool
    message: str
    latency_ms: int | None = None


class PlatformLLMStatusResponse(BaseModel):
    """平台内置 LLM（服务器默认 Key）可用性，供前端自适应文案。"""

    enabled: bool = Field(..., description="平台是否已配置 LLM_API_KEY")
    model: str = Field(..., description="平台默认模型（enabled 时生效）")
    daily_quota: int = Field(..., description="未自带 Key 用户的每日调用预算")
