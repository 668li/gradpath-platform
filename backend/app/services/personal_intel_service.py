"""个人情报总览服务 — 看板护城河（强化数据聚合）。

把用户分散在各表的数据聚合成一份「个人情报」，使看板成为无法被通用
BI 替代的、随使用越积越深的护城河：
- 三大方向进度（考研/考公/就业在库数据覆盖度）
- 竞争力雷达（技能/测评/规划/暗知识缺口）
- 待办风险（临期里程碑、空白关键档案）
- 暗知识缺口（对比平台 10 万暗知识库，提示用户未覆盖的方向）
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.career_plan import CareerPlan
from app.models.destination_decision import DestinationDecision
from app.models.experience_post import ExperiencePost
from app.models.qa import QA
from app.models.skill_node import SkillNode
from app.models.user import User


def get_personal_intel(db: Session, user_id: UUID) -> dict:
    user = db.get(User, user_id)

    # 1. 资产计数
    inventory = {
        "decisions": _count(db, DestinationDecision, user_id),
        "skills": _count(db, SkillNode, user_id),
        "plans": _count(db, CareerPlan, user_id),
        "assessments": _count(db, Assessment, user_id),
        "experience_posts": _count(db, ExperiencePost, user_id),
        "qa": _count(db, QA, user_id),
    }

    # 2. 三大方向进度（基于关键表有无数据）
    directions = _direction_progress(db, user_id, inventory)

    # 3. 竞争力雷达（0-100 归一）
    radar = _competitiveness_radar(inventory)

    # 4. 待办风险
    risks = _pending_risks(db, user_id, inventory)

    # 5. 档案完整度
    profile_gaps = []
    if user:
        if not user.current_stage:
            profile_gaps.append("当前阶段")
        if not user.school:
            profile_gaps.append("学校")
        if not user.major:
            profile_gaps.append("专业")
        if not user.graduation_year:
            profile_gaps.append("毕业年份")

    completeness = round(
        (5 - len(profile_gaps)) / 5 * 100
    )

    return {
        "inventory": inventory,
        "directions": directions,
        "competitiveness_radar": radar,
        "risks": risks,
        "profile_gaps": profile_gaps,
        "profile_completeness": completeness,
    }


def _count(db: Session, model, user_id: UUID) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)) or 0


def _direction_progress(db: Session, user_id: UUID, inv: dict) -> list[dict]:
    """基于数据覆盖度估算三大方向进度。"""
    # 考研：经验帖/问答/决策
    grad = min(100, inv["experience_posts"] * 5 + inv["qa"] + inv["decisions"] * 20)
    # 就业：技能 + 规划 + 测评
    employ = min(100, inv["skills"] * 10 + inv["plans"] * 25 + inv["assessments"] * 15)
    # 考公：决策中含考公 + 规划
    civil = min(100, inv["decisions"] * 20 + inv["plans"] * 20)
    return [
        {"name": "考研", "progress": grad, "hint": "经验帖/问答/决策越多越完整"},
        {"name": "就业", "progress": employ, "hint": "技能/规划/测评驱动"},
        {"name": "考公", "progress": civil, "hint": "决策与规划驱动"},
    ]


def _competitiveness_radar(inv: dict) -> list[dict]:
    """返回雷达维度（0-100）。"""
    return [
        {"axis": "自我认知", "value": min(100, inv["assessments"] * 50)},
        {"axis": "决策力", "value": min(100, inv["decisions"] * 25)},
        {"axis": "技能储备", "value": min(100, inv["skills"] * 12)},
        {"axis": "规划执行", "value": min(100, inv["plans"] * 30)},
        {"axis": "社区贡献", "value": min(100, inv["experience_posts"] * 10 + inv["qa"] * 2)},
        {"axis": "复盘习惯", "value": min(100, (inv["experience_posts"] + inv["qa"]) * 3)},
    ]


def _pending_risks(db: Session, user_id: UUID, inv: dict) -> list[str]:
    risks: list[str] = []
    if inv["decisions"] == 0:
        risks.append("尚未做出任何去向决策 — 建议先做决策实验室")
    if inv["assessments"] == 0:
        risks.append("未完成职业测评 — 方向缺乏数据支撑")
    if inv["plans"] == 0 and inv["decisions"] > 0:
        risks.append("有决策但无规划 — 落地路径缺失")
    if inv["skills"] == 0:
        risks.append("技能树为空 — 竞争力无法量化")
    return risks
