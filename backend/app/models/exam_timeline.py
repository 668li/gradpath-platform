"""考公流程时间线伴随模型（feature 001）— 信息差伴随层的脊柱。

宪法级设计（.specify/memory/constitution.md 1/4 + spec §2.5）：
- 日期诚实状态机：date_status ∈ {OFFICIAL, PREDICTED, UNKNOWN}。
  UNKNOWN ⇒ planned_date 必空；OFFICIAL ⇒ source_url/collected_at/evidence_id 必填。
- OFFICIAL 的唯一产生方式是证据链（TimelineEvidence 行 + require_evidence 闸），
  任何旁路写入在模型层之外由服务闸拒绝；状态机禁止 OFFICIAL 回退。
- 2027 推算锚点链（FR-E6）：PREDICTED 必须指向 2026 同环节的已证日期（predict_basis 留痕）。
"""

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class DateStatus(str, enum.Enum):
    """日期诚实三态（宪法 4）。"""

    OFFICIAL = "OFFICIAL"  # 官方公告明文（必须挂证据行）
    PREDICTED = "PREDICTED"  # 按已证实的上一年节奏推算（界面必标"预测"）
    UNKNOWN = "UNKNOWN"  # 无可靠信息——日期必空


class NodeStage(str, enum.Enum):
    """考公 12 环节词表（D6），对齐 CivilServiceDarkKnowledge 映射在 service 层。"""

    announce = "announce"  # 公告发布
    registration = "registration"  # 网上报名
    payment = "payment"  # 报名确认与缴费
    admission_ticket = "admission_ticket"  # 打印准考证
    written = "written"  # 笔试
    score = "score"  # 成绩查询/合格线
    adjustment = "adjustment"  # 调剂
    interview = "interview"  # 面试
    medical = "medical"  # 体检
    political = "political"  # 考察（政审）
    publicity = "publicity"  # 拟录用公示
    hire = "hire"  # 备案录用

    @classmethod
    def ordered(cls) -> list["NodeStage"]:
        """按流程顺序返回 12 环节（Enum 定义序即流程序）。"""
        return list(cls)


class EvidenceChannel(str, enum.Enum):
    """证据来源渠道：真实 HTTP 抓取 / 官方原文人工粘贴。"""

    fetch = "fetch"
    manual_paste = "manual_paste"


class ReminderKind(str, enum.Enum):
    """提醒提前量类型（D5）。"""

    heads_up = "heads_up"  # 公告 T-3 / 报名 T-3 / 笔试 T-7 等预告
    opening = "opening"  # 报名首日 / 查分开放日 / 准考证日
    deadline_t1 = "deadline_t1"  # 截止前一天
    dayof = "dayof"  # 当天（笔试日等）
    followup = "followup"  # 通知后跟进（面试/体检/政审）


class ReminderTone(str, enum.Enum):
    """文案语气分级（D2 单点闸的输入维度）。"""

    assertive = "assertive"  # 断言式（"明天截止"）——仅 OFFICIAL 可用
    tentative = "tentative"  # 试探式（"预计近期，建议收藏入口"）


class NodeFeedbackStatus(str, enum.Enum):
    """节点回传三态（不建"未完成"负值——未回传即缺行）。"""

    done = "done"
    uncertain = "uncertain"
    skipped = "skipped"


class Exam(UUIDMixin, TimestampMixin, Base):
    """考次：如 guokao-2026 / guokao-2027 / guangdong-shengkao-2026。"""

    __tablename__ = "t_exam"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    track: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="guokao",
        comment="guokao/shengkao/buwei_shengkao…可扩展",
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    official_home_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="upcoming",
        comment="upcoming/ongoing/closed（closed=周期走完仍可浏览）",
    )

    nodes: Mapped[list["ExamNode"]] = relationship(
        back_populates="exam", order_by="ExamNode.node_seq"
    )


class TimelineEvidence(UUIDMixin, TimestampMixin, Base):
    """证据链实体（FR-E1）：OFFICIAL 日期的唯一合法来源凭证。

    写路径唯一 = timeline_service.require_evidence()；行本身可审计到人/任务。
    """

    __tablename__ = "t_timeline_evidence"

    channel: Mapped[EvidenceChannel] = mapped_column(
        Enum(EvidenceChannel, name="evidencechannel"), nullable=False
    )
    source_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="域名须 *.gov.cn 政府域"
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_sha: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="抓取正文/粘贴文本 sha256"
    )
    matched_excerpt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="命中日期的正文片段（含日期串±60字）"
    )
    pasted_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="manual_paste 全量原文留档"
    )
    recorded_by: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="user email / seed_fetch:<job_id>"
    )


class ExamNode(UUIDMixin, TimestampMixin, Base):
    """12 环节节点。诚实字段组合校验在服务闸 validate_honesty()，状态机禁回退。"""

    __tablename__ = "t_exam_node"
    __table_args__ = (UniqueConstraint("exam_id", "stage_key", name="uq_exam_node_stage"),)

    exam_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("t_exam.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_key: Mapped[NodeStage] = mapped_column(Enum(NodeStage, name="nodestage"), nullable=False)
    node_seq: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="1..12 流程顺序")
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    date_status: Mapped[DateStatus] = mapped_column(
        Enum(DateStatus, name="datestatus"), nullable=False, default=DateStatus.UNKNOWN
    )
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="UNKNOWN 必空")
    planned_end_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment="窗口型节点（报名起止）"
    )
    predict_basis: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="仅 PREDICTED：推算依据"
    )
    official_entry_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="OFFICIAL 必填"
    )
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="OFFICIAL 必填"
    )
    evidence_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("t_timeline_evidence.id"),
        nullable=True,
        comment="OFFICIAL 必填；其余必空",
    )
    materials: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, comment="[{name, note?}]"
    )
    action_guide: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="该做什么（人工撰写摘要）"
    )
    announced_via_announce_id: Mapped[str | None] = mapped_column(
        GUID(), nullable=True, comment="Phase 2 回填位（FR10），本期恒 NULL"
    )

    exam: Mapped["Exam"] = relationship(back_populates="nodes")
    evidence: Mapped[Optional["TimelineEvidence"]] = relationship()


class ExamSubscription(UUIDMixin, TimestampMixin, Base):
    """用户 × 考次订阅（唯一）。退订=置 notify_channels 空列表，保留回传史。"""

    __tablename__ = "t_exam_subscription"
    __table_args__ = (
        UniqueConstraint("user_id", "exam_id", name="uq_exam_subscription_user_exam"),
    )

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("t_exam.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notify_channels: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=lambda: ["inapp", "serverchan"]
    )

    exam: Mapped["Exam"] = relationship()


class NodeFeedback(UUIDMixin, TimestampMixin, Base):
    """节点回传（done/uncertain/skipped），喂北极星条件完成率。"""

    __tablename__ = "t_exam_node_feedback"
    __table_args__ = (
        UniqueConstraint("subscription_id", "node_id", name="uq_node_feedback_sub_node"),
    )

    subscription_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("t_exam_subscription.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("t_exam_node.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[NodeFeedbackStatus] = mapped_column(
        Enum(NodeFeedbackStatus, name="nodefeedbackstatus"), nullable=False
    )
    feedback_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TimelineReminderLog(UUIDMixin, TimestampMixin, Base):
    """提醒发送日志：unique(user,node,kind) = 幂等硬闸（D4，DB 约束非代码判断）。

    tone 落库供审计——验证 D2 文案分级闸在生产真实生效（测试+巡检断言
    tone=assertive ⇒ 关联节点 date_status=OFFICIAL）。
    """

    __tablename__ = "t_timeline_reminder_log"
    __table_args__ = (
        UniqueConstraint("user_id", "node_id", "kind", name="uq_reminder_user_node_kind"),
    )

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("t_exam_node.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[ReminderKind] = mapped_column(
        Enum(ReminderKind, name="reminderkind"), nullable=False
    )
    tone: Mapped[ReminderTone] = mapped_column(
        Enum(ReminderTone, name="remindertone"), nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channel: Mapped[str] = mapped_column(
        String(30), nullable=False, default="inapp", comment="inapp/serverchan"
    )
    notification_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
