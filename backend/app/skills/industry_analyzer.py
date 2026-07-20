# backend/app/skills/industry_analyzer.py
"""行业分析器 Skill — 分析目标行业的趋势和机会。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = [
    "行业分析", "行业趋势", "行业前景", "industry",
    "行业分析器", "行业动态", "行业发展", "行业机会",
]

OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含行业分析总览与建议",
  "industry_analysis": {
    "industry_name": "目标行业名称",
    "market_size": "市场规模概述",
    "growth_trend": "增长趋势（如：快速增长/稳定增长/放缓/下行）",
    "key_drivers": ["驱动因素1", "驱动因素2"],
    "opportunities": ["机会1", "机会2"],
    "challenges": ["挑战1", "挑战2"],
    "salary_range": "薪资范围概述",
    "entry_barrier": "进入门槛（高/中/低）",
    "recommendation": "针对用户背景的个性化建议"
  }
}"""


class IndustryAnalyzerSkill(BaseSkill):
    """行业分析器 Skill。"""

    code = "industry_analyzer"
    name = "industry_analyzer"
    description = "分析目标行业的趋势和机会，帮助用户做出职业决策"
    icon = "bar-chart"

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
            "你是 GradPath 行业分析专家，擅长深入分析各行业的发展趋势、市场机会与挑战。\n\n"
            "你的任务：基于用户的个人数据与知识库参考，为目标行业提供全面分析，包括：\n"
            "1. 市场规模与增长趋势\n"
            "2. 关键驱动因素\n"
            "3. 行业机会与挑战\n"
            "4. 薪资水平与进入门槛\n"
            "5. 针对用户背景的个性化建议\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- key_drivers、opportunities、challenges 至少各给 2 条\n"
            "- 所有内容使用中文\n"
            "- 结合用户画像给出个性化分析，避免泛泛而谈\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户行业分析请求】\n{message}\n\n请基于以上信息生成行业分析报告（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取 industry_analysis 数据。"""
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))
        analysis_raw = data.get("industry_analysis")

        industry_analysis = None
        if isinstance(analysis_raw, dict):
            industry_analysis = _coerce_industry_analysis(analysis_raw)

        return {"content": content, "industry_analysis": industry_analysis, "career_plan": None}


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

    return {"content": content, "industry_analysis": None}


def _coerce_industry_analysis(raw: dict) -> dict:
    """将解析后的 industry_analysis dict 强制转换为标准结构。"""
    def _as_list(v) -> list:
        return v if isinstance(v, list) else []

    return {
        "industry_name": str(raw.get("industry_name", "")),
        "market_size": str(raw.get("market_size", "")),
        "growth_trend": str(raw.get("growth_trend", "")),
        "key_drivers": _as_list(raw.get("key_drivers")),
        "opportunities": _as_list(raw.get("opportunities")),
        "challenges": _as_list(raw.get("challenges")),
        "salary_range": str(raw.get("salary_range", "")),
        "entry_barrier": str(raw.get("entry_barrier", "")),
        "recommendation": str(raw.get("recommendation", "")),
    }
