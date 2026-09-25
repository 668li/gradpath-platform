"""复盘深化核心服务 — 事实回放 / 原则库 / Try 行动卡。

设计依据（2026-09-25 深度调研 + 对抗审查裁决）：
- replay 四源聚合纯 DB 零 LLM（006 FR1）：节点回传 / 职业事件 / 条件缺口 / 到期行动卡
- 原则条目三要素：触发条件(if) + 行动指令(then) + 来源案例链接（Dalio/NASA LLIS/错题本共识）
- 原则状态机：draft → verified（复验有效）/ invalid（复验无效），联想纪律"一两次复盘
  别急着定规律"→ 新原则默认 draft，验证过才算数
- Try 行动卡 ≤3 条（KPT 铁律），带触发场景 + 复审日期；复审 effective 可升级为原则
- 空话闸：拒绝"要更努力"式空洞行动（006 FR3）
- 原则库唯一真相源=retro_principles 表，不做 user_memory_facts 双写（对抗审查裁决）
"""

import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.exam_timeline import ExamNode, ExamSubscription, NodeFeedback
from app.models.retrospective import (
    PrincipleStatus,
    RetroAction,
    RetroActionStatus,
    RetroPrinciple,
    Retrospective,
)

logger = logging.getLogger(__name__)

# 空话闸：action 命中这些模式且没有更具体内容时拒绝（006 FR3）
# 判定法：整句只由空话修饰词构成（无任何具体动作词）即拒绝
_VAGUE_CHARS = set(
    "要得更应该需要更加多再一定努力认真用心自律专注坚持加油刻苦勤奋学习复习备考争取下次考好一点些地，。！!？?的着了"
)


def _is_vague_action(action: str) -> bool:
    return bool(action) and all(ch in _VAGUE_CHARS for ch in action)


_MIN_ACTION_LEN = 6
_MAX_ACTIONS_PER_RETRO = 3  # KPT 铁律
_REVIEW_INTERVAL_DAYS = 14

# 冷启动示例原则（对抗审查裁决：预置示例破空态；source_snapshot 带 example 标记，
# UI 显示"示例"徽章，用户可删可改成自己的）
_EXAMPLE_PRINCIPLES = [
    {
        "trigger_scene": "模考或正式考试中，数学大题时间快失控时",
        "action": "先跳过大题最后一问，把后面两道大题的第一问拿到手，最后回头再啃",
        "rationale": "大题第一问通常是送分步，先收割确定分值比死磕难题期望值高",
        "scene_tags": ["模考崩盘", "考场策略"],
    },
    {
        "trigger_scene": "择校/选岗纠结、反复刷经验帖停不下来时",
        "action": "停止浏览新信息 24 小时，把已知的选项各写三行利弊，明天只看这张表做决定",
        "rationale": "信息过载期的边际信息量趋零，写下来才能看见真实偏好",
        "scene_tags": ["择校纠结", "选岗"],
    },
    {
        "trigger_scene": "被家长或他人质疑选择，情绪上头想吵架时",
        "action": "先把对方最担心的一件事写下来，下次谈话开场先回应这一条再讲自己的规划",
        "rationale": "反对背后是担忧，先接住担忧才听得进规划",
        "scene_tags": ["家庭沟通"],
    },
    {
        "trigger_scene": "连续几天没学习/没进度，想彻底放弃时",
        "action": "只做 10 分钟最小任务（一道题/一页笔记），做完就算今天赢",
        "rationale": "中断后重启的门槛要压到不可能失败，连续性比强度重要",
        "scene_tags": ["状态中断"],
    },
    {
        "trigger_scene": "面试或复试前一夜紧张失眠时",
        "action": "写完三个最可能被问的问题的提纲（每题三行），然后合上材料睡觉",
        "rationale": '未准备的焦虑比准备本身更耗睡眠，三题提纲给大脑一个"已做完了"的信号',
        "scene_tags": ["面试复盘", "复试"],
    },
    {
        "trigger_scene": "出分/出结果不如预期，想立刻做重大决定时",
        "action": "强制等 48 小时再做任何不可逆决定，期间只收集信息不动作",
        "rationale": "情绪峰值期做的决定大概率是发泄不是策略",
        "scene_tags": ["出分落差"],
    },
]


def _validate_action_text(action: str) -> str | None:
    """空话闸：返回错误消息或 None（通过）。"""
    action = (action or "").strip()
    if len(action) < _MIN_ACTION_LEN:
        return f"行动指令太短（至少 {_MIN_ACTION_LEN} 字），请写具体到能直接执行的做法"
    if _is_vague_action(action):
        return '"更努力/要坚持"式空话无法执行——请写成具体动作（做什么、什么时候做、做到什么程度）'
    return None


def _invalidate_chat_context(user_id: UUID) -> None:
    """原则变更后失效 chat 的 user_context 缓存（chat_service 300s TTL 的主动补刀）。"""
    try:
        from app.core.cache import invalidate_user_context

        invalidate_user_context(str(user_id))
    except Exception:
        logger.debug("invalidate_user_context 失败（靠 TTL 自然过期兜底）")


# ----------------------------------------------------------------------
# 事实回放（replay）— 四源聚合，纯 DB，零 LLM，零造假
# ----------------------------------------------------------------------


def build_replay(db: Session, user_id: UUID, start: date, end: date) -> dict:
    """聚合复盘时段内的事実原料：用户在事实层只做判断，不靠回忆。"""
    replay: dict = {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "node_feedbacks": [],
        "career_events": [],
        "condition_summary": None,
        "due_actions": [],
        "counts": {"node_done": 0, "node_uncertain": 0, "node_skipped": 0, "events": 0},
    }

    # 源1：考试时间线节点回传（done/uncertain/skipped + 节点名）
    try:
        rows = (
            db.query(NodeFeedback, ExamNode)
            .join(ExamNode, NodeFeedback.node_id == ExamNode.id)
            .join(ExamSubscription, NodeFeedback.subscription_id == ExamSubscription.id)
            .filter(
                ExamSubscription.user_id == user_id,
                NodeFeedback.feedback_at
                >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
                NodeFeedback.feedback_at
                <= datetime.combine(
                    end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
                ),
            )
            .order_by(NodeFeedback.feedback_at.desc())
            .limit(50)
            .all()
        )
        for fb, node in rows:
            replay["node_feedbacks"].append(
                {
                    "node_title": node.title,
                    "status": fb.status.value if hasattr(fb.status, "value") else str(fb.status),
                    "feedback_at": fb.feedback_at.isoformat() if fb.feedback_at else None,
                }
            )
            key = f"node_{fb.status.value if hasattr(fb.status, 'value') else fb.status}"
            replay["counts"][key] = replay["counts"].get(key, 0) + 1
    except Exception:
        logger.exception("replay 节点回传聚合失败，降级跳过")

    # 源2：职业事件（含 STAR 五字段 + 情绪）
    try:
        events = (
            db.query(CareerEvent)
            .filter(
                CareerEvent.user_id == user_id,
                CareerEvent.event_date >= start,
                CareerEvent.event_date <= end,
            )
            .order_by(CareerEvent.event_date.desc())
            .limit(50)
            .all()
        )
        for ev in events:
            replay["career_events"].append(
                {
                    "id": str(ev.id),
                    "event_date": ev.event_date.isoformat(),
                    "event_type": (
                        ev.event_type.value
                        if hasattr(ev.event_type, "value")
                        else str(ev.event_type)
                    ),
                    "title": ev.title,
                    "has_star": bool(ev.situation or ev.task or ev.action or ev.result),
                    "mood": ev.mood,
                    "reflection": ev.reflection,
                }
            )
        replay["counts"]["events"] = len(events)
    except Exception:
        logger.exception("replay 职业事件聚合失败，降级跳过")

    # 源3：条件账本缺口（最近核对的目标职位完成度）
    try:
        from app.services.condition_checklist_service import get_latest_condition_summary

        replay["condition_summary"] = get_latest_condition_summary(db, str(user_id))
    except Exception:
        logger.exception("replay 条件缺口聚合失败，降级跳过")

    # 源4：到期待复审的 Try 行动卡（复盘开场先复审上次的——M&M 开场核对同构）
    replay["due_actions"] = list_due_actions(db, user_id, include_future_days=0)

    return replay


# ----------------------------------------------------------------------
# Try 行动卡
# ----------------------------------------------------------------------


def create_actions(
    db: Session, user_id: UUID, retro_id: UUID, items: list[dict]
) -> tuple[list[RetroAction], str | None]:
    """为复盘创建行动卡。返回 (cards, error)；超过 3 条拒绝（KPT 铁律）。"""
    if not items:
        return [], None
    if len(items) > _MAX_ACTIONS_PER_RETRO:
        return (
            [],
            f"行动卡每次最多 {_MAX_ACTIONS_PER_RETRO} 条——六条 Try 意味着一条也得不到真正关注",
        )

    retro = (
        db.query(Retrospective)
        .filter(Retrospective.id == retro_id, Retrospective.user_id == user_id)
        .first()
    )
    if not retro:
        return [], "复盘记录不存在"

    today = date.today()
    cards = []
    for item in items:
        err = _validate_action_text(item.get("content", ""))
        if err:
            return [], err
        trigger = (item.get("trigger_scene") or "").strip()
        if len(trigger) < 4:
            return [], "触发场景太短——请写清'当____的时候'（越具体，下次越容易被想起来）"
        due = item.get("review_due_at")
        review_due = (
            date.fromisoformat(due) if due else today + timedelta(days=_REVIEW_INTERVAL_DAYS)
        )
        cards.append(
            RetroAction(
                user_id=user_id,
                retro_id=retro_id,
                content=item["content"].strip(),
                trigger_scene=trigger,
                status=RetroActionStatus.pending,
                review_due_at=review_due,
            )
        )
    db.add_all(cards)
    db.commit()
    for c in cards:
        db.refresh(c)
    return cards, None


def list_due_actions(db: Session, user_id: UUID, include_future_days: int = 0) -> list[dict]:
    """到期（或未来 N 天内到期）待复审的行动卡。"""
    horizon = date.today() + timedelta(days=include_future_days)
    rows = (
        db.query(RetroAction)
        .filter(
            RetroAction.user_id == user_id,
            RetroAction.status == RetroActionStatus.pending,
            RetroAction.review_due_at <= horizon,
        )
        .order_by(RetroAction.review_due_at.asc())
        .limit(20)
        .all()
    )
    return [action_to_dict(r) for r in rows]


def action_to_dict(a: RetroAction) -> dict:
    return {
        "id": str(a.id),
        "retro_id": str(a.retro_id),
        "content": a.content,
        "trigger_scene": a.trigger_scene,
        "status": a.status.value,
        "review_due_at": a.review_due_at.isoformat(),
        "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        "review_note": a.review_note,
        "principle_id": str(a.principle_id) if a.principle_id else None,
    }


def review_action(
    db: Session, user_id: UUID, action_id: UUID, verdict: str, note: str | None = None
) -> tuple[RetroAction | None, RetroPrinciple | None, str | None]:
    """复审裁决行动卡（KPT Try 复审）。

    verdict:
    - effective: 用上了且有效 → 状态落 effective；同时升级为原则（trigger+content 直转）
    - ineffective: 试了没用 → 落 ineffective，note 记原因
    - not_met: 还没遇到触发场景 → 顺延复审日 +14 天
    返回 (action, upgraded_principle, error)。
    """
    action = (
        db.query(RetroAction)
        .filter(RetroAction.id == action_id, RetroAction.user_id == user_id)
        .first()
    )
    if not action:
        return None, None, "行动卡不存在"

    if verdict == "effective":
        action.status = RetroActionStatus.effective
        principle = RetroPrinciple(
            user_id=user_id,
            trigger_scene=action.trigger_scene,
            action=action.content,
            rationale=(note or "").strip() or None,
            scene_tags=[],
            status=PrincipleStatus.verified,
            verify_count=1,
            source_retro_id=action.retro_id,
            source_snapshot={"from_action": str(action.id), "review_note": note or ""},
            next_review_at=date.today() + timedelta(days=_REVIEW_INTERVAL_DAYS),
        )
        db.add(principle)
        db.flush()
        action.principle_id = principle.id
        action.reviewed_at = datetime.now(timezone.utc)
        action.review_note = note
        db.commit()
        db.refresh(action)
        db.refresh(principle)
        _invalidate_chat_context(user_id)
        return action, principle, None

    if verdict == "ineffective":
        action.status = RetroActionStatus.ineffective
    elif verdict == "not_met":
        action.status = RetroActionStatus.pending
        action.review_due_at = date.today() + timedelta(days=_REVIEW_INTERVAL_DAYS)
    else:
        return None, None, "verdict 必须是 effective / ineffective / not_met"

    action.reviewed_at = datetime.now(timezone.utc)
    action.review_note = note
    db.commit()
    db.refresh(action)
    return action, None, None


# ----------------------------------------------------------------------
# 原则库
# ----------------------------------------------------------------------


def principle_to_dict(p: RetroPrinciple) -> dict:
    snap = p.source_snapshot or {}
    return {
        "id": str(p.id),
        "trigger_scene": p.trigger_scene,
        "action": p.action,
        "rationale": p.rationale,
        "scene_tags": p.scene_tags or [],
        "status": p.status.value,
        "verify_count": p.verify_count,
        "source_retro_id": str(p.source_retro_id) if p.source_retro_id else None,
        "source_title": snap.get("title"),
        "is_example": bool(snap.get("example")),
        "next_review_at": p.next_review_at.isoformat() if p.next_review_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def list_principles(db: Session, user_id: UUID, include_inactive: bool = False) -> list[dict]:
    q = db.query(RetroPrinciple).filter(RetroPrinciple.user_id == user_id)
    if not include_inactive:
        q = q.filter(RetroPrinciple.is_active.is_(True))
    rows = q.order_by(RetroPrinciple.created_at.desc()).all()
    # verified 优先，同状态按验证次数降序（Python 排序保证 SQLite 测试与 PG 生产一致）
    order = {PrincipleStatus.verified: 0, PrincipleStatus.draft: 1, PrincipleStatus.invalid: 2}
    rows.sort(key=lambda r: (order.get(r.status, 3), -r.verify_count))
    return [principle_to_dict(r) for r in rows]


def create_principle(
    db: Session,
    user_id: UUID,
    trigger_scene: str,
    action: str,
    rationale: str | None,
    scene_tags: list[str] | None,
    source_retro_id: UUID | None,
) -> tuple[RetroPrinciple | None, str | None]:
    """创建原则（默认 draft 态——联想纪律：一两次复盘别急着定规律）。"""
    err = _validate_action_text(action)
    if err:
        return None, err
    trigger = (trigger_scene or "").strip()
    if len(trigger) < 6:
        return None, "触发条件太短——请写清'下次遇到____情况时'，越具体越容易被想起来"

    snapshot: dict = {}
    if source_retro_id:
        retro = (
            db.query(Retrospective)
            .filter(Retrospective.id == source_retro_id, Retrospective.user_id == user_id)
            .first()
        )
        if retro:
            snapshot = {
                "title": retro.title,
                "period": f"{retro.period_start}~{retro.period_end}",
                "satisfaction": retro.satisfaction,
                "lessons_learned": (retro.lessons_learned or "")[:300],
            }

    p = RetroPrinciple(
        user_id=user_id,
        trigger_scene=trigger,
        action=action.strip(),
        rationale=(rationale or "").strip() or None,
        scene_tags=[t.strip() for t in (scene_tags or []) if t.strip()][:5],
        status=PrincipleStatus.draft,
        source_retro_id=source_retro_id,
        source_snapshot=snapshot,
        next_review_at=date.today() + timedelta(days=_REVIEW_INTERVAL_DAYS),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    _invalidate_chat_context(user_id)
    return p, None


def verify_principle(
    db: Session, user_id: UUID, principle_id: UUID, verdict: str, note: str | None = None
) -> tuple[RetroPrinciple | None, str | None]:
    """原则复审裁决：again(再次有效) / ineffective(失效) / pending(还没遇到，顺延)。"""
    p = (
        db.query(RetroPrinciple)
        .filter(RetroPrinciple.id == principle_id, RetroPrinciple.user_id == user_id)
        .first()
    )
    if not p:
        return None, "原则不存在"

    if verdict == "again":
        p.status = PrincipleStatus.verified
        p.verify_count += 1
        p.next_review_at = date.today() + timedelta(
            days=_REVIEW_INTERVAL_DAYS * max(1, p.verify_count)
        )
    elif verdict == "ineffective":
        p.status = PrincipleStatus.invalid
        p.next_review_at = None
    elif verdict == "pending":
        p.next_review_at = date.today() + timedelta(days=_REVIEW_INTERVAL_DAYS)
    else:
        return None, "verdict 必须是 again / ineffective / pending"

    if note:
        p.source_snapshot = {**(p.source_snapshot or {}), "last_review_note": note[:400]}
    db.commit()
    db.refresh(p)
    _invalidate_chat_context(user_id)
    return p, None


def update_principle(
    db: Session, user_id: UUID, principle_id: UUID, **fields
) -> tuple[RetroPrinciple | None, str | None]:
    """修订原则（原则是活的——Dalio 的原则一直在演化，修订回 draft 态重验）。"""
    p = (
        db.query(RetroPrinciple)
        .filter(RetroPrinciple.id == principle_id, RetroPrinciple.user_id == user_id)
        .first()
    )
    if not p:
        return None, "原则不存在"
    if "action" in fields and fields["action"] is not None:
        err = _validate_action_text(fields["action"])
        if err:
            return None, err
        p.action = fields["action"].strip()
        p.status = PrincipleStatus.draft  # 修订后重新走验证
    if "trigger_scene" in fields and fields["trigger_scene"]:
        trigger = fields["trigger_scene"].strip()
        if len(trigger) < 6:
            return None, "触发条件太短"
        p.trigger_scene = trigger
    if "rationale" in fields:
        p.rationale = (fields["rationale"] or "").strip() or None
    if "scene_tags" in fields and fields["scene_tags"] is not None:
        p.scene_tags = [t.strip() for t in fields["scene_tags"] if t.strip()][:5]
    db.commit()
    db.refresh(p)
    _invalidate_chat_context(user_id)
    return p, None


def deactivate_principle(db: Session, user_id: UUID, principle_id: UUID) -> bool:
    p = (
        db.query(RetroPrinciple)
        .filter(RetroPrinciple.id == principle_id, RetroPrinciple.user_id == user_id)
        .first()
    )
    if not p:
        return False
    p.is_active = False
    db.commit()
    _invalidate_chat_context(user_id)
    return True


def ensure_example_principles(db: Session, user_id: UUID) -> None:
    """冷启动：用户原则库为空时预置示例（可删可改）。幂等。"""
    count = (
        db.query(func.count(RetroPrinciple.id)).filter(RetroPrinciple.user_id == user_id).scalar()
    )
    if count:
        return
    for ex in _EXAMPLE_PRINCIPLES:
        db.add(
            RetroPrinciple(
                user_id=user_id,
                trigger_scene=ex["trigger_scene"],
                action=ex["action"],
                rationale=ex["rationale"],
                scene_tags=ex["scene_tags"],
                status=PrincipleStatus.draft,
                source_snapshot={"example": True},
            )
        )
    db.commit()


def get_principles_for_chat(db: Session, user_id: UUID, limit: int = 5) -> list[dict]:
    """chat 注入用：active 且未失效的原则，verified 优先。

    token 预算纪律：每条一行，trigger+action 各截 60 字。
    """
    try:
        rows = (
            db.query(RetroPrinciple)
            .filter(
                RetroPrinciple.user_id == user_id,
                RetroPrinciple.is_active.is_(True),
                RetroPrinciple.status != PrincipleStatus.invalid,
            )
            .order_by(RetroPrinciple.verify_count.desc(), RetroPrinciple.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "line": (
                    f"- [{'已验证' if r.status == PrincipleStatus.verified else '待验证'}"
                    f"{'×' + str(r.verify_count) if r.verify_count else ''}]"
                    f"当「{r.trigger_scene[:60]}」→ {r.action[:60]}"
                ),
                "status": r.status.value,
            }
            for r in rows
        ]
    except Exception:
        logger.exception("chat 原则注入查询失败，降级为空")
        return []
