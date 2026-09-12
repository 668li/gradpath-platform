# backend/app/services/sedimentation_service.py
"""用户沉淀摘要（speckit 003 FR1）——"记忆感"的原材料。

从四类真实沉淀实时组一段可直接追加到 system prompt 的文本：
订阅（ExamSubscription）、待回传节点（已发提醒且无 NodeFeedback）、
微行动（MicroActionPlan/Task）、连击（StreakRecord）。

设计约束：
- 每轮实时查、不进 build_user_context 的 300s 缓存——"刚回传就被引用"的
  新鲜度优先；四组均为索引小查询（<10ms 量级），无缓存必要。
- 逐段 try/except 独立降级：任何一段查询失败只丢该段，绝不让记忆感拖垮对话。
- 待回传/订阅的判定定义在此单点，action_hook_service 复用同一函数
  （research R3：两处消费一套口径，不出现"两套口径"前科）。

零造假（宪法 1）：块内每一行都来自库查询结果；用户无沉淀返回空串，
由 chat_service.apply_sedimentation 追加"禁虚构"纪律行。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 上下文里最多引用的订阅/待回传条数（记忆感靠"一条点中"，不靠堆列表）
_SUB_LIMIT = 3
_PENDING_LIMIT = 2


def build_sedimentation_block(db: Session, user_id) -> str:
    """组【用户沉淀】块；用户无任何沉淀返回空字符串。"""
    lines: list[str] = []
    lines += _subscription_lines(db, user_id)
    lines += _pending_feedback_lines(db, user_id)
    lines += _micro_action_lines(db, user_id)
    lines += _streak_lines(db, user_id)
    if not lines:
        return ""
    return "【用户沉淀（真实库数据，引用必须与此一致，禁止编造）】\n" + "\n".join(lines)


# ----------------------------------------------------------------------
# 公共查询（钩子服务同源复用：订阅/待回传判定各只有这一个定义）
# ----------------------------------------------------------------------


def get_user_subscriptions(db: Session, user_id) -> list:
    """用户的考次订阅（带 exam），最多 _SUB_LIMIT 条；查询失败返回空表。"""
    from app.models.exam_timeline import ExamSubscription

    try:
        return (
            db.query(ExamSubscription)
            .filter(ExamSubscription.user_id == str(user_id))
            .order_by(ExamSubscription.created_at.desc())
            .limit(_SUB_LIMIT)
            .all()
        )
    except Exception as e:  # noqa: BLE001 — 沉淀段独立降级
        logger.debug("订阅沉淀查询失败: %s", e)
        return []


def get_pending_feedback_nodes(db: Session, user_id) -> list[tuple]:
    """已发过提醒且尚无回传的节点，[(ExamNode, Exam)]，最多 _PENDING_LIMIT 条。

    待回传的诚实定义 = TimelineReminderLog 有记录（提醒真实到过用户）
    ∩ NodeFeedback 无行（没回传过）。查询失败返回空表。
    """
    from app.models.exam_timeline import (
        Exam,
        ExamNode,
        ExamSubscription,
        NodeFeedback,
        TimelineReminderLog,
    )

    try:
        logged_node_ids = [
            row[0]
            for row in db.query(TimelineReminderLog.node_id)
            .filter(TimelineReminderLog.user_id == str(user_id))
            .distinct()
            .all()
        ]
        if not logged_node_ids:
            return []
        feedback_node_ids = {
            row[0]
            for row in db.query(NodeFeedback.node_id)
            .join(ExamSubscription, NodeFeedback.subscription_id == ExamSubscription.id)
            .filter(ExamSubscription.user_id == str(user_id))
            .all()
        }
        pending = [nid for nid in logged_node_ids if nid not in feedback_node_ids]
        if not pending:
            return []
        rows = (
            db.query(ExamNode, Exam)
            .join(Exam, ExamNode.exam_id == Exam.id)
            .filter(ExamNode.id.in_(pending))
            .order_by(ExamNode.node_seq)
            .limit(_PENDING_LIMIT)
            .all()
        )
        return [(node, exam) for node, exam in rows]
    except Exception as e:  # noqa: BLE001 — 沉淀段独立降级
        logger.debug("待回传沉淀查询失败: %s", e)
        return []


# ----------------------------------------------------------------------
# 四段组块
# ----------------------------------------------------------------------


def _subscription_lines(db: Session, user_id) -> list[str]:
    subs = get_user_subscriptions(db, user_id)
    out: list[str] = []
    for s in subs:
        exam = s.exam
        if exam is None:
            continue
        out.append(f"- 已订阅考次：{exam.name}{_since_suffix(s.created_at, '订阅')}")
    return out


def _pending_feedback_lines(db: Session, user_id) -> list[str]:
    out: list[str] = []
    for node, exam in get_pending_feedback_nodes(db, user_id):
        out.append(f"- 待回传节点：{exam.name}·{node.title}（提醒已发，等用户说一句完成没完成）")
    return out


def _micro_action_lines(db: Session, user_id) -> list[str]:
    from app.models.micro_action import MicroActionPlan, MicroActionTask

    try:
        plan = (
            db.query(MicroActionPlan)
            .filter(MicroActionPlan.user_id == user_id, MicroActionPlan.status == "active")
            .order_by(MicroActionPlan.started_at.desc())
            .first()
        )
        if plan is None:
            return []
        tasks = (
            db.query(MicroActionTask)
            .filter(MicroActionTask.plan_id == plan.id)
            .order_by(MicroActionTask.day_number)
            .all()
        )
        done = sum(1 for t in tasks if t.status == "completed")
        line = f"- 进行中的 7 天微行动：{plan.target_role or plan.target_path}（已完成 {done}/{len(tasks)} 天"
        nxt = next((t for t in tasks if t.status == "pending"), None)
        if nxt is not None:
            line += f"，下次：第 {nxt.day_number} 天「{nxt.title}」"
        line += "）"
        return [line]
    except Exception as e:  # noqa: BLE001 — 沉淀段独立降级
        logger.debug("微行动沉淀查询失败: %s", e)
        return []


def _streak_lines(db: Session, user_id) -> list[str]:
    from app.models.streak import StreakRecord

    try:
        rec = (
            db.query(StreakRecord)
            .filter(StreakRecord.user_id == user_id)
            .order_by(StreakRecord.activity_date.desc())
            .first()
        )
        if rec is None or not rec.streak_count:
            return []
        return [f"- 微行动连击：{rec.streak_count} 天"]
    except Exception as e:  # noqa: BLE001 — 沉淀段独立降级
        logger.debug("连击沉淀查询失败: %s", e)
        return []


def _since_suffix(created_at, verb: str) -> str:
    """ "X 天前订阅"式相对时间；时间缺失/比对异常一律降级为空，不阻塞组块。"""
    if created_at is None:
        return ""
    try:
        dt = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        days = max((datetime.now(timezone.utc) - dt).days, 0)
        return f"（{days} 天前{verb}）" if days else f"（刚{verb}）"
    except Exception:  # noqa: BLE001
        return ""
