# backend/app/skills/resume_optimizer.py
"""简历优化器 Skill — 分析用户简历内容，提供优化建议和改进方案。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = ["简历优化", "简历分析", "优化简历", "简历检查", "resume"]

OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式优化报告总览",
  "suggestions": ["具体优化建议1", "具体优化建议2", "..."],
  "score": 75,
  "improved_sections": {"项目经历": "优化后的项目经历描述", "技能清单": "优化后的技能清单"}
}"""


class ResumeOptimizerSkill(BaseSkill):
    """简历优化器 Skill。"""

    code = "resume_optimizer"
    name = "resume_optimizer"
    description = "分析用户简历内容，提供优化建议和改进方案"
    icon = "file-text"

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
            "你是 GradPath 简历优化专家，精通互联网、金融等行业的简历优化。\n\n"
            "你的任务：分析用户提供的简历内容，结合其个人数据与目标岗位，提供"
            "专业、具体、可执行的优化方案。\n\n"
            "优化维度：\n"
            "1. 整体结构与排版规范\n"
            "2. 项目经验描述（STAR 法则、量化成果、关键词匹配）\n"
            "3. 技能清单与岗位匹配度\n"
            "4. 教育背景与经历呈现\n"
            "5. 语言表达与亮点突出\n"
            "6. ATS（自动筛选系统）友好度\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- suggestions 至少给 3 条具体可执行的优化建议\n"
            "- score 为 0-100 的简历质量评分\n"
            "- improved_sections 给出关键部分的优化后版本\n"
            "- 结合用户画像与目标岗位给出针对性建议\n"
            "- 所有内容使用中文\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户简历内容/请求】\n{message}\n\n请对简历进行优化分析（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取优化建议、评分和改进片段。

        Returns:
            {content, suggestions: list, score: int, improved_sections: dict, career_plan: None}
        """
        data = _safe_parse_json(llm_output)
        content = str(data.get("content", llm_output))
        suggestions_raw = data.get("suggestions", [])
        if not isinstance(suggestions_raw, list):
            suggestions_raw = []
        suggestions = [str(s) for s in suggestions_raw]
        score = data.get("score")
        if not isinstance(score, int):
            score = None
        improved_sections = data.get("improved_sections", {})
        if not isinstance(improved_sections, dict):
            improved_sections = {}
        return {
            "content": content,
            "suggestions": suggestions,
            "score": score,
            "improved_sections": improved_sections,
            "career_plan": None,
        }


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

    return {"content": content, "suggestions": []}
