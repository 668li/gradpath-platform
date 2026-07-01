# backend/app/skills/grad_school_planning.py
"""考研规划 Skill — 生成结构化考研备考规划。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

# 激活关键词
ACTIVATE_KEYWORDS = [
    "考研", "保研", "研究生", "读研", "学硕", "专硕", "硕士",
]

# 期望的 LLM JSON 输出格式说明
OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含考研规划总览与建议",
  "target_schools": ["目标院校1", "目标院校2"],
  "target_major": "目标专业方向",
  "exam_subjects": ["考试科目1", "考试科目2"],
  "timeline": "备考时间线概述（基础/强化/冲刺阶段）",
  "prep_strategy": "备考策略概述"
}"""


class GradSchoolPlanningSkill(BaseSkill):
    """考研规划 Skill。"""

    code = "grad_school_planning"
    name = "考研规划"
    description = "考研院校选择、专业方向、备考时间线规划"
    icon = "🎓"

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
            "你是 GradPath 考研规划专家，擅长为考生制定个性化、可执行的考研备考规划。\n\n"
            "你的任务：基于用户的个人数据与知识库参考，生成结构化的考研规划，聚焦：\n"
            "1. 院校梯队分析（冲稳保策略，结合本科背景与目标方向）\n"
            "2. 考试科目与参考书目（统考科目与自命题科目）\n"
            "3. 历年分数线与录取情况（国家线/院线/复试线）\n"
            "4. 备考时间线与阶段策略（基础/强化/冲刺/模拟）\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- target_schools 至少给 2 所院校，按梯队划分\n"
            "- exam_subjects 列出全部统考与自命题科目\n"
            "- timeline 按阶段规划，标注关键节点\n"
            "- prep_strategy 结合用户基础给出针对性策略\n"
            "- 所有内容使用中文\n"
            "- 结合用户画像给出个性化规划，避免泛泛而谈\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户考研规划请求】\n{message}\n\n请基于以上信息生成结构化的考研规划（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取考研规划数据。

        尝试从 LLM 回复提取 JSON（target_schools, target_major, exam_subjects,
        timeline, prep_strategy），失败返回原始内容。

        Returns:
            {content, target_schools, target_major, exam_subjects, timeline,
             prep_strategy, career_plan: None}
        """
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))

        return {
            "content": content,
            "target_schools": _as_list(data.get("target_schools")),
            "target_major": _as_str(data.get("target_major")),
            "exam_subjects": _as_list(data.get("exam_subjects")),
            "timeline": _as_str(data.get("timeline")),
            "prep_strategy": _as_str(data.get("prep_strategy")),
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
