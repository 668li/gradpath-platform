"""同路人洞察服务 — 创意功能引擎。

从第一性原理出发，把平台的「真实数据护城河」转化为改变用户信念的洞察：
1. 同路人镜像：和你相似的人怎么选、结果如何（社会证明，对抗盲目焦虑）
2. 决策拖延成本：量化"还在犹豫"的真实代价（对抗拖延）
3. 暗知识缺口雷达：你还不知道但同路人都知道的关键信息（对抗信息差）

每个功能都带 60s 缓存，避免高频聚合查询拖垮数据库。
"""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.models.dark_knowledge_push import DarkKnowledgePushLog
from app.models.destination_decision import DecisionStatus, DestinationDecision
from app.models.grad_intel import DarkKnowledge
from app.models.outcome_report import OutcomeReport
from app.models.user import User

logger = logging.getLogger(__name__)

# 去向中文标签
_DEST_LABELS = {
    "employment": "就业",
    "postgrad": "考研",
    "civil_service": "考公",
    "abroad": "出国",
    "phd": "读博",
    "startup": "创业",
    "gap_year": "间隔年",
}

_STAGE_LABELS = {
    "student": "在读",
    "graduating": "应届毕业",
    "early_career": "职场新人",
    "experienced": "资深从业者",
}


def get_peer_mirror(db: Session, user_id: UUID) -> dict:
    """同路人镜像：聚合与当前用户相似群体的去向分布与结果。

    相似定义：同 current_stage（阶段）的用户群体。
    返回去向分布、上岸率、以及一条真实的过来人建议。
    """
    cache_key = f"peer_mirror:{user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    user = db.get(User, user_id)
    my_stage = user.current_stage.value if user and user.current_stage else None

    # 找到同阶段的同路人（排除自己）
    peer_query = db.query(User.id).filter(User.id != user_id)
    if my_stage:
        peer_query = peer_query.filter(User.current_stage == my_stage)
    peer_ids = [r[0] for r in peer_query.limit(500).all()]

    result: dict = {
        "has_data": False,
        "peer_count": 0,
        "stage_label": _STAGE_LABELS.get(my_stage, "同阶段"),
        "distribution": [],
        "success_rate": None,
        "peer_advice": None,
    }

    if not peer_ids:
        cache.set(cache_key, result, ttl=60)
        return result

    # 同路人的去向分布
    rows = (
        db.query(DestinationDecision.destination_type, func.count(DestinationDecision.id))
        .filter(DestinationDecision.user_id.in_(peer_ids))
        .group_by(DestinationDecision.destination_type)
        .order_by(func.count(DestinationDecision.id).desc())
        .all()
    )
    total_decisions = sum(c for _, c in rows)
    if total_decisions == 0:
        cache.set(cache_key, result, ttl=60)
        return result

    distribution = [
        {
            "destination_type": dt.value if hasattr(dt, "value") else str(dt),
            "label": _DEST_LABELS.get(dt.value if hasattr(dt, "value") else str(dt), str(dt)),
            "count": int(c),
            "percent": round(c / total_decisions * 100),
        }
        for dt, c in rows
    ]

    # 同路人的上岸率（来自公开的 outcome_report）
    outcome_rows = (
        db.query(OutcomeReport.outcome_type, func.count(OutcomeReport.id))
        .filter(
            OutcomeReport.user_id.in_(peer_ids),
            OutcomeReport.is_public != "private",
        )
        .group_by(OutcomeReport.outcome_type)
        .all()
    )
    total_outcomes = sum(c for _, c in outcome_rows)
    success_count = sum(
        c
        for ot, c in outcome_rows
        if (ot.value if hasattr(ot, "value") else str(ot)) in ("grad_civil_career", "adjustment")
    )
    success_rate = round(success_count / total_outcomes * 100) if total_outcomes > 0 else None

    # 一条真实的过来人建议（优先取满意度高且有建议的）
    advice_row = (
        db.query(OutcomeReport)
        .filter(
            OutcomeReport.user_id.in_(peer_ids),
            OutcomeReport.is_public != "private",
            OutcomeReport.advice_for_others.isnot(None),
        )
        .order_by(OutcomeReport.satisfaction_after.desc().nullslast(), OutcomeReport.year.desc())
        .first()
    )
    peer_advice = None
    if advice_row and advice_row.advice_for_others:
        peer_advice = {
            "advice": advice_row.advice_for_others[:200],
            "target_school": advice_row.target_school,
            "year": advice_row.year,
            "satisfaction": advice_row.satisfaction_after,
        }

    result = {
        "has_data": True,
        "peer_count": len(peer_ids),
        "stage_label": _STAGE_LABELS.get(my_stage, "同阶段"),
        "distribution": distribution,
        "success_rate": success_rate,
        "peer_advice": peer_advice,
    }
    cache.set(cache_key, result, ttl=60)
    return result


def get_procrastination_cost(db: Session, user_id: UUID) -> dict:
    """决策拖延成本：量化用户停留在 'planned' 状态决策的真实代价。

    从第一性原理：拖延的本质是"用未来的准备时间换取当下的舒适"。
    每多犹豫一天，可用于执行的准备时间就少一天，成功率随之下降。
    """
    cache_key = f"procrastination_cost:{user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    today = date.today()
    pending = (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.user_id == user_id,
            DestinationDecision.status == DecisionStatus.planned,
        )
        .all()
    )

    items = []
    total_stale_days = 0
    for d in pending:
        created = d.created_at.date() if d.created_at else d.decision_date
        days_pending = (today - created).days if created else 0
        days_pending = max(0, days_pending)
        total_stale_days += days_pending

        # 估算机会成本：按每天 3 小时有效准备时间折算
        lost_prep_hours = days_pending * 3
        # 紧迫度分级
        if days_pending >= 30:
            urgency = "critical"
            message = f"已犹豫 {days_pending} 天，相当于损失约 {lost_prep_hours} 小时准备时间"
        elif days_pending >= 14:
            urgency = "high"
            message = f"已犹豫 {days_pending} 天，建议本周内做出决定"
        elif days_pending >= 7:
            urgency = "medium"
            message = f"已犹豫 {days_pending} 天，还在可接受范围，但别再拖了"
        else:
            urgency = "low"
            message = f"刚创建 {days_pending} 天，趁热打铁推进分析"

        items.append(
            {
                "decision_id": str(d.id),
                "destination_type": d.destination_type.value,
                "destination_label": _DEST_LABELS.get(
                    d.destination_type.value, str(d.destination_type)
                ),
                "days_pending": days_pending,
                "lost_prep_hours": lost_prep_hours,
                "urgency": urgency,
                "message": message,
                "confidence": d.confidence,
            }
        )

    # 按紧迫度排序
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda x: urgency_order.get(x["urgency"], 9))

    result = {
        "has_pending": len(items) > 0,
        "pending_count": len(items),
        "total_stale_days": total_stale_days,
        "total_lost_hours": total_stale_days * 3,
        "items": items[:5],
    }
    cache.set(cache_key, result, ttl=60)
    return result


def get_dark_knowledge_gap(db: Session, user_id: UUID, limit: int = 5) -> dict:
    """暗知识缺口雷达：找出用户尚未看到的高重要性暗知识。

    从第一性原理：信息差的杀伤力在于"你不知道你不知道"。
    把同路人都在看、但你还没看到的关键暗知识主动浮出水面。
    """
    cache_key = f"dk_gap:{user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 用户已经看过的暗知识 ID
    seen_ids_subq = db.query(DarkKnowledgePushLog.dark_knowledge_id).filter(
        DarkKnowledgePushLog.user_id == user_id
    )

    # 高重要性且未看过的暗知识
    unseen = (
        db.query(DarkKnowledge)
        .filter(
            DarkKnowledge.importance == "high",
            ~DarkKnowledge.id.in_(seen_ids_subq),
        )
        .order_by(DarkKnowledge.sort_order.asc())
        .limit(limit)
        .all()
    )

    # 统计同路人（全体用户）已读这些暗知识的人数，制造"别人都看了"的社会证明
    gap_items = []
    for dk in unseen:
        read_count = (
            db.query(func.count(DarkKnowledgePushLog.id))
            .filter(
                DarkKnowledgePushLog.dark_knowledge_id == dk.id,
                DarkKnowledgePushLog.read_at.isnot(None),
            )
            .scalar()
        ) or 0
        gap_items.append(
            {
                "id": str(dk.id),
                "title": dk.title,
                "content_preview": (dk.content or "")[:120],
                "stage": dk.stage,
                "category": dk.category,
                "read_by_peers": int(read_count),
                "common_misconception": (
                    dk.common_misconception[:100] if dk.common_misconception else None
                ),
            }
        )

    result = {
        "has_gap": len(gap_items) > 0,
        "gap_count": len(gap_items),
        "items": gap_items,
    }
    cache.set(cache_key, result, ttl=60)
    return result


def get_regret_lessons(db: Session, limit_per_type: int = 2) -> dict:
    """前车之鉴：从公开的上岸报告中提取真实的后悔与教训。

    从第一性原理：决策质量的最好老师，是"已经走过这条路的人的回望"。
    按 outcome_type 分组（上岸/调剂/未上岸），呈现三种视角的教训，
    让正在犹豫的人提前看到每条路的真实代价与收获。
    """
    cache_key = f"regret_lessons:{limit_per_type}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    _OUTCOME_LABELS = {
        "grad_civil_career": "成功上岸",
        "adjustment": "调剂上岸",
        "failed": "未上岸",
    }
    _OUTCOME_TONES = {
        "grad_civil_career": "success",
        "adjustment": "mixed",
        "failed": "caution",
    }

    groups = []
    for outcome_type in ["grad_civil_career", "adjustment", "failed"]:
        reports = (
            db.query(OutcomeReport)
            .filter(
                OutcomeReport.outcome_type == outcome_type,
                OutcomeReport.is_public != "private",
            )
            .order_by(OutcomeReport.year.desc(), OutcomeReport.created_at.desc())
            .limit(limit_per_type * 3)
            .all()
        )
        lessons = []
        for r in reports:
            # 优先取"如果重来"，其次取"给后来人的建议"
            text = r.what_i_would_do_differently or r.advice_for_others
            if not text or not text.strip():
                continue
            lessons.append(
                {
                    "text": text.strip()[:300],
                    "target_school": r.target_school,
                    "target_major": r.target_major,
                    "year": r.year,
                    "score_total": r.score_total,
                    "satisfaction_after": r.satisfaction_after,
                    "confidence_before": r.confidence_before,
                }
            )
            if len(lessons) >= limit_per_type:
                break
        if lessons:
            groups.append(
                {
                    "outcome_type": outcome_type,
                    "label": _OUTCOME_LABELS.get(outcome_type, outcome_type),
                    "tone": _OUTCOME_TONES.get(outcome_type, "neutral"),
                    "lessons": lessons,
                }
            )

    result = {
        "has_lessons": len(groups) > 0,
        "group_count": len(groups),
        "groups": groups,
    }
    cache.set(cache_key, result, ttl=120)
    return result
