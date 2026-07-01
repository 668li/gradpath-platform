# backend/app/skills/career_planning.py
"""职业路径规划 Skill — 生成结构化职业规划。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

# 激活关键词
ACTIVATE_KEYWORDS = [
    "规划", "路径", "怎么进", "如何准备", "目标", "进大厂",
    "职业规划", "发展路径", "career plan", "career",
]

# 期望的 LLM JSON 输出格式说明
OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含规划总览与建议",
  "career_plan": {
    "goal": "用户的职业目标（如：3年内进入字节跳动后端开发岗）",
    "current_state": {"skills": "当前技能概述", "education": "教育背景", "experience": "经验概述"},
    "target_state": {"position": "目标岗位", "company": "目标公司", "requirements": "岗位要求概述"},
    "gaps": [{"skill": "技能名", "current_level": "当前水平(1-5)", "target_level": "目标水平(1-5)", "gap": "差距描述"}],
    "milestones": [{"title": "里程碑标题", "description": "描述", "deadline": "截止日期(YYYY-MM-DD)", "skills": ["相关技能"], "status": "pending"}],
    "timeline_months": 6
  }
}"""


class CareerPlanningSkill(BaseSkill):
    """职业路径规划 Skill。"""

    code = "career_planning"
    name = "职业规划"
    description = "生成结构化职业发展路径，含目标、差距分析与里程碑"
    icon = "route"

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
            "你是 GradPath 职业规划专家，擅长为求职者制定个性化、可执行的职业发展路径规划。\n\n"
            "你的任务：基于用户的个人数据与知识库参考，生成结构化的职业规划，包括：\n"
            "1. 明确的职业目标\n"
            "2. 当前状态评估（技能/教育/经验）\n"
            "3. 目标状态分析（岗位/公司/要求）\n"
            "4. 能力差距分析（逐项列出技能差距与提升方案）\n"
            "5. 阶段性里程碑（含截止日期与相关技能）\n"
            "6. 时间线规划\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- gaps 与 milestones 至少各给 2 条\n"
            "- timeline_months 为整数\n"
            "- 所有内容使用中文\n"
            "- 结合用户画像给出个性化规划，避免泛泛而谈\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户规划请求】\n{message}\n\n请基于以上信息生成结构化的职业规划（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取 career_plan 数据。

        Expected output format:
        {content: str (markdown response), career_plan: {goal, current_state, target_state, gaps, milestones, timeline_months}}
        """
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))
        plan_raw = data.get("career_plan")

        career_plan = None
        if isinstance(plan_raw, dict):
            career_plan = _coerce_career_plan(plan_raw)

        return {"content": content, "career_plan": career_plan}


def _safe_parse_json(content: str) -> dict:
    """容错解析 LLM 返回的 JSON。"""
    # 1. 直接解析
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. 提取 markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # 3. 兜底：提取第一个 {...} 块
    brace_match = re.search(r"\{.*\}", content, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    # 4. 返回原始文本
    return {"content": content, "career_plan": None}


def _coerce_career_plan(raw: dict) -> dict:
    """将解析后的 career_plan dict 强制转换为标准结构，容忍字段缺失/类型错误。"""
    goal = str(raw.get("goal", ""))

    def _as_dict(v) -> dict:
        return v if isinstance(v, dict) else {}

    def _as_list(v) -> list:
        return v if isinstance(v, list) else []

    def _get_int(key: str, default: int = 6) -> int:
        v = raw.get(key, default)
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    return {
        "goal_text": goal,
        "current_state": _as_dict(raw.get("current_state")),
        "target_state": _as_dict(raw.get("target_state")),
        "gaps": _as_list(raw.get("gaps")),
        "milestones": _as_list(raw.get("milestones")),
        "timeline_months": _get_int("timeline_months", 6),
    }
