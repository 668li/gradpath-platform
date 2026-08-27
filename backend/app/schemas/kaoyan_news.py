"""考研资讯 Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KaoyanNewsBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="标题")
    summary: str | None = Field(None, max_length=500, description="摘要")
    content: str | None = Field(None, description="正文内容")
    source_platform: str = Field(default="rss", description="来源平台")
    source_url: str = Field(..., description="来源链接")
    published_at: datetime | None = Field(None, description="发布时间")
    category: str = Field(default="general", description="分类")
    tags: list[str] = Field(default_factory=list, description="标签")


class KaoyanNewsCreate(KaoyanNewsBase):
    """创建考研资讯"""

    pass


class KaoyanNewsUpdate(BaseModel):
    """更新考研资讯"""

    title: str | None = Field(None, min_length=1, max_length=200)
    summary: str | None = Field(None, max_length=500)
    content: str | None = None
    source_url: str | None = None
    published_at: datetime | None = None
    category: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class KaoyanNewsResponse(KaoyanNewsBase):
    """考研资讯响应（含 Phase A/C 提纯字段：质量分级、AI 摘要、关键时间点）"""

    id: UUID
    crawled_at: datetime
    status: str = Field(..., description="审核状态")
    # === 提纯与质量（信息差升级）===
    ai_summary: str | None = Field(None, description="AI 摘要（LLM 增强；无则为规则版摘要或空）")
    quality_score: int | None = Field(None, ge=0, le=100, description="质量分 0-100")
    quality_grade: str | None = Field(None, description="质量等级 A/B/C/D")
    quality_reasons: list[str] | None = Field(
        None, description="质量扣分原因（Phase I 逐维可解释，徽章 hover 展示）"
    )
    key_dates: list[dict] = Field(
        default_factory=list, description="关键时间点 [{label, date, end_date?}]"
    )
    structured_meta: dict | None = Field(
        None, description="结构化元信息（Phase G 规则抽取：招生人数/考试科目/参考书目）"
    )
    is_expired: bool = Field(default=False, description="时效过期标记")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KaoyanNewsListResponse(BaseModel):
    """考研资讯列表响应"""

    items: list[KaoyanNewsResponse]
    total: int
    page: int
    page_size: int
