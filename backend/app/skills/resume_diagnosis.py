# backend/app/skills/resume_diagnosis.py
"""简历诊断 Skill — 分析简历并给出修改建议。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = ["简历", "CV", "修改简历", "resume", "简历修改", "简历诊断"]

OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式诊断报告总览",
  "suggestions": ["具体修改建议1", "具体修改建议2", "..."]
}"""


class ResumeDiagnosisSkill(BaseSkill):
    """简历诊断 Skill。"""

    code = "resume_diagnosis"
    name = "简历诊断"
    description = "分析简历内容，给出针对性的修改建议"
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
            "你是 GradPath 简历诊断专家，精通互联网、金融等行业的简历优化。\n\n"
            "你的任务：分析用户提供的简历内容或描述，结合其个人数据与岗位要求，给出专业、"
            "具体的修改建议。\n\n"
            "诊断维度：\n"
            "1. 整体结构与排版\n"
            "2. 项目经验描述（STAR 法则、量化成果）\n"
            "3. 技能匹配度（与目标岗位）\n"
            "4. 教育与经历呈现\n"
            "5. 语言表达与亮点突出\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- suggestions 至少给 3 条具体可执行的建议\n"
            "- 结合用户画像与目标岗位给出针对性建议\n"
            "- 所有内容使用中文\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户简历内容/请求】\n{message}\n\n请给出简历诊断与修改建议（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取 suggestions 列表。

        Returns:
            {content, suggestions: list, career_plan: None}
        """
        data = _safe_parse_json(llm_output)
        content = str(data.get("content", llm_output))
        suggestions_raw = data.get("suggestions", [])
        if not isinstance(suggestions_raw, list):
            suggestions_raw = []
        suggestions = [str(s) for s in suggestions_raw]
        return {"content": content, "suggestions": suggestions, "career_plan": None}


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
