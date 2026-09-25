"""Decision OS 领域模型 — 决策验证闭环的一等实体（D9 拍板 09-25）。

闭环：Decision → Hypothesis → DecisionEvidence → ValidationAction → DecisionOutcome
→ DecisionReflection。术语定义见仓库 CONTEXT.md。

设计拍板约束：
- Evidence 命名 DecisionEvidence（Evidence 已被时间线域 TimelineEvidence 占用）；
- Action 新建 ValidationAction（既有三套行动系统语义不合，收敛挂账）；
- Decision 不新建表：扩展 destination_decisions（Q5，见 docs/adr/004）；
- 证据创建一律 internal_unverified：库里有 ≠ 已验证；externally_verified 必须带
  verification_source（服务层强制，模型层不做业务）。

枚举成员名=值（本仓约定），与迁移 e9c2a7d4f1b3 的字面量严格一致。
"""

import enum
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class HypothesisImportance(str, enum.Enum):
    critical = "critical"
    high = "high"
    supporting = "supporting"


class HypothesisStatus(str, enum.Enum):
    untested = "untested"
    supporting = "supporting"
    refuted = "refuted"
    obsolete = "obsolete"


class EvidenceSourceType(str, enum.Enum):
    official = "official"
    peer = "peer"
    media = "media"
    internal_db = "internal_db"
    user_observed = "user_observed"
    ai_generated = "ai_generated"


class EvidenceReliability(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EvidenceStance(str, enum.Enum):
    supporting = "supporting"
    contradicting = "contradicting"
    neutral = "neutral"


class EvidenceVerificationStatus(str, enum.Enum):
    internal_unverified = "internal_unverified"
    externally_verified = "externally_verified"
    contradicted = "contradicted"
    stale = "stale"
    unverifiable = "unverifiable"


class ValidationActionStatus(str, enum.Enum):
    todo = "todo"
    doing = "doing"
    done = "done"
    skipped = "skipped"


class ActionResultStance(str, enum.Enum):
    hypothesis_supported = "hypothesis_supported"
    hypothesis_weakened = "hypothesis_weakened"
    inconclusive = "inconclusive"


class DecisionOutcomeKind(str, enum.Enum):
    direct = "direct"
    partial = "partial"
    unobservable = "unobservable"
    counterfactual_unknown = "counterfactual_unknown"


class ReflectionMatchStatus(str, enum.Enum):
    matched = "matched"
    partial = "partial"
    missed = "missed"
    unknown = "unknown"


class DecisionHypothesis(UUIDMixin, TimestampMixin, Base):
    """关键假设：若本判断不成立，决策即不成立。可证伪、挂证据与验证行动。"""

    __tablename__ = "decision_hypotheses"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[HypothesisImportance] = mapped_column(
        Enum(HypothesisImportance, name="decision_hypothesis_importance"),
        nullable=False,
        default=HypothesisImportance.high,
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[HypothesisStatus] = mapped_column(
        Enum(HypothesisStatus, name="decision_hypothesis_status"),
        nullable=False,
        default=HypothesisStatus.untested,
    )
    # 该假设被证伪时决策会发生什么
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 验证结论的自由文本摘要（由用户复盘时填写）
    result: Mapped[str | None] = mapped_column(Text, nullable=True)


class DecisionEvidence(UUIDMixin, TimestampMixin, Base):
    """决策证据：一条带来源、立场、可靠性与验证状态的 claim。

    provider 标注产出方（如 internal:grad_intel / external:web），它只是出处标注，
    不改变 verification_status——状态只能被显式验证动作推进。
    """

    __tablename__ = "decision_evidence"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    hypothesis_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("decision_hypotheses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[EvidenceSourceType] = mapped_column(
        Enum(EvidenceSourceType, name="decision_evidence_source_type"),
        nullable=False,
        default=EvidenceSourceType.user_observed,
    )
    reliability: Mapped[EvidenceReliability] = mapped_column(
        Enum(EvidenceReliability, name="decision_evidence_reliability"),
        nullable=False,
        default=EvidenceReliability.medium,
    )
    stance: Mapped[EvidenceStance] = mapped_column(
        Enum(EvidenceStance, name="decision_evidence_stance"),
        nullable=False,
        default=EvidenceStance.neutral,
    )
    observed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verification_status: Mapped[EvidenceVerificationStatus] = mapped_column(
        Enum(EvidenceVerificationStatus, name="decision_evidence_verification_status"),
        nullable=False,
        default=EvidenceVerificationStatus.internal_unverified,
    )
    verification_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DecisionValidationAction(UUIDMixin, TimestampMixin, Base):
    """验证行动：为降低某个假设的不确定性设计的最小真实行动。

    与既有三套行动系统（micro_action / t_action / DailyAction）语义不同：
    本表必须能回答"验证哪个假设、降低哪种不确定性、结果可能改变什么"。
    """

    __tablename__ = "decision_validation_actions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hypothesis_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("decision_hypotheses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_information_gain: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ValidationActionStatus] = mapped_column(
        Enum(ValidationActionStatus, name="decision_action_status"),
        nullable=False,
        default=ValidationActionStatus.todo,
    )
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_stance: Mapped[ActionResultStance | None] = mapped_column(
        Enum(ActionResultStance, name="decision_action_result_stance"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DecisionOutcome(UUIDMixin, TimestampMixin, Base):
    """决策结果：现实反馈。不强迫二值化，允许不可观测与反事实未知。"""

    __tablename__ = "decision_outcomes"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[DecisionOutcomeKind] = mapped_column(
        Enum(DecisionOutcomeKind, name="decision_outcome_kind"),
        nullable=False,
        default=DecisionOutcomeKind.direct,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    observed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DecisionReflection(UUIDMixin, TimestampMixin, Base):
    """复盘：预测误差/错误假设/遗漏因素/教训；教训可沉淀为原则。"""

    __tablename__ = "decision_reflections"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    wrong_assumption: Mapped[str | None] = mapped_column(Text, nullable=True)
    omitted_factor: Mapped[str | None] = mapped_column(Text, nullable=True)
    lesson: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_status: Mapped[ReflectionMatchStatus] = mapped_column(
        Enum(ReflectionMatchStatus, name="decision_reflection_match_status"),
        nullable=False,
        default=ReflectionMatchStatus.unknown,
    )
    # 从本次复盘中提炼、可写入 user_memory(principle) 的候选原则
    new_principle: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
