"""Decision OS 服务层 — 决策验证闭环（D9 拍板 09-25）。

纪律：
- 所有权：所有读写先过 user_id 过滤；查不到一律按"不存在"处理（不泄露他用户资源）。
- 证据闸：创建一律 internal_unverified；externally_verified 必须带 verification_source；
  本服务层是唯一能推进 verification_status 的地方（AI/爬虫/内部库都只是 Provider）。
- 不替用户决定：complete_action 只有在请求显式携带 hypothesis_status_update 时才改
  假设状态；AI 结构化只产出草稿，confirm 必须由用户发起。
- legacy 兼容：confirm_draft 把假设 statement 镜像进 destination_decisions.assumptions，
  让旧的决策中心视图继续可读；新逻辑一律读 decision_hypotheses。
"""

import json
import logging
import re
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.cache import invalidate_user_context
from app.core.exceptions import NotFoundError, ValidationFailedError
from app.models.decision_os import (
    DecisionEvidence,
    DecisionHypothesis,
    DecisionOutcome,
    DecisionReflection,
    DecisionValidationAction,
    EvidenceStance,
    EvidenceVerificationStatus,
    HypothesisImportance,
    ValidationActionStatus,
)
from app.models.destination_decision import DecisionStatus, DestinationDecision
from app.schemas.decision_os import (
    ActionCompleteRequest,
    ConfirmDraftRequest,
    EvidenceCreate,
    EvidenceUpdate,
    EvidenceVerifyRequest,
    HypothesisCreate,
    HypothesisUpdate,
    OutcomeCreate,
    ReflectionCreate,
    StructuredDraft,
    ValidationActionCreate,
    ValidationActionUpdate,
)
from app.services.ai_orchestrator import AIOrchestrator
from app.services.decision_service import get_decision

logger = logging.getLogger(__name__)

_DRAFT_SYSTEM_PROMPT = """你是一位决策分析师（Decision Analyst）。用户用自然语言描述了一个正在面对的重大决策。

你的任务是把这段话结构化为一张"决策卡"草稿，帮助用户去验证这个决策——而不是替用户做决定。

规则：
- question：用一句中性的疑问句重述这个决策，不得包含"建议"或"应该"。
- options：用户提到的候选选项（0-4 个，没提到就给空数组）。
- constraints：用户明确说出的约束（时间/钱/家庭/能力等），不要编造。
- hypotheses：3-6 条关键假设。每条必须是"如果这个判断不成立，这个决策就不成立"的可证伪命题；
  禁止写成建议、行动或结论。importance 取值：critical=被证伪则决策直接崩塌 / high=严重影响 / supporting=次要。
  impact 一句话写清"若被证伪，决策会发生什么"。
- evidence_needs：验证这些假设最缺什么证据，每条一句话。
- desired_outcome：用户期望的结果；没提就 null。context：补充背景；没有就 null。

严格输出 JSON（不要输出 JSON 以外的任何内容）：
{
  "question": "...",
  "context": "..." 或 null,
  "options": ["..."],
  "constraints": ["..."],
  "desired_outcome": "..." 或 null,
  "hypotheses": [{"statement": "...", "importance": "critical", "impact": "..."}],
  "evidence_needs": ["..."]
}"""

_VALID_IMPORTANCE = {i.value for i in HypothesisImportance}


# ---------------------------------------------------------------- hypothesis
def create_hypothesis(
    db: Session, user_id: UUID, decision_id: UUID, data: HypothesisCreate
) -> DecisionHypothesis:
    decision = get_decision(db, user_id, decision_id)
    hypothesis = DecisionHypothesis(user_id=user_id, decision_id=decision.id, **data.model_dump())
    db.add(hypothesis)
    db.commit()
    db.refresh(hypothesis)
    return hypothesis


def get_hypothesis(db: Session, user_id: UUID, hypothesis_id: UUID) -> DecisionHypothesis:
    hypothesis = (
        db.query(DecisionHypothesis)
        .filter(DecisionHypothesis.id == hypothesis_id, DecisionHypothesis.user_id == user_id)
        .first()
    )
    if not hypothesis:
        raise NotFoundError("假设不存在")
    return hypothesis


def update_hypothesis(
    db: Session, user_id: UUID, hypothesis_id: UUID, data: HypothesisUpdate
) -> DecisionHypothesis:
    hypothesis = get_hypothesis(db, user_id, hypothesis_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(hypothesis, key, value)
    db.commit()
    db.refresh(hypothesis)
    return hypothesis


def delete_hypothesis(db: Session, user_id: UUID, hypothesis_id: UUID) -> None:
    hypothesis = get_hypothesis(db, user_id, hypothesis_id)
    db.delete(hypothesis)
    db.commit()


# ---------------------------------------------------------------- evidence
def get_evidence(db: Session, user_id: UUID, evidence_id: UUID) -> DecisionEvidence:
    evidence = (
        db.query(DecisionEvidence)
        .filter(DecisionEvidence.id == evidence_id, DecisionEvidence.user_id == user_id)
        .first()
    )
    if not evidence:
        raise NotFoundError("证据不存在")
    return evidence


def create_evidence(
    db: Session,
    user_id: UUID,
    data: EvidenceCreate,
    *,
    decision_id: UUID | None = None,
    hypothesis_id: UUID | None = None,
) -> DecisionEvidence:
    """创建证据。路径参数优先于 body 中的归属字段。

    证据闸：无论 provider 是内部库还是外部源，创建一律 internal_unverified；
    verification_status / verification_source / verified_on 只能由 verify_evidence 推进。
    """
    effective_decision = decision_id or data.decision_id
    effective_hypothesis = hypothesis_id or data.hypothesis_id
    if not effective_decision and not effective_hypothesis:
        raise ValidationFailedError("证据必须挂在 decision 或 hypothesis 之一")

    if effective_hypothesis:
        hypothesis = get_hypothesis(db, user_id, effective_hypothesis)
        if effective_decision and effective_decision != hypothesis.decision_id:
            raise ValidationFailedError("该假设不属于指定的决策")
        effective_decision = hypothesis.decision_id
    else:
        get_decision(db, user_id, effective_decision)  # 所有权检查

    evidence = DecisionEvidence(
        user_id=user_id,
        decision_id=effective_decision,
        hypothesis_id=effective_hypothesis,
        claim=data.claim,
        source=data.source,
        source_url=data.source_url,
        source_type=data.source_type,
        reliability=data.reliability,
        stance=data.stance,
        observed_on=data.observed_on,
        provider=data.provider,
        notes=data.notes,
        verification_status=EvidenceVerificationStatus.internal_unverified,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def update_evidence(
    db: Session, user_id: UUID, evidence_id: UUID, data: EvidenceUpdate
) -> DecisionEvidence:
    evidence = get_evidence(db, user_id, evidence_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(evidence, key, value)
    db.commit()
    db.refresh(evidence)
    return evidence


def verify_evidence(
    db: Session, user_id: UUID, evidence_id: UUID, data: EvidenceVerifyRequest
) -> DecisionEvidence:
    """显式验证：唯一的 verification_status 推进入口。

    证据闸硬规则：externally_verified 必须提供 verification_source，
    否则就是"没有真实来源却标记 VERIFIED"（禁令 §十三.13）。
    """
    evidence = get_evidence(db, user_id, evidence_id)
    if (
        data.verification_status == EvidenceVerificationStatus.externally_verified
        and not data.verification_source.strip()
    ):
        raise ValidationFailedError("externally_verified 必须提供 verification_source")
    evidence.verification_status = data.verification_status
    evidence.verification_source = data.verification_source.strip() or None
    if data.verification_status in (
        EvidenceVerificationStatus.externally_verified,
        EvidenceVerificationStatus.contradicted,
    ):
        evidence.verified_on = data.verified_on or date.today()
    else:
        evidence.verified_on = None
    db.commit()
    db.refresh(evidence)
    return evidence


def delete_evidence(db: Session, user_id: UUID, evidence_id: UUID) -> None:
    evidence = get_evidence(db, user_id, evidence_id)
    db.delete(evidence)
    db.commit()


# ---------------------------------------------------------------- actions
def create_action(
    db: Session, user_id: UUID, decision_id: UUID, data: ValidationActionCreate
) -> DecisionValidationAction:
    get_decision(db, user_id, decision_id)
    if data.hypothesis_id:
        hypothesis = get_hypothesis(db, user_id, data.hypothesis_id)
        if hypothesis.decision_id != decision_id:
            raise ValidationFailedError("该假设不属于此决策，行动不能跨决策挂接")
    action = DecisionValidationAction(user_id=user_id, decision_id=decision_id, **data.model_dump())
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def get_action(db: Session, user_id: UUID, action_id: UUID) -> DecisionValidationAction:
    action = (
        db.query(DecisionValidationAction)
        .filter(
            DecisionValidationAction.id == action_id,
            DecisionValidationAction.user_id == user_id,
        )
        .first()
    )
    if not action:
        raise NotFoundError("验证行动不存在")
    return action


def update_action(
    db: Session, user_id: UUID, action_id: UUID, data: ValidationActionUpdate
) -> DecisionValidationAction:
    action = get_action(db, user_id, action_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(action, key, value)
    db.commit()
    db.refresh(action)
    return action


def complete_action(
    db: Session, user_id: UUID, action_id: UUID, data: ActionCompleteRequest
) -> DecisionValidationAction:
    action = get_action(db, user_id, action_id)
    action.status = ValidationActionStatus.done
    action.completed_at = datetime.now(timezone.utc)
    action.result = data.result
    action.result_stance = data.result_stance
    if data.hypothesis_status_update:
        if not action.hypothesis_id:
            raise ValidationFailedError("该行动未挂接假设，无法更新假设状态")
        hypothesis = get_hypothesis(db, user_id, action.hypothesis_id)
        hypothesis.status = data.hypothesis_status_update
    db.commit()
    db.refresh(action)
    return action


def delete_action(db: Session, user_id: UUID, action_id: UUID) -> None:
    action = get_action(db, user_id, action_id)
    db.delete(action)
    db.commit()


# ---------------------------------------------------------------- outcome / reflection
def create_outcome(
    db: Session, user_id: UUID, decision_id: UUID, data: OutcomeCreate
) -> DecisionOutcome:
    get_decision(db, user_id, decision_id)
    outcome = DecisionOutcome(user_id=user_id, decision_id=decision_id, **data.model_dump())
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


def create_reflection(
    db: Session, user_id: UUID, decision_id: UUID, data: ReflectionCreate
) -> DecisionReflection:
    get_decision(db, user_id, decision_id)
    reflection = DecisionReflection(user_id=user_id, decision_id=decision_id, **data.model_dump())
    db.add(reflection)
    db.commit()
    db.refresh(reflection)
    return reflection


# ---------------------------------------------------------------- AI structuring
def _normalize_draft_data(data: dict, raw_text: str) -> StructuredDraft:
    """把 LLM 返回的 dict 规范化为草稿；脏字段按保守值处理，不抛异常。"""
    hypotheses: list[dict] = []
    for item in (data.get("hypotheses") or [])[:6]:
        if not isinstance(item, dict):
            continue
        statement = str(item.get("statement") or "").strip()
        if not statement:
            continue
        importance = item.get("importance")
        if importance not in _VALID_IMPORTANCE:
            importance = HypothesisImportance.high.value
        hypotheses.append(
            {
                "statement": statement[:2000],
                "importance": importance,
                "impact": (str(item.get("impact")).strip() or None) if item.get("impact") else None,
            }
        )

    def _str_list(value: object, cap: int = 8) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(v).strip()[:500] for v in value if str(v).strip()][:cap]

    question = str(data.get("question") or "").strip() or raw_text.strip()
    return StructuredDraft(
        question=question[:500],
        context=(str(data.get("context")).strip() or None) if data.get("context") else None,
        options=_str_list(data.get("options"), cap=4),
        constraints=_str_list(data.get("constraints")),
        desired_outcome=(
            (str(data.get("desired_outcome")).strip() or None)
            if data.get("desired_outcome")
            else None
        ),
        hypotheses=hypotheses,
        evidence_needs=_str_list(data.get("evidence_needs")),
        ai_used=True,
    )


async def structure_draft(raw_text: str) -> StructuredDraft:
    """AI 结构化草稿。LLM 不可用/解析失败时诚实降级：question=原文、hypotheses 空、
    ai_used=False，由用户手工补齐——绝不编造假设凑数。"""
    try:
        orchestrator = AIOrchestrator()
        raw = await orchestrator.chat(
            system_prompt=_DRAFT_SYSTEM_PROMPT, user_prompt=f"用户的话：{raw_text}", timeout=30
        )
    except Exception as exc:
        logger.warning("AI 结构化降级（ai_used=False）: %s", exc)
        return StructuredDraft(question=raw_text.strip()[:500], ai_used=False)

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"\{.*\}", raw or "", re.DOTALL)
        if not match:
            logger.warning("AI 结构化返回不可解析，降级（ai_used=False）")
            return StructuredDraft(question=raw_text.strip()[:500], ai_used=False)
        try:
            data = json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            return StructuredDraft(question=raw_text.strip()[:500], ai_used=False)

    if not isinstance(data, dict):
        return StructuredDraft(question=raw_text.strip()[:500], ai_used=False)
    return _normalize_draft_data(data, raw_text)


# ---------------------------------------------------------------- confirm + card
def confirm_draft(db: Session, user_id: UUID, data: ConfirmDraftRequest) -> DestinationDecision:
    """用户确认草稿 → 落库决策 + 假设。最终决策权在用户：类型/日期/置信度都由确认方提供。"""
    draft = data.draft
    decision = DestinationDecision(
        user_id=user_id,
        decision_date=data.decision_date or date.today(),
        destination_type=data.destination_type,
        status=DecisionStatus.planned,
        details={},
        reasoning=None,
        confidence=data.confidence,
        question=draft.question[:500],
        context=draft.context,
        constraints=draft.constraints,
        options=draft.options,
        desired_outcome=draft.desired_outcome,
        # legacy 镜像：assumptions 存假设 statement，保旧视图可读；新逻辑读 decision_hypotheses
        assumptions=[h.statement for h in draft.hypotheses],
    )
    db.add(decision)
    db.flush()
    for h in draft.hypotheses:
        db.add(
            DecisionHypothesis(
                user_id=user_id,
                decision_id=decision.id,
                statement=h.statement,
                importance=h.importance,
                impact=h.impact,
            )
        )
    db.commit()
    db.refresh(decision)
    invalidate_user_context(user_id)
    return decision


def get_card(db: Session, user_id: UUID, decision_id: UUID) -> dict:
    """决策卡聚合：决策 + 假设（带证据立场计数）+ 行动 + 结果 + 复盘。"""
    decision = get_decision(db, user_id, decision_id)
    hypotheses = (
        db.query(DecisionHypothesis)
        .filter(
            DecisionHypothesis.user_id == user_id,
            DecisionHypothesis.decision_id == decision_id,
        )
        .order_by(DecisionHypothesis.created_at.asc())
        .all()
    )
    evidence = (
        db.query(DecisionEvidence)
        .filter(DecisionEvidence.user_id == user_id, DecisionEvidence.decision_id == decision_id)
        .order_by(DecisionEvidence.created_at.asc())
        .all()
    )
    actions = (
        db.query(DecisionValidationAction)
        .filter(
            DecisionValidationAction.user_id == user_id,
            DecisionValidationAction.decision_id == decision_id,
        )
        .order_by(DecisionValidationAction.created_at.asc())
        .all()
    )
    outcomes = (
        db.query(DecisionOutcome)
        .filter(DecisionOutcome.user_id == user_id, DecisionOutcome.decision_id == decision_id)
        .order_by(DecisionOutcome.created_at.asc())
        .all()
    )
    reflections = (
        db.query(DecisionReflection)
        .filter(
            DecisionReflection.user_id == user_id,
            DecisionReflection.decision_id == decision_id,
        )
        .order_by(DecisionReflection.created_at.asc())
        .all()
    )

    evidence_by_hypothesis: dict[UUID, list[DecisionEvidence]] = {}
    for ev in evidence:
        if ev.hypothesis_id:
            evidence_by_hypothesis.setdefault(ev.hypothesis_id, []).append(ev)

    hypothesis_cards: list[dict] = []
    for hyp in hypotheses:
        rows = evidence_by_hypothesis.get(hyp.id, [])
        stance_counts = {
            EvidenceStance.supporting: 0,
            EvidenceStance.contradicting: 0,
            EvidenceStance.neutral: 0,
        }
        for ev in rows:
            stance_counts[ev.stance] = stance_counts.get(ev.stance, 0) + 1
        hypothesis_cards.append(
            {
                "id": hyp.id,
                "decision_id": hyp.decision_id,
                "statement": hyp.statement,
                "importance": hyp.importance,
                "confidence": hyp.confidence,
                "status": hyp.status,
                "impact": hyp.impact,
                "result": hyp.result,
                "created_at": hyp.created_at,
                "evidence_count": len(rows),
                "supporting": stance_counts[EvidenceStance.supporting],
                "contradicting": stance_counts[EvidenceStance.contradicting],
                "neutral": stance_counts[EvidenceStance.neutral],
            }
        )

    return {
        "decision": decision,
        "hypotheses": hypothesis_cards,
        "evidence": evidence,
        "actions": actions,
        "outcomes": outcomes,
        "reflections": reflections,
    }
