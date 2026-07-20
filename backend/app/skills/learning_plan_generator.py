# backend/app/skills/learning_plan_generator.py
"""学习计划生成器 Skill — 根据用户目标生成详细的学习计划和时间表。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

# 激活关键词
ACTIVATE_KEYWORDS = [
    "学习计划", "制定计划", "学习安排", "备考计划",
]

# 期望的 LLM JSON 输出格式说明
OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含学习计划总览与建议",
  "total_weeks": 12,
  "phases": [
    {
      "name": "阶段名称",
      "weeks": "1-4",
      "goals": ["目标1", "目标2"],
      "tasks": ["具体任务1", "具体任务2"],
      "daily_hours": 3
    }
  ],
  "milestones": ["里程碑1", "里程碑2"],
  "resources": ["推荐资源1", "推荐资源2"]
}"""


class LearningPlanGeneratorSkill(BaseSkill):
    """学习计划生成器 Skill。"""

    code = "learning_plan_generator"
    name = "learning_plan_generator"
    description = "根据用户目标生成详细的学习计划和时间表"
    icon = "calendar"

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
            "你是 GradPath 学习计划生成专家，擅长根据用户的学习目标、时间约束和现有基础，"
            "制定详细、可执行的学习计划。\n\n"
            "你的任务：基于用户的个人数据与知识库参考，生成结构化的学习计划，聚焦：\n"
            "1. 阶段划分（基础/强化/冲刺等阶段，明确每阶段时间跨度）\n"
            "2. 每阶段具体目标与每日学习时长\n"
            "3. 里程碑节点（阶段性检验点）\n"
            "4. 推荐学习资源与方法\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- phases 至少包含 3 个阶段，覆盖完整学习周期\n"
            "- 每阶段的 tasks 要具体可执行，避免笼统\n"
            "- milestones 标注关键检验节点\n"
            "- resources 根据用户学习目标推荐具体资源\n"
            "- 所有内容使用中文\n"
            "- 结合用户画像给出个性化计划，避免泛泛而谈\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户学习计划请求】\n{message}\n\n请基于以上信息生成详细的学习计划（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取学习计划数据。

        尝试从 LLM 回复提取 JSON（total_weeks, phases, milestones, resources），
        失败返回原始内容。

        Returns:
            {content, total_weeks, phases, milestones, resources, career_plan: None}
        """
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))

        return {
            "content": content,
            "total_weeks": _as_int(data.get("total_weeks")),
            "phases": _as_list(data.get("phases")),
            "milestones": _as_list(data.get("milestones")),
            "resources": _as_list(data.get("resources")),
            "career_plan": None,
        }


def _as_list(v) -> list:
    if not isinstance(v, list):
        return []
    return [str(x) if not isinstance(x, dict) else x for x in v]


def _as_int(v) -> int:
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


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
