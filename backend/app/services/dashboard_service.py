from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.destination_decision import DestinationDecision
from app.models.retrospective import Retrospective
from app.models.skill_node import SkillNode


def get_overview(db: Session, user_id: UUID) -> dict:
    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .all()
    )
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.event_date.desc())
        .all()
    )
    skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
    retros = (
        db.query(Retrospective)
        .filter(Retrospective.user_id == user_id)
        .order_by(Retrospective.period_end.desc())
        .all()
    )

    skill_categories: dict[str, int] = {}
    for s in skills:
        skill_categories[s.category] = skill_categories.get(s.category, 0) + 1

    latest_decision = None
    if decisions:
        d = decisions[0]
        latest_decision = {
            "id": str(d.id),
            "destination_type": d.destination_type.value,
            "status": d.status.value,
            "decision_date": d.decision_date.isoformat(),
        }

    recent_events = [
        {
            "id": str(e.id),
            "title": e.title,
            "event_type": e.event_type.value,
            "event_date": e.event_date.isoformat(),
        }
        for e in events[:5]
    ]

    latest_retro = None
    if retros:
        r = retros[0]
        latest_retro = {
            "id": str(r.id),
            "title": r.title,
            "period_end": r.period_end.isoformat(),
        }

    # 合并 timeline
    timeline = []
    for d in decisions:
        detail = d.details or {}
        timeline.append({
            "id": str(d.id),
            "date": d.decision_date.isoformat(),
            "type": "decision",
            "title": f"去向决策: {d.destination_type.value}",
            "subtitle": detail.get("company") or detail.get("target_school") or "",
        })
    for e in events:
        timeline.append({
            "id": str(e.id),
            "date": e.event_date.isoformat(),
            "type": "event",
            "title": e.title,
            "subtitle": e.event_type.value,
        })
    timeline.sort(key=lambda x: x["date"], reverse=True)

    return {
        "decisions_count": len(decisions),
        "events_count": len(events),
        "skills_count": len(skills),
        "retrospectives_count": len(retros),
        "latest_decision": latest_decision,
        "recent_events": recent_events,
        "skill_categories": skill_categories,
        "latest_retrospective": latest_retro,
        "timeline": timeline,
    }
