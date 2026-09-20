"""一次性把现有 DestinationDecision.assumptions 回填为 DecisionHypothesis。

用法：
    python -m scripts.backfill_decision_hypotheses
"""

from app.database import SessionLocal
from app.models.destination_decision import DestinationDecision
from app.services.decision_evidence_service import sync_assumptions_to_hypotheses


def main() -> None:
    db = SessionLocal()
    try:
        decisions = db.query(DestinationDecision).all()
        created = 0
        for decision in decisions:
            before = (
                db.query(DestinationDecision.id)
                .filter(DestinationDecision.id == decision.id)
                .count()
            )
            created += sync_assumptions_to_hypotheses(db, decision.user_id, decision)
            print(f"decision={decision.id} assumptions={len(decision.assumptions or [])} processed={before > 0}")
        print(f"backfill complete: decisions={len(decisions)} hypotheses_created={created}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
