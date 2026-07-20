# backend/app/skills/salary_negotiation.py
"""薪资谈判助手 Skill — 帮助用户准备薪资谈判策略。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

# 激活关键词
ACTIVATE_KEYWORDS = [
    "薪资谈判", "谈薪", "工资谈判", "薪资", "salary", "negotiation",
]

# 期望的 LLM JSON 输出格式说明
OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含谈判策略与建议",
  "salary_negotiation": {
    "position_info": {"title": "职位名称", "company": "目标公司", "industry": "行业", "location": "工作地点"},
    "market_salary": {"min": 0, "max": 0, "median": 0, "currency": "CNY", "source": "参考来源说明"},
    "negotiation_points": [{"point": "谈判要点", "argument": "支撑论据", "expected_impact": "预期效果(high/medium/low)"}],
    "strategy": {"approach": "整体策略描述", "opening_move": "开场报价建议", "walk_away_point": "底线薪资", "non_salary_benefits": ["可争取的非薪资福利"]},
    "timeline": [{"step": "步骤", "description": "描述", "timing": "时间节点"}],
    "risk_assessment": {"risks": ["风险点"], "mitigation": ["应对措施"]}
  }
}"""


class SalaryNegotiationSkill(BaseSkill):
    """薪资谈判助手 Skill。"""

    code = "salary_negotiation"
    name = "salary_negotiation"
    display_name = "薪资谈判助手"
    description = "帮助用户准备薪资谈判策略，分析市场行情，制定谈判方案"
    icon = "dollar-sign"

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
            "你是 GradPath 薪资谈判专家，擅长帮助求职者制定科学、有效的薪资谈判策略。\n\n"
            "你的任务：基于用户提供的职位信息与知识库参考，生成结构化的薪资谈判方案，包括：\n"
            "1. 市场薪资行情分析\n"
            "2. 可用谈判要点及支撑论据\n"
            "3. 整体谈判策略（含开场报价和底线）\n"
            "4. 分阶段谈判时间线\n"
            "5. 风险评估与应对措施\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- negotiation_points 至少给 3 条\n"
            "- non_salary_benefits 至少列 3 项\n"
            "- 所有内容使用中文\n"
            "- 结合用户画像给出个性化建议，避免泛泛而谈\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【薪资谈判咨询】\n{message}\n\n请基于以上信息生成结构化的薪资谈判方案（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取 salary_negotiation 数据。"""
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))
        neg_raw = data.get("salary_negotiation")

        salary_negotiation = None
        if isinstance(neg_raw, dict):
            salary_negotiation = _coerce_negotiation(neg_raw)

        return {"content": content, "salary_negotiation": salary_negotiation}


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

    return {"content": content, "salary_negotiation": None}


def _coerce_negotiation(raw: dict) -> dict:
    """将解析后的 salary_negotiation dict 强制转换为标准结构。"""
    def _as_dict(v) -> dict:
        return v if isinstance(v, dict) else {}

    def _as_list(v) -> list:
        return v if isinstance(v, list) else []

    return {
        "position_info": _as_dict(raw.get("position_info")),
        "market_salary": _as_dict(raw.get("market_salary")),
        "negotiation_points": _as_list(raw.get("negotiation_points")),
        "strategy": _as_dict(raw.get("strategy")),
        "timeline": _as_list(raw.get("timeline")),
        "risk_assessment": _as_dict(raw.get("risk_assessment")),
    }
