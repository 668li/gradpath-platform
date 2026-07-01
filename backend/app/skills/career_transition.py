# backend/app/skills/career_transition.py
"""职业转型 Skill — 跨行业/跨岗位转型可行性分析与路径规划。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

# 激活关键词
ACTIVATE_KEYWORDS = [
    "转行", "转型", "跨行", "换赛道", "跨岗位",
]

# 期望的 LLM JSON 输出格式说明
OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含转型可行性分析与路径建议",
  "current_field": "当前所在行业/岗位",
  "target_field": "目标行业/岗位",
  "transferable_skills": ["可迁移技能1", "可迁移技能2"],
  "gaps": ["能力差距1", "能力差距2"],
  "transition_steps": ["转型步骤1", "转型步骤2"]
}"""


class CareerTransitionSkill(BaseSkill):
    """职业转型 Skill。"""

    code = "career_transition"
    name = "职业转型"
    description = "跨行业/跨岗位转型可行性分析与路径规划"
    icon = "🔄"

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
            "你是 GradPath 职业转型顾问，擅长评估跨行业/跨岗位转型的可行性并规划落地路径。\n\n"
            "你的任务：基于用户的个人数据与知识库参考，分析转型可行性，包括：\n"
            "1. 当前行业/岗位与目标行业/岗位的对比\n"
            "2. 可迁移技能识别（哪些能力可以直接复用）\n"
            "3. 能力差距分析（需要补齐的技能与经验）\n"
            "4. 分阶段转型路径（短期准备、中期过渡、长期立足）\n"
            "5. 风险提示与备选方案\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- transferable_skills 至少给 2 项可迁移技能\n"
            "- gaps 客观评估能力差距，给出补齐建议\n"
            "- transition_steps 至少给 3 步，按时间顺序排列\n"
            "- 结合用户画像给出个性化建议，避免泛泛而谈\n"
            "- 所有内容使用中文\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户职业转型请求】\n{message}\n\n请基于以上信息分析转型可行性并规划路径（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取职业转型分析数据。

        尝试从 LLM 回复提取 JSON（current_field, target_field, transferable_skills,
        gaps, transition_steps），失败返回原始内容。

        Returns:
            {content, current_field, target_field, transferable_skills, gaps,
             transition_steps, career_plan: None}
        """
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))

        return {
            "content": content,
            "current_field": _as_str(data.get("current_field")),
            "target_field": _as_str(data.get("target_field")),
            "transferable_skills": _as_list(data.get("transferable_skills")),
            "gaps": _as_list(data.get("gaps")),
            "transition_steps": _as_list(data.get("transition_steps")),
            "career_plan": None,
        }


def _as_list(v) -> list:
    if not isinstance(v, list):
        return []
    return [str(x) for x in v]


def _as_str(v) -> str:
    if v is None:
        return ""
    return str(v)


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
    return {"content": content}
