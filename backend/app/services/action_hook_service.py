# backend/app/services/action_hook_service.py
"""行动钩子服务（speckit 003 FR2/FR3/FR7）——把回答的终点变成动作入口。

按用户消息命中的数据域 + 真实沉淀状态，生成 ≤2 个"三态诚实"的钩子：
- 可执行：指向真实入口（未订阅→订阅页 / 有待回传→回传锚点 / 有活跃计划→微行动面板）；
- 已做过：不出（已订阅绝不再推销订阅；无待回传绝不出回传钩子）；
- 无沉淀：给探索型钩子（不锁赛道，身份面覆盖：测评/微行动对所有身份开放）。

纯服务端模板 + 库数据插值，不走 LLM——零幻觉面、429 不影响、可测。
与 inject_data/沉淀块同库同 session 同口径（spec A2）；整段异常降级为
空表，绝不阻塞正常回答（FR7）。文案含日期时必须过宪法 4 分级——
当前钩子文案刻意不含日期（订阅/回传/打卡动作不需要日期），从构造上
消灭该风险面；将来加带日期的钩子必须先接 tone 判定。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 每轮最多钩子数（FR7 防膨胀）
HOOK_MAX = 2

# 探索型钩子：无任何沉淀时给（身份覆盖：测评/微行动对所有身份开放，不锁赛道）
_EXPLORE_HOOKS = [
    {
        "type": "explore",
        "text": "做一个 3 分钟微测评，建议才能对得上你的情况",
        "link": "/assessment",
    },
    {
        "type": "explore",
        "text": "从 20 分钟的 7 天微行动开始，先动起来",
        "link": "/micro-actions",
    },
]


def build_action_hooks(
    db: Session,
    user_id,
    content: str,
    covered_domains: frozenset[str] = frozenset(),
) -> list[dict]:
    """生成当轮行动钩子。任何异常返回 []（FR7 降级负例）。"""
    try:
        return _build(db, user_id, content or "", covered_domains)
    except Exception as e:  # noqa: BLE001 — 钩子失败不阻塞回答
        logger.debug("action hooks 整体降级为空: %s", e)
        return []


def _build(db: Session, user_id, content: str, covered_domains: frozenset[str]) -> list[dict]:
    hooks: list[dict] = []
    domains = _detect_domains(content)

    # timeline / announcements 域 → 订阅钩子 + 回传钩子
    # （与 covered_domains 无关：钩子是动作入口，不随数据注入层分工变化）
    if "timeline" in domains or "announcements" in domains:
        hooks += _timeline_hooks(db, user_id)

    # 微行动打卡钩子：任何域都给（行为设计闭环，北极星回传率的另一条腿）
    hooks += _micro_hooks(db, user_id)

    if not hooks:
        hooks = list(_EXPLORE_HOOKS)
    return hooks[:HOOK_MAX]


def _detect_domains(content: str) -> set[str]:
    """复用数据搜索层的意图词表（同一套口径，零额外维护面）。"""
    from app.services.data_search_service import detect_data_intents

    return {i.domain for i in detect_data_intents(content)}


def _timeline_hooks(db: Session, user_id) -> list[dict]:
    from app.models.exam_timeline import Exam, ExamSubscription
    from app.services.data_search_service import _pick_timeline_exam
    from app.services.sedimentation_service import get_pending_feedback_nodes

    exam_ref = _pick_timeline_exam(db, None)
    if exam_ref is None:
        return []
    exam = db.query(Exam).filter(Exam.code == exam_ref["code"]).first()
    if exam is None:
        return []

    hooks: list[dict] = []
    # 已做过判定（FR3）：该考次已有订阅 ⇒ 不出订阅钩子。直接查订阅表存在性，
    # 不借 sedimentation 的"最近 3 条"切片（老用户订阅多时会漏判）。
    subscribed = (
        db.query(ExamSubscription.id)
        .filter(
            ExamSubscription.user_id == str(user_id),
            ExamSubscription.exam_id == exam.id,
        )
        .first()
        is not None
    )
    if not subscribed:
        hooks.append(
            {
                "type": "subscribe_timeline",
                "text": f"帮你盯 {exam.name} 的时间线，节点准时提醒",
                "link": "/civil-service?tab=timeline",
            }
        )

    pending = get_pending_feedback_nodes(db, user_id)
    for node, p_exam in pending:
        hooks.append(
            {
                "type": "feedback_node",
                "text": f"{p_exam.name}的「{node.title}」完成了吗？30 秒回传",
                "link": f"/civil-service?tab=timeline&node={node.id}",
            }
        )
    return hooks


def _micro_hooks(db: Session, user_id) -> list[dict]:
    from app.models.micro_action import MicroActionPlan, MicroActionTask

    plan = (
        db.query(MicroActionPlan)
        .filter(MicroActionPlan.user_id == user_id, MicroActionPlan.status == "active")
        .order_by(MicroActionPlan.started_at.desc())
        .first()
    )
    if plan is None:
        return []
    nxt = (
        db.query(MicroActionTask)
        .filter(MicroActionTask.plan_id == plan.id, MicroActionTask.status == "pending")
        .order_by(MicroActionTask.day_number)
        .first()
    )
    if nxt is None:
        # 计划内全部完成：不催打卡，引导新计划由探索型/沉淀块承接
        return []
    return [
        {
            "type": "micro_checkin",
            "text": f"第 {nxt.day_number} 天的「{nxt.title}」做完告诉我",
            "link": "/micro-actions",
        }
    ]
