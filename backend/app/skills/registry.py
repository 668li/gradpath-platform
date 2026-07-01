# backend/app/skills/registry.py
"""Skill 注册表 — 管理所有可用 Skill 的注册与匹配。"""
from app.skills.base import BaseSkill
from app.skills.career_planning import CareerPlanningSkill
from app.skills.career_transition import CareerTransitionSkill
from app.skills.default_skill import DefaultSkill
from app.skills.grad_school_planning import GradSchoolPlanningSkill
from app.skills.interview_simulation import InterviewSimulationSkill
from app.skills.resume_diagnosis import ResumeDiagnosisSkill

# 注册顺序决定匹配优先级；DefaultSkill 始终最后作为兜底
SKILL_REGISTRY: list[BaseSkill] = [
    CareerPlanningSkill(),
    GradSchoolPlanningSkill(),
    CareerTransitionSkill(),
    ResumeDiagnosisSkill(),
    InterviewSimulationSkill(),
    DefaultSkill(),  # Always last as fallback
]


def find_skill(message: str, context: dict) -> BaseSkill:
    """找到匹配的 Skill，默认返回 DefaultSkill。"""
    for skill in SKILL_REGISTRY:
        if skill.should_activate(message, context):
            return skill
    return SKILL_REGISTRY[-1]  # DefaultSkill


def get_skill(code: str) -> BaseSkill | None:
    """按 code 获取 Skill。"""
    for skill in SKILL_REGISTRY:
        if skill.code == code:
            return skill
    return None


def list_skills() -> list[dict]:
    """列出所有可用 Skill。"""
    return [
        {"code": s.code, "name": s.name, "description": s.description, "icon": s.icon}
        for s in SKILL_REGISTRY
    ]
