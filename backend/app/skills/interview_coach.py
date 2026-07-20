# backend/app/skills/interview_coach.py
"""面试教练 Skill — 提供面试技巧指导、常见问题解析、面试心态调整建议。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = [
    "面试技巧", "面试准备", "面试心态", "面试指导", "interview coach",
]

OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式面试技巧与心态调整总览",
  "interview_coach": {
    "tips": [{"category": "技巧类别", "tip": "具体建议", "why": "重要性说明"}],
    "common_questions": [{"question": "常见问题", "answer_strategy": "回答策略", "pitfall": "常见误区"}],
    "mindset": {"title": "心态调整要点", "suggestions": ["具体建议"], "exercises": ["心态练习"]},
    "preparation_checklist": [{"item": "准备事项", "priority": "high/medium/low", "description": "具体说明"}]
  }
}"""


class InterviewCoachSkill(BaseSkill):
    """面试教练 Skill。"""

    code = "interview_coach"
    name = "interview_coach"
    display_name = "面试教练"
    description = "提供面试技巧指导、常见问题解析、面试心态调整建议"
    icon = "message-circle"

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
            "你是 GradPath 面试教练，擅长帮助求职者提升面试技巧、准备面试内容、调整面试心态。\n\n"
            "你的任务：根据用户的目标岗位与个人背景，提供全面的面试指导，包括：\n"
            "1. 实用面试技巧（表达、肢体语言、时间管理等）\n"
            "2. 常见面试问题解析与回答策略\n"
            "3. 面试心态调整与压力管理建议\n"
            "4. 面试前准备清单\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- tips 至少给 5 条\n"
            "- common_questions 至少给 3 个常见问题\n"
            "- mindset 包含至少 3 条建议和 2 个练习\n"
            "- preparation_checklist 至少给 4 项\n"
            "- 所有内容使用中文\n"
            "- 结合用户画像给出个性化建议，避免泛泛而谈\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【面试教练咨询】\n{message}\n\n请提供全面的面试技巧指导与心态调整建议（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取 interview_coach 数据。"""
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))
        coach_raw = data.get("interview_coach")

        interview_coach = None
        if isinstance(coach_raw, dict):
            interview_coach = _coerce_coach(coach_raw)

        return {"content": content, "interview_coach": interview_coach}


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

    return {"content": content, "interview_coach": None}


def _coerce_coach(raw: dict) -> dict:
    """将解析后的 interview_coach dict 强制转换为标准结构。"""
    def _as_list(v) -> list:
        return v if isinstance(v, list) else []

    def _as_dict(v) -> dict:
        return v if isinstance(v, dict) else {}

    return {
        "tips": _as_list(raw.get("tips")),
        "common_questions": _as_list(raw.get("common_questions")),
        "mindset": _as_dict(raw.get("mindset")),
        "preparation_checklist": _as_list(raw.get("preparation_checklist")),
    }
