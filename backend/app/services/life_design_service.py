"""人生设计引擎服务层 — AI Life Design 七步法落地。

将模糊焦虑转化为结构化行动：
人生审计(AI提问10个直击灵魂的问题) → 愿景构建 → 90天冲刺 → 周复盘 → 季度回顾
"""
import json
import re
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.life_design import LifeDesignSprint, WeeklyReview
from app.services.ai_service import AIService
from app.services.ai_orchestrator import AIOrchestrator

# 领域定义
DOMAIN_NAMES = {
    "career": "职业发展",
    "finance": "财务状况",
    "health": "身心健康",
    "relationships": "人际关系",
    "growth": "个人成长",
    "fun": "乐趣休闲",
    "environment": "生活环境",
    "spirituality": "意义灵性",
}

# 人生审计问题库（按领域分组）
AUDIT_QUESTIONS = {
    "career": [
        "你现在的工作/学业状态让你感到充实还是消耗？具体是哪些部分？",
        "如果完全不考虑金钱，你最想从事什么职业或方向？是什么阻止了你？",
    ],
    "finance": [
        "你目前的财务状况让你感到安全还是焦虑？你理想的财务状态是什么样的？",
        "你有哪些消费习惯是在悄悄消耗你的未来资源？",
    ],
    "health": [
        "你的身体和心理健康在过去三个月里是变好了还是变差了？主要影响因素是什么？",
        "如果健康满分是10分，你给自己打几分？为什么不是更高？",
    ],
    "relationships": [
        "你生活中最重要的关系（家人/朋友/伴侣）目前给你带来的是能量还是消耗？",
        "有没有一段你想改善但一直在回避的关系？是什么在阻碍你？",
    ],
    "growth": [
        "过去六个月，你在哪些方面真正成长了？哪些方面停滞了？",
        "你内心深处最想突破的限制性信念或恐惧是什么？",
    ],
}


def generate_audit_questions(focus_areas: list[str]) -> list[dict]:
    """生成人生审计问题（不依赖 LLM，基于问题库）。"""
    questions = []
    for area in focus_areas:
        if area in AUDIT_QUESTIONS:
            for q in AUDIT_QUESTIONS[area]:
                questions.append({
                    "domain": area,
                    "domain_name": DOMAIN_NAMES.get(area, area),
                    "question": q,
                })
    # 如果用户没有选择领域，返回全部
    if not questions:
        for area, qs in AUDIT_QUESTIONS.items():
            for q in qs:
                questions.append({
                    "domain": area,
                    "domain_name": DOMAIN_NAMES.get(area, area),
                    "question": q,
                })
    return questions


async def generate_vision_from_audit(db: Session, user_id: UUID, audit_qa: list[dict]) -> str:
    """基于审计问答，AI 生成 2-3 年愿景声明。"""
    system_prompt = """你是一位人生设计教练。基于用户的人生审计问答，帮助他们构建一个清晰的 2-3 年理想生活愿景。

要求：
- 基于审计中暴露的真实痛点和渴望
- 具体而非空泛（不要"过上幸福生活"这种废话）
- 包含 2-3 个领域的具体画面
- 语气温暖但有力，200-300 字
- 不使用 markdown 格式"""

    qa_text = "\n".join(
        f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}"
        for item in audit_qa
        if item.get("answer")
    )

    if not qa_text.strip():
        return "请先完成人生审计，AI 才能为你生成个性化愿景。"

    orchestrator = AIOrchestrator()
    return await orchestrator.chat(system_prompt=system_prompt, user_prompt=qa_text, timeout=30)


def create_sprint(db: Session, user_id: UUID, data: dict) -> LifeDesignSprint:
    """创建一个 90 天冲刺。"""
    sprint = LifeDesignSprint(
        user_id=user_id,
        name=data["name"],
        primary_domain=data["primary_domain"],
        maintenance_domains=data.get("maintenance_domains", []),
        start_date=data["start_date"],
        end_date=data["end_date"],
        goals=data.get("goals", []),
        vision_statement=data.get("vision_statement"),
        audit_summary=data.get("audit_summary"),
        audit_qa=data.get("audit_qa", []),
        status="planned",
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return sprint


def get_active_sprint(db: Session, user_id: UUID) -> LifeDesignSprint | None:
    """获取当前活跃的冲刺。"""
    return (
        db.query(LifeDesignSprint)
        .filter(LifeDesignSprint.user_id == user_id, LifeDesignSprint.status == "active")
        .first()
    )


def get_sprints(db: Session, user_id: UUID) -> list[LifeDesignSprint]:
    """获取用户所有冲刺。"""
    return (
        db.query(LifeDesignSprint)
        .filter(LifeDesignSprint.user_id == user_id)
        .order_by(LifeDesignSprint.start_date.desc())
        .all()
    )


def activate_sprint(db: Session, user_id: UUID, sprint_id: UUID) -> LifeDesignSprint:
    """激活一个冲刺（同时将其他冲刺设为已完成或放弃）。"""
    # 先停用其他活跃冲刺
    others = (
        db.query(LifeDesignSprint)
        .filter(LifeDesignSprint.user_id == user_id, LifeDesignSprint.status == "active")
        .all()
    )
    for o in others:
        o.status = "completed"

    sprint = db.query(LifeDesignSprint).filter(
        LifeDesignSprint.id == sprint_id, LifeDesignSprint.user_id == user_id
    ).first()
    if not sprint:
        raise ValueError("冲刺不存在")

    sprint.status = "active"
    db.commit()
    db.refresh(sprint)
    return sprint


async def generate_sprint_review(db: Session, sprint_id: UUID) -> str:
    """AI 生成季度回顾分析。"""
    sprint = db.query(LifeDesignSprint).filter(LifeDesignSprint.id == sprint_id).first()
    if not sprint:
        raise ValueError("冲刺不存在")

    system_prompt = """你是一位人生设计教练，正在帮用户做季度回顾。

基于这个90天冲刺的数据，请分析：
1. 主攻领域目标完成情况如何？
2. 维护领域是否守住底线？
3. 最大的收获和最大的遗憾是什么？
4. 下个季度应该聚焦什么？

请用中文回复，300-400 字，语气真诚不客套。不使用 markdown 格式。"""

    context = f"""冲刺名称：{sprint.name}
主攻领域：{DOMAIN_NAMES.get(sprint.primary_domain, sprint.primary_domain)}
周期：{sprint.start_date} 到 {sprint.end_date}
愿景：{sprint.vision_statement or '未设定'}

目标：
"""
    for i, g in enumerate(sprint.goals, 1):
        if isinstance(g, dict):
            context += f"  {i}. {g.get('title', '?')} — 可衡量结果: {g.get('measurable_result', '?')}\n"

    if sprint.review_notes:
        context += f"\n用户自述回顾：{sprint.review_notes}"

    orchestrator = AIOrchestrator()
    analysis = await orchestrator.chat(system_prompt=system_prompt, user_prompt=context, timeout=30)
    sprint.ai_review = analysis
    db.commit()
    return analysis


# === 周复盘 ===

async def create_weekly_review(db: Session, user_id: UUID, data: dict) -> WeeklyReview:
    """创建周复盘。"""
    review = WeeklyReview(
        user_id=user_id,
        sprint_id=data.get("sprint_id"),
        week_start=data["week_start"],
        week_end=data["week_end"],
        planned_actions=data.get("planned_actions"),
        actual_actions=data.get("actual_actions"),
        what_worked=data.get("what_worked"),
        what_didnt_work=data.get("what_didnt_work"),
        next_week_plan=data.get("next_week_plan"),
        energy_level=data.get("energy_level"),
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # 自动生成 AI 分析
    await _generate_weekly_ai_analysis(db, review)
    return review


async def _generate_weekly_ai_analysis(db: Session, review: WeeklyReview):
    """AI 分析周复盘。"""
    system_prompt = """你是一位问责教练，正在看用户的周复盘。请给出：
1. 一个具体的鼓励（基于他实际做了的事，不要空洞）
2. 一个尖锐但善意的观察（关于计划 vs 实际的差距）
3. 一个下周的具体建议

用中文，150 字以内，不使用 markdown。"""

    context = f"""本周计划：{review.planned_actions or '未填写'}
实际完成：{review.actual_actions or '未填写'}
什么有效：{review.what_worked or '未填写'}
什么没效：{review.what_didnt_work or '未填写'}
下周计划：{review.next_week_plan or '未填写'}
能量水平：{review.energy_level or '未评'}/5"""

    try:
        orchestrator = AIOrchestrator()
        review.ai_analysis = await orchestrator.chat(system_prompt=system_prompt, user_prompt=context, timeout=30)
        db.commit()
    except Exception:
        pass


def get_weekly_reviews(db: Session, user_id: UUID, limit: int = 10) -> list[WeeklyReview]:
    return (
        db.query(WeeklyReview)
        .filter(WeeklyReview.user_id == user_id)
        .order_by(WeeklyReview.week_start.desc())
        .limit(limit)
        .all()
    )
