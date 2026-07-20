# backend/app/skills/company_review.py
"""公司评价分析 Skill — 分析用户对公司的评价，提取关键信息，帮助其他用户了解公司真实情况。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = [
    "公司评价", "公司口碑", "公司怎么样", "company review",
    "工作体验", "公司评价分析", "公司测评", "工作环境评价",
]

OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含公司评价分析总览",
  "company_review": {
    "company_name": "公司名称",
    "overall_rating": "综合评分（1-10）",
    "work_culture": "工作文化评价",
    "work_life_balance": "工作生活平衡评价",
    "compensation": "薪资福利评价",
    "management": "管理风格评价",
    "growth_opportunity": "成长机会评价",
    "strengths": ["优势1", "优势2"],
    "concerns": ["顾虑1", "顾虑2"],
    "target_candidates": "适合什么样的求职者",
    "summary": "一句话总结"
  }
}"""


class CompanyReviewSkill(BaseSkill):
    """公司评价分析 Skill。"""

    code = "company_review"
    name = "company_review"
    description = "分析用户对公司的评价，提取关键信息，帮助其他用户了解公司真实情况"
    icon = "building"

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
            "你是 GradPath 公司评价分析专家，擅长从用户描述中提取公司关键信息，帮助求职者了解公司真实情况。\n\n"
            "你的任务：基于用户的公司评价描述和知识库参考，生成结构化的公司评价分析，包括：\n"
            "1. 工作文化评价\n"
            "2. 工作生活平衡评价\n"
            "3. 薪资福利评价\n"
            "4. 管理风格评价\n"
            "5. 成长机会评价\n"
            "6. 优势与顾虑分析\n"
            "7. 适合的求职者画像\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- strengths、concerns 至少各给 2 条\n"
            "- 所有内容使用中文\n"
            "- 客观公正地分析，既指出优点也指出不足\n"
            "- 结合用户描述给出个性化分析，避免泛泛而谈\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户公司评价请求】\n{message}\n\n请基于以上信息生成公司评价分析报告（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取 company_review 数据。"""
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))
        review_raw = data.get("company_review")

        company_review = None
        if isinstance(review_raw, dict):
            company_review = _coerce_company_review(review_raw)

        return {"content": content, "company_review": company_review, "career_plan": None}


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

    return {"content": content, "company_review": None}


def _coerce_company_review(raw: dict) -> dict:
    """将解析后的 company_review dict 强制转换为标准结构。"""
    def _as_list(v) -> list:
        return v if isinstance(v, list) else []

    return {
        "company_name": str(raw.get("company_name", "")),
        "overall_rating": str(raw.get("overall_rating", "")),
        "work_culture": str(raw.get("work_culture", "")),
        "work_life_balance": str(raw.get("work_life_balance", "")),
        "compensation": str(raw.get("compensation", "")),
        "management": str(raw.get("management", "")),
        "growth_opportunity": str(raw.get("growth_opportunity", "")),
        "strengths": _as_list(raw.get("strengths")),
        "concerns": _as_list(raw.get("concerns")),
        "target_candidates": str(raw.get("target_candidates", "")),
        "summary": str(raw.get("summary", "")),
    }
