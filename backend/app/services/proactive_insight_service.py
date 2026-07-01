"""AI 主动洞察服务层 — 跨数据模式识别，主动生成非显而易见的洞察。

不同于 reactive 的成长洞察（用户请求时生成），主动洞察是系统主动分析
用户数据模式后生成的，展示在看板上提醒用户注意。

洞察类型：
- pattern: 发现的行为模式（如"你连续3周在添加技术类技能"）
- reminder: 到期提醒（如"你有一个决策需要回溯评估"）
- celebration: 里程碑庆祝（如"恭喜完成第5个里程碑！"）
- warning: 风险预警（如"你的规划已逾期2周"）
- suggestion: 建议推送（如"基于你的霍兰德测评，建议探索算法方向"）
"""
import json
import re
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.career_event import CareerEvent
from app.models.career_plan import CareerPlan
from app.models.destination_decision import DestinationDecision
from app.models.proactive_insight import ProactiveInsight
from app.models.skill_node import SkillNode
from app.services.ai_service import AIService

SYSTEM_PROMPT = """你是一位敏锐的职业成长观察者。基于用户的数据，请发现 2-3 个非显而易见的洞察。

洞察要求：
- 必须基于具体数据，不能泛泛而谈
- 优先发现用户自己可能没注意到的模式
- 每个洞察包含：标题（15字以内）、详细内容（50-100字）、建议行动（30字以内）
- 用中文，语气亲切但不啰嗦

严格输出 JSON 数组：
[
  {
    "insight_type": "pattern|reminder|celebration|warning|suggestion",
    "title": "简短标题",
    "content": "详细内容",
    "action_suggestion": "建议行动",
    "priority": 1到5的整数
  }
]

不要输出 JSON 以外的内容。"""


def _build_context(db: Session, user_id: UUID) -> str:
    """组装用户全量数据用于模式分析。"""
    lines = ["【用户数据概览】"]

    # 技能趋势
    skills = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == user_id)
        .order_by(SkillNode.created_at.desc())
        .limit(20)
        .all()
    )
    if skills:
        lines.append("【技能树】")
        for s in skills[:10]:
            lines.append(f"- {s.name}(Lv{s.level}) 分类:{s.category}")

    # 近期事件
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.event_date.desc())
        .limit(15)
        .all()
    )
    if events:
        lines.append("【近期事件】")
        for ev in events[:10]:
            lines.append(f"- {ev.event_date} [{ev.event_type.value}] {ev.title}")

    # 决策与回溯
    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .limit(10)
        .all()
    )
    if decisions:
        lines.append("【历史决策】")
        for d in decisions[:5]:
            review_status = "已回溯" if d.review_completed else ("待回溯" if d.review_date else "未设回溯")
            lines.append(
                f"- {d.decision_date} [{d.destination_type.value}] "
                f"置信度={d.confidence} 回溯={review_status}"
            )

    # 活跃规划
    plans = (
        db.query(CareerPlan)
        .filter(CareerPlan.user_id == user_id, CareerPlan.status == "active")
        .all()
    )
    if plans:
        lines.append("【当前规划】")
        for p in plans:
            total = len(p.milestones) if p.milestones else 0
            done = sum(1 for m in (p.milestones or []) if isinstance(m, dict) and m.get("status") == "completed")
            lines.append(f"- 目标:{p.goal_text} 进度:{done}/{total}")

    # 测评结果
    assessment = (
        db.query(Assessment)
        .filter(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if assessment:
        lines.append(f"【霍兰德测评】编码:{assessment.result_code} 推荐:{', '.join(assessment.recommended_directions[:3])}")

    # 待回溯决策
    today = date.today()
    pending_reviews = (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.user_id == user_id,
            DestinationDecision.review_completed == False,
            DestinationDecision.review_date <= today,
        )
        .all()
    )
    if pending_reviews:
        lines.append(f"【待回溯决策】{len(pending_reviews)} 个决策已到回溯日期")

    return "\n".join(lines) if len(lines) > 1 else "用户暂无数据"


def generate_insights(db: Session, user_id: UUID) -> list[ProactiveInsight]:
    """主动分析用户数据模式，生成洞察并保存。"""
    context = _build_context(db, user_id)

    # 规则型洞察（不依赖 LLM，即时生成）
    rule_insights = _generate_rule_insights(db, user_id)

    # LLM 型洞察（深度模式识别）
    llm_insights = []
    try:
        service = AIService()
        raw = service.chat(SYSTEM_PROMPT, context, timeout=30)
        llm_insights = _parse_insights(raw)
    except Exception:
        # LLM 不可用时仅返回规则型洞察
        pass

    # 保存洞察
    all_insights = rule_insights + llm_insights
    saved = []
    for item in all_insights:
        insight = ProactiveInsight(
            user_id=user_id,
            insight_type=item.get("insight_type", "suggestion"),
            title=item.get("title", ""),
            content=item.get("content", ""),
            action_suggestion=item.get("action_suggestion"),
            priority=item.get("priority", 3),
            related_data=item.get("related_data", {}),
        )
        db.add(insight)
        saved.append(insight)

    if saved:
        db.commit()
        for s in saved:
            db.refresh(s)

    return saved


def _generate_rule_insights(db: Session, user_id: UUID) -> list[dict]:
    """基于规则即时生成洞察（不依赖 LLM）。"""
    insights = []
    today = date.today()

    # 1. 待回溯决策提醒
    pending_reviews = (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.user_id == user_id,
            DestinationDecision.review_completed == False,
            DestinationDecision.review_date <= today,
        )
        .all()
    )
    for d in pending_reviews[:2]:
        days_overdue = (today - d.review_date).days if d.review_date else 0
        insights.append({
            "insight_type": "reminder",
            "title": f"决策回溯提醒",
            "content": f"你在 {d.decision_date} 做的「{d.destination_type.value}」决策已到回溯日期{'，逾期 ' + str(days_overdue) + ' 天' if days_overdue > 0 else ''}。记录实际结果，校准你的判断力。",
            "action_suggestion": "前往去向决策页面填写回溯评估",
            "priority": 5 if days_overdue > 0 else 4,
            "related_data": {"decision_id": str(d.id)},
        })

    # 2. 逾期里程碑警告
    plans = (
        db.query(CareerPlan)
        .filter(CareerPlan.user_id == user_id, CareerPlan.status == "active")
        .all()
    )
    for p in plans[:3]:
        if not p.milestones:
            continue
        for m in p.milestones:
            if not isinstance(m, dict):
                continue
            if m.get("status") in ("completed", "in_progress"):
                continue
            deadline = m.get("deadline")
            if deadline and deadline <= today.isoformat():
                insights.append({
                    "insight_type": "warning",
                    "title": "里程碑逾期提醒",
                    "content": f"规划「{p.goal_text}」中的里程碑「{m.get('title', '未命名')}」已逾期。",
                    "action_suggestion": "调整计划或标记为进行中",
                    "priority": 4,
                    "related_data": {"plan_id": str(p.id)},
                })
                break

    # 3. 里程碑完成庆祝
    for p in plans[:3]:
        if not p.milestones:
            continue
        done = sum(1 for m in p.milestones if isinstance(m, dict) and m.get("status") == "completed")
        total = len(p.milestones)
        if done > 0 and done == total:
            insights.append({
                "insight_type": "celebration",
                "title": "规划全部完成！",
                "content": f"恭喜！你的规划「{p.goal_text}」的 {total} 个里程碑已全部完成。是时候设定下一个目标了。",
                "action_suggestion": "创建新的职业规划",
                "priority": 3,
                "related_data": {"plan_id": str(p.id)},
            })
            break

    return insights


def _parse_insights(raw: str) -> list[dict]:
    """解析 LLM 返回的洞察 JSON 数组。"""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except (json.JSONDecodeError, TypeError):
                return []
        else:
            return []

    if not isinstance(data, list):
        return []

    results = []
    for item in data[:3]:
        if not isinstance(item, dict):
            continue
        results.append({
            "insight_type": str(item.get("insight_type", "pattern")),
            "title": str(item.get("title", ""))[:200],
            "content": str(item.get("content", "")),
            "action_suggestion": str(item.get("action_suggestion", "")) or None,
            "priority": max(1, min(5, int(item.get("priority", 3)))),
        })
    return results


def list_insights(db: Session, user_id: UUID, limit: int = 10, unread_only: bool = False) -> list[ProactiveInsight]:
    """列出用户的主动洞察。"""
    query = db.query(ProactiveInsight).filter(ProactiveInsight.user_id == user_id)
    if unread_only:
        query = query.filter(ProactiveInsight.is_read == False)
    return query.order_by(ProactiveInsight.priority.desc(), ProactiveInsight.created_at.desc()).limit(limit).all()


def mark_as_read(db: Session, user_id: UUID, insight_id: UUID) -> bool:
    """标记洞察为已读。"""
    insight = (
        db.query(ProactiveInsight)
        .filter(ProactiveInsight.id == insight_id, ProactiveInsight.user_id == user_id)
        .first()
    )
    if not insight:
        return False
    insight.is_read = True
    db.commit()
    return True


def get_summary(db: Session, user_id: UUID) -> dict:
    """获取洞察摘要（未读数 + 最新洞察）。"""
    all_insights = list_insights(db, user_id, limit=10)
    unread = [i for i in all_insights if not i.is_read]
    return {
        "unread_count": len(unread),
        "total_count": len(all_insights),
        "latest_insights": all_insights[:5],
    }
