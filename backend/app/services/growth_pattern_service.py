"""成长模式智能服务层 — 分析历史数据，发现非显而易见的模式。

真正有价值的不是"你做了多少事"，而是"你的行为模式揭示了什么"。
"""
import json
import re
from collections import Counter
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.career_plan import CareerPlan
from app.models.decision_analysis import DecisionAnalysis
from app.models.destination_decision import DestinationDecision
from app.models.life_design import LifeDesignSprint
from app.models.milestone_log import MilestoneLog
from app.models.skill_node import SkillNode
from app.services.ai_service import AIService
from app.services.ai_orchestrator import AIOrchestrator


def analyze_patterns(db: Session, user_id: UUID) -> dict:
    """分析用户历史数据，发现成长模式。"""
    patterns = []
    data_points = {}

    # 1. 技能偏好分析
    skills = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == user_id)
        .order_by(SkillNode.created_at.desc())
        .all()
    )
    if skills:
        categories = Counter(s.category for s in skills if s.category)
        total = sum(categories.values())
        if total >= 3:
            top_cat = categories.most_common(1)[0]
            top_pct = round(top_cat[1] / total * 100)
            if top_pct >= 60:
                patterns.append({
                    "pattern_type": "skill_bias",
                    "title": f"技能投入偏重{top_cat[0]}（{top_pct}%）",
                    "description": f"你记录的 {total} 个技能中，{top_cat[1]} 个属于「{top_cat[0]}」类别，占比 {top_pct}%。过度集中在单一类别可能限制了可迁移性。",
                    "data_points": {"total": total, "categories": dict(categories)},
                    "suggestion": "考虑发展一个互补领域的技能，例如沟通/项目管理，这会让你的技能组合更有竞争力。",
                })
            data_points["skill_categories"] = dict(categories)

    # 2. 决策置信度校准
    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .all()
    )
    reviewed = [d for d in decisions if d.review_completed]
    if len(reviewed) >= 3:
        avg_confidence = sum(d.confidence for d in reviewed) / len(reviewed)
        # 简单判断准确率：如果 actual_outcome 包含正面词汇则为准确
        positive_words = ["成功", "满意", "顺利", "正确", "值得", "好", "对", "达到", "实现"]
        accurate = sum(
            1 for d in reviewed
            if d.actual_outcome and any(w in d.actual_outcome for w in positive_words)
        )
        accuracy_rate = accurate / len(reviewed)
        calibration_gap = abs(avg_confidence / 5 - accuracy_rate)

        if calibration_gap > 0.2:
            if avg_confidence / 5 > accuracy_rate:
                patterns.append({
                    "pattern_type": "confidence_calibration",
                    "title": "决策过度自信",
                    "description": f"你的平均决策置信度为 {avg_confidence:.1f}/5（{avg_confidence/5*100:.0f}%），但回溯准确率仅 {accuracy_rate*100:.0f}%。差距 {calibration_gap*100:.0f} 个百分点，说明你倾向于高估自己的判断。",
                    "data_points": {
                        "avg_confidence": round(avg_confidence, 2),
                        "accuracy_rate": round(accuracy_rate, 2),
                        "gap": round(calibration_gap, 2),
                        "reviewed_count": len(reviewed),
                    },
                    "suggestion": "在做下一个决策前，试试预验尸分析——假设决策失败了，列出10个原因。这会帮你校准过度自信。",
                })
            else:
                patterns.append({
                    "pattern_type": "confidence_calibration",
                    "title": "决策不够自信",
                    "description": f"你的平均决策置信度仅 {avg_confidence:.1f}/5，但回溯准确率达 {accuracy_rate*100:.0f}%。你的判断比你以为的更准。",
                    "data_points": {
                        "avg_confidence": round(avg_confidence, 2),
                        "accuracy_rate": round(accuracy_rate, 2),
                    },
                    "suggestion": "你的直觉比你以为的更可靠。下次做决策时可以多一点勇气。",
                })
        data_points["calibration"] = {
            "avg_confidence": round(avg_confidence, 2),
            "accuracy_rate": round(accuracy_rate, 2),
            "gap": round(calibration_gap, 2),
        }

    # 3. 里程碑完成节奏（MilestoneLog 通过 plan_id 关联用户的规划）
    plan_ids = [
        p.id
        for p in db.query(CareerPlan.id).filter(CareerPlan.user_id == user_id).all()
    ]
    logs = (
        db.query(MilestoneLog)
        .filter(MilestoneLog.plan_id.in_(plan_ids))
        .order_by(MilestoneLog.logged_date.desc())
        .limit(50)
        .all()
    ) if plan_ids else []
    if len(logs) >= 5:
        # 分析按星期的活跃分布
        weekday_counts = Counter(log.logged_date.weekday() for log in logs)
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        most_active_day = weekday_counts.most_common(1)[0]
        if most_active_day[1] >= 3:
            day_name = weekday_names[most_active_day[0]]
            pct = round(most_active_day[1] / len(logs) * 100)
            patterns.append({
                "pattern_type": "momentum",
                "title": f"你的高效日是{day_name}",
                "description": f"在 {len(logs)} 条执行记录中，{pct}% 发生在{day_name}。这可能是你状态最好的时间窗口。",
                "data_points": {
                    "weekday_distribution": {weekday_names[k]: v for k, v in weekday_counts.items()},
                    "total_logs": len(logs),
                },
                "suggestion": f"把最重要的里程碑任务安排在{day_name}，利用你的自然能量节奏。",
            })
        data_points["weekday_distribution"] = {weekday_names[k]: v for k, v in weekday_counts.items()}

    # 4. LLM 深度模式分析（如果有足够数据）
    if len(patterns) >= 1 or len(skills) + len(decisions) + len(logs) >= 10:
        llm_patterns = _llm_pattern_analysis(db, user_id, skills, decisions, logs)
        patterns.extend(llm_patterns)

    # 校准分数
    calibration_score = 50
    if "calibration" in data_points:
        gap = data_points["calibration"]["gap"]
        calibration_score = max(0, min(100, 100 - int(gap * 200)))
    elif patterns:
        calibration_score = 70

    total_data = len(skills) + len(decisions) + len(logs)

    return {
        "patterns": patterns[:6],
        "calibration_score": calibration_score,
        "total_data_points": total_data,
    }


def _llm_pattern_analysis(db: Session, user_id: UUID, skills, decisions, logs) -> list[dict]:
    """LLM 深度模式分析。"""
    system_prompt = """你是一位行为数据分析师。基于用户的历史数据，发现 1-2 个非显而易见的成长模式。

要求：
- 必须基于具体数据，不能泛泛而谈
- 优先发现用户自己没注意到的模式
- 每个模式包含：pattern_type, title, description, suggestion
- 用中文，简洁有力

严格输出 JSON 数组：
[{"pattern_type": "string", "title": "15字以内", "description": "50-100字", "suggestion": "30字以内建议"}]
不要输出 JSON 以外的内容。"""

    context = "【用户数据概览】\n"
    if skills:
        context += f"技能：{len(skills)}个，分类分布：{dict(Counter(s.category for s in skills if s.category))}\n"
        context += f"平均等级：{sum(s.level for s in skills)/len(skills):.1f}\n"
    if decisions:
        context += f"决策：{len(decisions)}个，平均置信度：{sum(d.confidence for d in decisions)/len(decisions):.1f}/5\n"
        reviewed = [d for d in decisions if d.review_completed]
        context += f"已回溯：{len(reviewed)}个\n"
    if logs:
        context += f"执行记录：{len(logs)}条\n"
        statuses = Counter(log.status for log in logs)
        context += f"状态分布：{dict(statuses)}\n"

    if len(context) < 50:
        return []

    try:
        orchestrator = AIOrchestrator()
        raw = orchestrator.chat(system_prompt=system_prompt, user_prompt=context, timeout=30)
        data = json.loads(raw)
        if not isinstance(data, list):
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                return []
        return [
            {
                "pattern_type": str(p.get("pattern_type", "pattern")),
                "title": str(p.get("title", ""))[:50],
                "description": str(p.get("description", "")),
                "data_points": {},
                "suggestion": str(p.get("suggestion", "")),
            }
            for p in data[:2]
            if isinstance(p, dict)
        ]
    except Exception:
        return []
