"""Decision -> Hypothesis -> Evidence 数据服务。

这里刻意不做“AI 判定谁对谁错”。服务层只负责保证：
1. 数据属于当前用户；
2. hypothesis 必须属于同一个 decision；
3. evidence 可以明确支持/反驳/中立；
4. readiness 只描述证据覆盖度，不伪造“决策正确率”。
"""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.decision_evidence import DecisionEvidence
from app.models.decision_hypothesis import DecisionHypothesis
from app.models.destination_decision import DestinationDecision
from app.schemas.decision_evidence import EvidenceCreate, EvidenceUpdate, HypothesisCreate, HypothesisUpdate


VALID_HYPOTHESIS_STATUSES = {"open", "validated", "invalidated", "superseded"}



def sync_assumptions_to_hypotheses(
    db: Session, user_id: UUID, decision: DestinationDecision
) -> int:
    """把旧的 assumptions 字符串增量转换成结构化 Hypothesis。

    兼容已有 Decision 数据，不删除/覆盖旧 assumptions。重复执行是幂等的。
    """
    assumptions = [
        item.strip()
        for item in (decision.assumptions or [])
        if isinstance(item, str) and item.strip()
    ]
    if not assumptions:
        return 0

    existing_statements = {
        row[0]
        for row in db.query(DecisionHypothesis.statement)
        .filter(
            DecisionHypothesis.user_id == user_id,
            DecisionHypothesis.decision_id == decision.id,
        )
        .all()
    }
    confidence = round(max(0.0, min(1.0, (decision.confidence - 1) / 4)), 4)
    created = 0
    for statement in assumptions:
        if statement in existing_statements:
            continue
        db.add(
            DecisionHypothesis(
                user_id=user_id,
                decision_id=decision.id,
                statement=statement,
                importance=3,
                confidence=confidence,
                status="open",
                metadata_json={"source": "decision.assumptions"},
            )
        )
        existing_statements.add(statement)
        created += 1

    if created:
        db.commit()
    return created


def _get_decision(db: Session, user_id: UUID, decision_id: UUID) -> DestinationDecision:
    obj = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.id == decision_id, DestinationDecision.user_id == user_id)
        .first()
    )
    if not obj:
        raise NotFoundError("决策不存在或无权访问")
    return obj


def _get_hypothesis(
    db: Session, user_id: UUID, decision_id: UUID, hypothesis_id: UUID
) -> DecisionHypothesis:
    obj = (
        db.query(DecisionHypothesis)
        .filter(
            DecisionHypothesis.id == hypothesis_id,
            DecisionHypothesis.user_id == user_id,
            DecisionHypothesis.decision_id == decision_id,
        )
        .first()
    )
    if not obj:
        raise NotFoundError("决策假设不存在或无权访问")
    return obj


def _get_evidence(
    db: Session, user_id: UUID, decision_id: UUID, evidence_id: UUID
) -> DecisionEvidence:
    obj = (
        db.query(DecisionEvidence)
        .filter(
            DecisionEvidence.id == evidence_id,
            DecisionEvidence.user_id == user_id,
            DecisionEvidence.decision_id == decision_id,
        )
        .first()
    )
    if not obj:
        raise NotFoundError("决策证据不存在或无权访问")
    return obj


def create_hypothesis(
    db: Session, user_id: UUID, decision_id: UUID, data: HypothesisCreate
) -> DecisionHypothesis:
    _get_decision(db, user_id, decision_id)
    obj = DecisionHypothesis(
        user_id=user_id,
        decision_id=decision_id,
        statement=data.statement.strip(),
        importance=data.importance,
        confidence=data.confidence,
        status=data.status,
        verification_question=data.verification_question.strip() if data.verification_question else None,
        validation_action=data.validation_action.strip() if data.validation_action else None,
        metadata_json=data.metadata,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_hypotheses(
    db: Session, user_id: UUID, decision_id: UUID
) -> list[DecisionHypothesis]:
    _get_decision(db, user_id, decision_id)
    return (
        db.query(DecisionHypothesis)
        .filter(
            DecisionHypothesis.user_id == user_id,
            DecisionHypothesis.decision_id == decision_id,
        )
        .order_by(
            DecisionHypothesis.status.asc(),
            DecisionHypothesis.importance.desc(),
            DecisionHypothesis.created_at.asc(),
        )
        .all()
    )


def update_hypothesis(
    db: Session, user_id: UUID, decision_id: UUID, hypothesis_id: UUID, data: HypothesisUpdate
) -> DecisionHypothesis:
    obj = _get_hypothesis(db, user_id, decision_id, hypothesis_id)
    values = data.model_dump(exclude_unset=True)
    if "metadata" in values:
        values["metadata_json"] = values.pop("metadata")
    if "statement" in values and values["statement"] is not None:
        values["statement"] = values["statement"].strip()
    if "verification_question" in values and values["verification_question"] is not None:
        values["verification_question"] = values["verification_question"].strip() or None
    if "validation_action" in values and values["validation_action"] is not None:
        values["validation_action"] = values["validation_action"].strip() or None
    for key, value in values.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_hypothesis(
    db: Session, user_id: UUID, decision_id: UUID, hypothesis_id: UUID
) -> None:
    obj = _get_hypothesis(db, user_id, decision_id, hypothesis_id)
    db.delete(obj)
    db.commit()


def _validate_hypothesis_link(
    db: Session, user_id: UUID, decision_id: UUID, hypothesis_id: UUID | None
) -> None:
    if hypothesis_id is not None:
        _get_hypothesis(db, user_id, decision_id, hypothesis_id)


def create_evidence(
    db: Session, user_id: UUID, decision_id: UUID, data: EvidenceCreate
) -> DecisionEvidence:
    _get_decision(db, user_id, decision_id)
    _validate_hypothesis_link(db, user_id, decision_id, data.hypothesis_id)
    obj = DecisionEvidence(
        user_id=user_id,
        decision_id=decision_id,
        hypothesis_id=data.hypothesis_id,
        title=data.title.strip(),
        claim=data.claim.strip(),
        source_url=data.source_url.strip() if data.source_url else None,
        source_type=data.source_type,
        reliability=data.reliability,
        stance=data.stance,
        observed_on=data.observed_on,
        excerpt=data.excerpt.strip() if data.excerpt else None,
        metadata_json=data.metadata,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_evidence(
    db: Session, user_id: UUID, decision_id: UUID, hypothesis_id: UUID | None = None
) -> list[DecisionEvidence]:
    _get_decision(db, user_id, decision_id)
    query = db.query(DecisionEvidence).filter(
        DecisionEvidence.user_id == user_id,
        DecisionEvidence.decision_id == decision_id,
    )
    if hypothesis_id is not None:
        _validate_hypothesis_link(db, user_id, decision_id, hypothesis_id)
        query = query.filter(DecisionEvidence.hypothesis_id == hypothesis_id)
    return query.order_by(DecisionEvidence.created_at.desc()).all()


def update_evidence(
    db: Session, user_id: UUID, decision_id: UUID, evidence_id: UUID, data: EvidenceUpdate
) -> DecisionEvidence:
    obj = _get_evidence(db, user_id, decision_id, evidence_id)
    values = data.model_dump(exclude_unset=True)
    if "metadata" in values:
        values["metadata_json"] = values.pop("metadata")
    if "hypothesis_id" in values:
        _validate_hypothesis_link(db, user_id, decision_id, values["hypothesis_id"])
    for field in ("title", "claim", "source_url", "excerpt"):
        if field in values and values[field] is not None:
            values[field] = values[field].strip() or None
    for key, value in values.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete_evidence(
    db: Session, user_id: UUID, decision_id: UUID, evidence_id: UUID
) -> None:
    obj = _get_evidence(db, user_id, decision_id, evidence_id)
    db.delete(obj)
    db.commit()


def get_evidence_readiness(
    db: Session, user_id: UUID, decision_id: UUID
) -> dict:
    _get_decision(db, user_id, decision_id)
    hypothesis_ids = [
        row[0]
        for row in db.query(DecisionHypothesis.id)
        .filter(
            DecisionHypothesis.user_id == user_id,
            DecisionHypothesis.decision_id == decision_id,
        )
        .all()
    ]
    evidence_rows = (
        db.query(
            DecisionEvidence.hypothesis_id,
            DecisionEvidence.stance,
        )
        .filter(
            DecisionEvidence.user_id == user_id,
            DecisionEvidence.decision_id == decision_id,
        )
        .all()
    )

    covered = {hid for hid, _ in evidence_rows if hid is not None}
    total = len(hypothesis_ids)

    supporting = sum(stance == "supports" for _, stance in evidence_rows)
    refuting = sum(stance == "refutes" for _, stance in evidence_rows)
    neutral = sum(stance == "neutral" for _, stance in evidence_rows)

    return {
        "decision_id": decision_id,
        "hypotheses_total": total,
        "hypotheses_with_evidence": len(covered),
        "hypotheses_unverified": max(total - len(covered), 0),
        "evidence_total": len(evidence_rows),
        "evidence_supporting": supporting,
        "evidence_refuting": refuting,
        "evidence_neutral": neutral,
        "coverage": round((len(covered) / total), 4) if total else 0.0,
    }



def import_path_engine_evidence(
    db: Session,
    user_id: UUID,
    decision_id: UUID,
    major: str,
    region: str | None,
    school_tier: str | None,
    graduation_year: int | None,
    fresh_status: str | None,
    party_status: str | None,
    education: str | None,
    has_grassroots: bool | None,
    gender: str | None,
    estimated_score: int | None,
    kaoyan_estimated_score: int | None,
    hypothesis_id: UUID | None = None,
) -> dict:
    """把现有三路真实数据引擎的证据逐条导入 DecisionEvidence。

    这是 Evidence Provider 的第一条适配器：复用现有 path_decision_engine，
    不新增爬虫，不重复计算数据库指标。
    """
    _get_decision(db, user_id, decision_id)
    if hypothesis_id is not None:
        _get_hypothesis(db, user_id, decision_id, hypothesis_id)

    from app.services import path_decision_engine

    result = path_decision_engine.generate_decision(
        db=db,
        major=major,
        region=region,
        school_tier=school_tier,
        graduation_year=graduation_year,
        fresh_status=fresh_status,
        party_status=party_status,
        education=education,
        has_grassroots=has_grassroots,
        gender=gender,
        estimated_score=estimated_score,
        kaoyan_estimated_score=kaoyan_estimated_score,
    )

    imported = 0
    skipped = 0
    notes: list[str] = []

    existing = {
        (row.title, row.claim)
        for row in db.query(DecisionEvidence)
        .filter(
            DecisionEvidence.user_id == user_id,
            DecisionEvidence.decision_id == decision_id,
        )
        .all()
    }

    for metric in result.get("metrics", []):
        for evidence in metric.get("evidence", []) or []:
            title = str(evidence.get("label") or "").strip()
            claim = str(evidence.get("value") or "").strip()
            if not title or not claim:
                continue
            key = (title, claim)
            if key in existing:
                skipped += 1
                continue

            source_url = evidence.get("source_url") or None
            note = evidence.get("note") or None
            db.add(
                DecisionEvidence(
                    user_id=user_id,
                    decision_id=decision_id,
                    hypothesis_id=hypothesis_id,
                    title=title,
                    claim=claim,
                    source_url=source_url,
                    source_type="dataset",
                    reliability=5 if source_url else 3,
                    stance="neutral",
                    observed_on=None,
                    excerpt=note,
                    metadata_json={
                        "provider": "path_decision_engine",
                        "path_type": metric.get("path_type"),
                        "target_role": metric.get("target_role"),
                    },
                )
            )
            existing.add(key)
            imported += 1

    if not imported:
        notes.append("当前条件下没有新的可导入证据；这不代表数据库没有数据。")

    db.commit()
    return {
        "decision_id": decision_id,
        "imported": imported,
        "skipped_duplicates": skipped,
        "provider": "path_decision_engine",
        "notes": notes,
    }
