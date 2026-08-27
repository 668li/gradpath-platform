"""成长档案中心 Schema — 对齐系统设计 §3.2.M3.3 接口契约（方案 C：契约先行）。

字段严格对齐契约 DTO，枚举字段按契约以 str + 注释形式声明。
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GrowthTrajectoryCreateRequest(BaseModel):
    """记录成长轨迹事件请求（§3.2.M3.3）。"""

    # ===== 必填字段 =====
    # user_id 由登录态 token 推断（get_current_user），不在请求体传
    event_type: str = Field(
        ...,
        description="事件类型；枚举：action_checkin / review_completed / milestone",
    )
    event_payload: dict = Field(..., description="事件负载（打卡 / 复盘 / 里程碑明细）")
    occurred_at: datetime = Field(..., description="事件发生时间")
    # ===== 可选字段 =====
    source_event_id: str | None = Field(None, max_length=64, description="上游事件幂等 ID")


class GrowthTrajectoryVO(BaseModel):
    """成长轨迹事件 VO（按 t_growth_trajectory 模型字段推导）。"""

    id: int = Field(..., description="轨迹事件 ID")
    user_id: UUID = Field(..., description="用户 ID")
    event_type: str = Field(..., description="事件类型")
    event_payload: dict = Field(..., description="事件负载")
    occurred_at: datetime = Field(..., description="事件发生时间")
    source_event_id: str | None = Field(None, description="上游事件幂等 ID")

    model_config = {"from_attributes": True}


class GrowthTrajectoryListVO(BaseModel):
    """成长轨迹时间轴 VO。"""

    items: list[GrowthTrajectoryVO] = Field(..., description="轨迹事件列表")
    total: int = Field(..., description="总数")


class GrowthArchiveVO(BaseModel):
    """档案聚合 VO（§3.2.M3.3）。"""

    # ===== 基本信息 =====
    user_id: UUID = Field(..., description="用户 ID")
    # ===== 业务字段 =====
    action_completion_rate: float = Field(..., description="行动完成率；0.0~1.0，保留 2 位小数")
    total_actions: int = Field(..., description="累计行动数")
    completed_actions: int = Field(..., description="已完成行动数")
    streak_days: int = Field(..., description="当前 Streak Days")
    weighted_action_score: float = Field(..., description="加权行动完成分（D18 北极星指标）")
    # ===== 状态字段 =====
    archive_status: str = Field(..., description="枚举：ACTIVE / STALE")
    # ===== 时间字段 =====
    updated_at: datetime = Field(..., description="最近聚合时间")

    model_config = {"from_attributes": True}


class GrowthStatsVO(BaseModel):
    """成长统计 VO（行动完成率 + Streak 统计）。"""

    user_id: UUID = Field(..., description="用户 ID")
    action_completion_rate: float = Field(..., description="行动完成率；0.0~1.0")
    current_streak_days: int = Field(..., description="当前连续天数")
    longest_streak_days: int = Field(..., description="历史最长连续天数")
    total_actions: int = Field(..., description="累计行动数")
    completed_actions: int = Field(..., description="已完成行动数")
