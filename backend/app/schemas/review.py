"""复盘中心 Schema — 对齐系统设计 §3.2.M4.3 接口契约（方案 C：契约先行）。

字段严格对齐契约 DTO；枚举字段按契约以 str + 注释形式声明。
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    """创建复盘记录请求（§3.2.M4.3）。"""

    # ===== 必填字段 =====
    # user_id 由登录态 token 推断（get_current_user），不在请求体传
    review_type: str = Field(
        ...,
        description="复盘类型；枚举：daily / weekly / monthly / milestone",
    )
    period_start: date = Field(..., description="复盘周期开始")
    period_end: date = Field(..., description="复盘周期结束")
    content: str = Field(..., max_length=5000, description="复盘内容；长度 ≤ 5000")
    # ===== 可选字段 =====
    action_refs: list = Field(
        default_factory=list,
        description='关联行动 ID 列表；落库时转换为 {"action_ids": [...]} dict（JSONB）',
    )
    mood_score: int | None = Field(None, ge=1, le=5, description="主观评分；范围 1~5")


class ReviewVO(BaseModel):
    """复盘记录 VO（按 t_review_record 模型字段推导）。"""

    id: int = Field(..., description="复盘记录 ID")
    user_id: UUID = Field(..., description="用户 ID")
    review_type: str = Field(
        ..., description="复盘类型；枚举：daily / weekly / monthly / milestone"
    )
    period_start: date = Field(..., description="复盘周期开始")
    period_end: date = Field(..., description="复盘周期结束")
    content: str = Field(..., description="复盘内容")
    action_refs: dict | None = Field(None, description="关联行动引用（JSONB）")
    mood_score: int | None = Field(None, description="主观评分；范围 1~5")
    status: str = Field(..., description="状态；枚举：DRAFT / PENDING / COMPLETED / FAILED")
    created_time: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class ReviewDetailVO(ReviewVO):
    """复盘详情 VO = ReviewVO + AI 分析字段。"""

    ai_summary: str | None = Field(None, description="AI 复盘摘要")
    ai_insights: dict | None = Field(None, description="AI 洞察（JSONB）")
    ai_suggestions: dict | None = Field(None, description="AI 建议（JSONB）")
    uncertainty_score: float | None = Field(
        None, ge=0.0, le=1.0, description="不确定性评分；0.0~1.0"
    )


class ReviewPageResponse(BaseModel):
    """复盘列表分页响应（common.py 无 PageResponse，本模块自持 items+total 风格）。"""

    items: list[ReviewVO] = Field(..., description="复盘记录列表")
    total: int = Field(..., description="总数")


class AIReviewRequest(BaseModel):
    """触发 AI 复盘分析请求（§3.2.M4.3）。"""

    # ===== 必填字段 =====
    review_id: int = Field(..., description="复盘记录 ID")
    # user_id 由登录态 token 推断（get_current_user），不在请求体传
    # ===== 可选字段 =====
    focus_areas: list = Field(default_factory=list, description="关注维度；默认全维度")
    temperature: float = Field(0.3, ge=0.0, le=1.0, description="LLM 温度；默认 0.3")


class AIReviewVO(BaseModel):
    """AI 复盘结果 VO（§3.2.M4.3）。"""

    # ===== 基本信息 =====
    review_id: int = Field(..., description="复盘记录 ID")
    # ===== 业务字段 =====
    summary: str = Field(..., description="AI 复盘摘要")
    insights: list = Field(..., description="洞察列表（每条含 insight + evidence）")
    suggestions: list = Field(..., description="建议列表")
    uncertainty_score: float = Field(..., ge=0.0, le=1.0, description="不确定性评分；0.0~1.0")
    # ===== 状态字段 =====
    status: str = Field(..., description="枚举：PENDING / COMPLETED / FAILED")
    # ===== 时间字段 =====
    created_at: datetime = Field(..., description="创建时间")
