"""考研经验贴 Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# === 经验贴基础信息 ===
class ExperiencePostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="标题")
    summary: str | None = Field(None, max_length=500, description="摘要")
    # 修复: FASTAPI-VALID-001 — content 加 max_length 防止超大文本攻击
    content: str = Field(..., min_length=1, max_length=50000, description="正文内容")
    tags: list[str] = Field(default_factory=list, description="标签")
    category: str = Field(default="general", max_length=50, description="分类")
    is_anonymous: bool = Field(default=False, description="是否匿名")
    source_url: str | None = Field(None, max_length=2000, description="来源链接")


class ExperiencePostCreate(ExperiencePostBase):
    """创建经验贴"""

    pass


class ExperiencePostUpdate(BaseModel):
    """更新经验贴"""

    title: str | None = Field(None, min_length=1, max_length=200)
    summary: str | None = Field(None, max_length=500)
    content: str | None = Field(None, min_length=1, max_length=50000)
    tags: list[str] | None = None
    category: str | None = Field(None, max_length=50)
    is_anonymous: bool | None = None
    source_url: str | None = Field(None, max_length=2000)


class ExperiencePostResponse(ExperiencePostBase):
    """经验贴响应"""

    # 来源归属是服务端事实（用户创建强制 "user"），不在创建契约中暴露
    source_platform: str = Field(default="user", max_length=50, description="来源平台")
    id: UUID
    user_id: UUID
    view_count: int = Field(..., description="浏览数")
    like_count: int = Field(..., description="点赞数")
    comment_count: int = Field(..., description="评论数")
    external_view_count: int = Field(default=0, description="外部平台浏览数")
    external_like_count: int = Field(default=0, description="外部平台点赞数")
    is_pinned: bool = Field(..., description="是否置顶")
    status: str = Field(..., description="审核状态")
    is_verified: bool = Field(..., description="是否已验证")
    created_at: datetime
    updated_at: datetime
    author_name: str | None = Field(None, description="作者显示名")
    author_avatar: str | None = Field(None, description="作者头像URL")
    # Phase G 提纯字段：质量分/软广标注/结构化元信息（LLM 摘要挂载点，未启用时为 None）
    quality_score: int | None = Field(None, description="质量分 0-100")
    quality_grade: str | None = Field(None, max_length=2, description="质量等级 A/B/C/D")
    quality_reasons: list[str] | None = Field(
        None, description="质量扣分原因（Phase I 逐维可解释，徽章 hover 展示）"
    )
    ai_summary: str | None = Field(None, description="LLM 生成摘要（挂载点，未启用为 None）")
    structured_meta: dict | None = Field(
        None, description="结构化元信息（方法/适用人群/学科/阶段/院校/目标分）"
    )
    is_promotion: bool | None = Field(None, description="是否疑似软广/引流（标注不下架）")
    promotion_confidence: float | None = Field(None, description="软广置信度 0-1")
    promotion_reason: str | None = Field(None, description="软广判定依据")

    model_config = ConfigDict(from_attributes=True)


class ExperiencePostListResponse(BaseModel):
    """经验贴列表响应"""

    items: list[ExperiencePostResponse]
    total: int
    page: int
    page_size: int
