"""考公时间线 VO（feature 001 / M2）— 对齐 contracts/timeline-api.md。

契约级负断言：UNKNOWN ⇒ planned_date/planned_end_date/predict_basis 必空——
响应模型层再拦一次，防任何旁路写入让前端"猜日期"（宪法 4）。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.exam_timeline import DateStatus, NodeStage


class DarkKnowledgeBrief(BaseModel):
    """节点卡暗知识角标（FR9；confidence 取自 importance 列）。"""

    id: str
    title: str
    confidence: str


class NextNodeBrief(BaseModel):
    stage_key: NodeStage
    planned_date: date | None = None
    date_status: DateStatus
    is_predictive: bool = False


class NodeVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    stage_key: NodeStage
    title: str
    seq: int
    date_status: DateStatus
    planned_date: date | None = None
    planned_end_date: date | None = None
    predict_basis: str | None = None
    official_entry_url: str | None = None
    source_url: str | None = None
    collected_at: datetime | None = None
    evidence_id: str | None = None
    materials: list[Any] = []
    action_guide: str = ""
    verifiable: bool = True  # False=暂无可核验来源（UNKNOWN 且有推算/事实空窗）
    dark_knowledge: list[DarkKnowledgeBrief] = []

    @model_validator(mode="after")
    def _honesty(self) -> NodeVO:
        # 契约级负断言（违约即 500——保证绝不以 200 出现在响应面）
        if self.date_status == DateStatus.UNKNOWN:
            if (
                self.planned_date is not None
                or self.planned_end_date is not None
                or self.predict_basis is not None
            ):
                raise ValueError("UNKNOWN 节点不得携带日期/推算依据（宪法 4）")
        elif self.date_status == DateStatus.OFFICIAL:
            if not self.source_url or not self.evidence_id:
                raise ValueError("OFFICIAL 节点必须带源带证据（FR-E1）")
        return self


class ExamListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    track: str
    year: int
    status: str
    official_home_url: str
    next_node: NextNodeBrief | None = None


class ExamDetail(ExamListItem):
    nodes: list[NodeVO] = []


class SubscribeResult(BaseModel):
    exam_code: str
    subscribed: bool = True
    notify_channels: list[str] = []


class ProgressVO(BaseModel):
    reached: int = 0
    done: int = 0
    feedback_rate: float | None = None  # 有回传的已到达节点占比（北极星口径见 docs/度量口径.md）


class MyExamItem(BaseModel):
    exam: ExamListItem
    subscribed: bool = True  # 退订（notify 空）但保留回传史的订阅仍列出
    progress: ProgressVO
    completion_rate: float | None = None  # 条件完成率=done/已到达窗口（北极星分子口径）
    next_node: NextNodeBrief | None = None


class FeedbackRequest(BaseModel):
    status: Literal["done", "uncertain", "skipped"]
