"""行动任务中心 Schema — 对齐系统设计 §3.2.M2.3 接口契约（方案 C：契约先行）。

字段严格对齐契约 DTO，枚举字段按契约以 str + 注释形式声明（不额外收紧类型）。
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ActionCreateRequest(BaseModel):
    """创建行动项请求（§3.2.M2.3）。

    注：note / biz_fields 契约字段暂无存储列，创建时忽略（docstring 声明，
    不为契约扩展字段加列加迁移）。
    """

    # ===== 必填字段 =====
    # user_id 由登录态 token 推断（get_current_user），不在请求体传
    action_type: str = Field(
        ...,
        description="行动类型；枚举：read_article / finish_course / resume_revise / mock_interview / real_apply / get_offer / custom",
    )
    title: str = Field(..., max_length=200, description="行动标题；长度 ≤ 200")
    due_date: date = Field(..., description="计划完成日期；格式 年-月-日（如 2026-01-15）")
    # ===== 可选字段 =====
    source_decision_id: int | None = Field(None, description="来源决策分析 ID（决策中心联动）")
    note: str | None = Field(None, description="备注")
    # ===== 扩展字段 =====
    biz_fields: dict = Field(default_factory=dict, description="业务方扩展")


class ActionUpdateRequest(BaseModel):
    """更新行动项请求（部分更新，均可选）。"""

    title: str | None = Field(None, max_length=200, description="行动标题；长度 ≤ 200")
    due_date: date | None = Field(None, description="计划完成日期")
    status: str | None = Field(
        None,
        description="行动状态；枚举：PENDING / DONE / EXPIRED / CANCELED",
    )
    note: str | None = Field(None, description="备注")


class CheckinRequest(BaseModel):
    """行动打卡请求（§3.2.M2.3）。"""

    # ===== 必填字段 =====
    action_id: int = Field(..., description="行动 ID；必须存在且属于当前用户")
    # user_id 由登录态 token 推断（get_current_user），不在请求体传
    completed_at: datetime = Field(..., description="打卡时间")
    # ===== 可选字段 =====
    evidence_url: str | None = Field(None, max_length=500, description="完成证据链接（完整版）")
    note: str | None = Field(None, max_length=500, description="打卡备注")


class StreakVO(BaseModel):
    """连续天数统计 VO（§3.2.M2.3）。"""

    # ===== 基本信息 =====
    user_id: UUID = Field(..., description="用户 ID")
    # ===== 业务字段 =====
    current_streak_days: int = Field(..., description="当前连续天数")
    longest_streak_days: int = Field(..., description="历史最长连续天数")
    last_checkin_date: date | None = Field(None, description="最近打卡日期")
    # ===== 状态字段 =====
    streak_status: str = Field(..., description="枚举：ACTIVE / BROKEN / NEVER")

    model_config = {"from_attributes": True}


class ActionVO(BaseModel):
    """行动项 VO（按 t_action 模型字段推导）。"""

    id: int = Field(..., description="行动 ID")
    user_id: UUID = Field(..., description="用户 ID")
    action_type: str = Field(..., description="行动类型")
    title: str = Field(..., description="行动标题")
    due_date: date = Field(..., description="计划完成日期")
    source_decision_id: int | None = Field(None, description="来源决策分析 ID")
    weight: int = Field(..., description="行动权重")
    status: str = Field(..., description="行动状态；枚举：PENDING / DONE / EXPIRED / CANCELED")
    created_time: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class ActionListVO(BaseModel):
    """行动列表 VO。"""

    items: list[ActionVO] = Field(..., description="行动列表")
    total: int = Field(..., description="总数")


class CheckinVO(BaseModel):
    """打卡记录 VO（按 t_action_checkin 模型字段推导）。"""

    id: int = Field(..., description="打卡 ID")
    action_id: int = Field(..., description="行动 ID")
    user_id: UUID = Field(..., description="用户 ID")
    completed_at: datetime = Field(..., description="打卡时间")
    evidence_url: str | None = Field(None, description="完成证据链接")
    note: str | None = Field(None, description="打卡备注")
    biz_req_no: str = Field(..., description="业务请求号（幂等键）")

    model_config = {"from_attributes": True}


class CheckinListVO(BaseModel):
    """打卡历史列表 VO。"""

    items: list[CheckinVO] = Field(..., description="打卡记录列表")
    total: int = Field(..., description="总数")


class ActionWeightVO(BaseModel):
    """行动权重 VO（按 t_action_weight 模型字段推导）。"""

    id: int = Field(..., description="权重配置 ID")
    action_type: str = Field(..., description="行动类型")
    weight: int = Field(..., description="权重值")
    weight_label: str = Field(..., description="权重标签")
    enabled: bool = Field(..., description="是否启用")

    model_config = {"from_attributes": True}


class ActionWeightListVO(BaseModel):
    """行动权重列表 VO。"""

    items: list[ActionWeightVO] = Field(..., description="权重配置列表")
    total: int = Field(..., description="总数")
