"""7天微行动 Schemas — 与后端 app/models/micro_action.py 对齐。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MicroActionPlanCreate(BaseModel):
    """创建 7 天微行动计划请求体。"""

    target_path: str = Field(..., description="目标路径：kaoyan/employment/civil_service")
    target_role: str | None = Field(None, max_length=100, description="可选，具体岗位/院校/职位")


class MicroActionTaskResponse(BaseModel):
    """单日任务响应。"""

    id: UUID
    day_number: int
    task_type: str
    title: str
    description: str
    estimated_minutes: int
    status: str
    completed_at: datetime | None
    user_response: str | None
    insight: str | None

    model_config = {"from_attributes": True}


class MicroActionPlanResponse(BaseModel):
    """7 天微行动计划响应。"""

    id: UUID
    target_path: str
    target_role: str | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    tasks: list[MicroActionTaskResponse]
    progress: int = Field(..., ge=0, le=100, description="完成任务数/7 * 100")
    self_discovery_report: str | None = None

    model_config = {"from_attributes": True}


class TaskCompleteRequest(BaseModel):
    """完成任务请求体。"""

    # 允许不写字完成任务（P0-3）：空串合法，service 层有兜底文案
    user_response: str = Field(default="", description="用户完成任务后的记录（可选）")
