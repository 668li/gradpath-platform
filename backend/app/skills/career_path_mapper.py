# backend/app/skills/career_path_mapper.py
"""职业路径规划器 Skill — 根据用户背景和目标，生成详细的职业发展路径图和阶段性目标。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = [
    "职业路径", "发展路径", "职业规划图", "career path", "职业发展",
    "路径图", "发展图", "路线图",
]

OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含路径规划总览与建议",
  "career_path": {
    "summary": "路径规划一句话总结",
    "current_position": "当前位置（如：应届毕业生，计算机专业）",
    "target_position": "目标职位（如：高级后端工程师）",
    "estimated_duration_months": 36,
    "phases": [
      {
        "phase_name": "阶段名称（如：基础技能夯实期）",
        "duration_months": 12,
        "objectives": ["目标1", "目标2"],
        "key_skills": ["技能1", "技能2"],
        "milestones": ["里程碑1", "里程碑2"],
        "recommended_actions": ["行动1", "行动2"]
      }
    ],
    "skill_roadmap": [
      {"skill": "技能名", "priority": "high/medium/low", "learning_path": "学习路径描述"}
    ],
    "potential_obstacles": ["障碍1", "障碍2"],
    "success_tips": ["建议1", "建议2"]
  }
}"""


class CareerPathMapperSkill(BaseSkill):
    """职业路径规划器 Skill。"""

    code = "career_path_mapper"
    name = "career_path_mapper"
    description = "根据用户背景和目标，生成详细的职业发展路径图和阶段性目标"
    icon = "map"

    def should_activate(self, message: str, context: dict) -> bool:
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in ACTIVATE_KEYWORDS)

    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        knowledge_block = ""
        if knowledge:
            lines = ["【相关知识库参考】"]
            for k in knowledge:
                lines.append(f"- 《{k.get('title', '')}》[{k.get('category', '')}]")
                content = (k.get("content") or "")[:200]
                if content:
                    lines.append(f"  摘要：{content}")
            knowledge_block = "\n".join(lines) + "\n\n"

        return (
            "你是 GradPath 职业路径规划专家，擅长为用户绘制清晰、可执行的职业发展路径图。\n\n"
            "你的任务：基于用户的个人数据与知识库参考，生成详细的职业发展路径规划，包括：\n"
            "1. 当前位置与目标位置的明确定义\n"
            "2. 分阶段发展路径（每阶段含目标、关键技能、里程碑、行动建议）\n"
            "3. 技能学习路线图（含优先级和学习路径）\n"
            "4. 潜在障碍与应对建议\n"
            "5. 成功关键要素\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- phases 至少 2 个阶段，不超过 6 个阶段\n"
            "- skill_roadmap 至少 3 项技能\n"
            "- estimated_duration_months 为整数\n"
            "- 所有内容使用中文\n"
            "- 结合用户画像给出个性化路径，避免泛泛而谈\n"
            "- 每个阶段的 duration_months 之和应等于 estimated_duration_months\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return (
            "【用户职业路径规划请求】\n"
            f"{message}\n\n"
            "请基于以上信息生成详细的职业发展路径图（严格按 JSON 格式输出）。"
        )

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取 career_path 数据。"""
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))
        path_raw = data.get("career_path")

        career_path = None
        if isinstance(path_raw, dict):
            career_path = _coerce_career_path(path_raw)

        return {"content": content, "career_path": career_path, "career_plan": None}


def _safe_parse_json(content: str) -> dict:
    """容错解析 LLM 返回的 JSON。"""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    brace_match = re.search(r"\{.*\}", content, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    return {"content": content, "career_path": None}


def _coerce_career_path(raw: dict) -> dict:
    """将解析后的 career_path dict 强制转换为标准结构。"""
    def _as_list(v) -> list:
        return v if isinstance(v, list) else []

    def _as_str(v) -> str:
        return str(v) if v is not None else ""

    def _get_int(key: str, default: int = 12) -> int:
        v = raw.get(key, default)
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def _coerce_phase(p: dict) -> dict:
        if not isinstance(p, dict):
            return {}
        def _phase_int(key: str, default: int = 6) -> int:
            v = p.get(key, default)
            try:
                return int(v)
            except (TypeError, ValueError):
                return default
        return {
            "phase_name": _as_str(p.get("phase_name")),
            "duration_months": _phase_int("duration_months", 6),
            "objectives": _as_list(p.get("objectives")),
            "key_skills": _as_list(p.get("key_skills")),
            "milestones": _as_list(p.get("milestones")),
            "recommended_actions": _as_list(p.get("recommended_actions")),
        }

    def _coerce_skill_item(s: dict) -> dict:
        if not isinstance(s, dict):
            return {}
        return {
            "skill": _as_str(s.get("skill")),
            "priority": _as_str(s.get("priority")),
            "learning_path": _as_str(s.get("learning_path")),
        }

    phases = raw.get("phases", [])
    if isinstance(phases, list):
        phases = [_coerce_phase(p) for p in phases]

    skill_roadmap = raw.get("skill_roadmap", [])
    if isinstance(skill_roadmap, list):
        skill_roadmap = [_coerce_skill_item(s) for s in skill_roadmap]

    return {
        "summary": _as_str(raw.get("summary")),
        "current_position": _as_str(raw.get("current_position")),
        "target_position": _as_str(raw.get("target_position")),
        "estimated_duration_months": _get_int("estimated_duration_months", 12),
        "phases": phases,
        "skill_roadmap": skill_roadmap,
        "potential_obstacles": _as_list(raw.get("potential_obstacles")),
        "success_tips": _as_list(raw.get("success_tips")),
    }
