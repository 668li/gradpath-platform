# backend/app/skills/salary_benchmark.py
"""薪资基准分析 Skill — 分析用户薪资数据，生成行业/岗位/地区的薪资基准报告。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = [
    "薪资基准", "薪资报告", "工资水平", "salary benchmark", "薪资分析",
]

OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式回复，包含薪资基准分析报告",
  "salary_benchmark": {
    "summary": "整体薪资概览",
    "industry": "目标行业",
    "position": "目标岗位",
    "region": "目标地区",
    "salary_distribution": {"min": 0, "max": 0, "median": 0, "p25": 0, "p75": 0, "currency": "CNY", "sample_size": 0},
    "factors": [{"factor": "影响因素", "impact": "高/中/低", "description": "说明"}],
    "trends": {"direction": "上涨/持平/下降", "annual_growth": "百分比", "forecast": "未来趋势说明"},
    "comparisons": [{"name": "对比维度", "value": "对比值", "benchmark": "基准值"}],
    "recommendations": [{"title": "建议标题", "detail": "详细说明", "priority": "high/medium/low"}]
  }
}"""


class SalaryBenchmarkSkill(BaseSkill):
    """薪资基准分析 Skill。"""

    code = "salary_benchmark"
    name = "salary_benchmark"
    display_name = "薪资基准分析"
    description = "分析用户薪资数据，生成行业/岗位/地区的薪资基准报告"
    icon = "trending-up"

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
            "你是 GradPath 薪资基准分析专家，擅长根据用户提供的薪资数据生成行业/岗位/地区的薪资基准报告。\n\n"
            "你的任务：基于用户提供的薪资数据与知识库参考，生成结构化的薪资基准分析报告，包括：\n"
            "1. 整体薪资概览\n"
            "2. 薪资分布统计（最小值、最大值、中位数、P25、P75）\n"
            "3. 影响薪资的关键因素\n"
            "4. 薪资趋势分析\n"
            "5. 多维度薪资对比\n"
            "6. 个性化薪资建议\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- factors 至少给 3 条\n"
            "- comparisons 至少给 2 条\n"
            "- recommendations 至少给 3 条\n"
            "- 所有内容使用中文\n"
            "- 结合用户画像给出个性化建议，避免泛泛而谈\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【薪资基准分析】\n{message}\n\n请基于以上信息生成结构化的薪资基准分析报告（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，提取 salary_benchmark 数据。"""
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))
        bench_raw = data.get("salary_benchmark")

        salary_benchmark = None
        if isinstance(bench_raw, dict):
            salary_benchmark = _coerce_benchmark(bench_raw)

        return {"content": content, "salary_benchmark": salary_benchmark}


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

    return {"content": content, "salary_benchmark": None}


def _coerce_benchmark(raw: dict) -> dict:
    """将解析后的 salary_benchmark dict 强制转换为标准结构。"""
    def _as_dict(v) -> dict:
        return v if isinstance(v, dict) else {}

    def _as_list(v) -> list:
        return v if isinstance(v, list) else []

    return {
        "summary": str(raw.get("summary", "")),
        "industry": str(raw.get("industry", "")),
        "position": str(raw.get("position", "")),
        "region": str(raw.get("region", "")),
        "salary_distribution": _as_dict(raw.get("salary_distribution")),
        "factors": _as_list(raw.get("factors")),
        "trends": _as_dict(raw.get("trends")),
        "comparisons": _as_list(raw.get("comparisons")),
        "recommendations": _as_list(raw.get("recommendations")),
    }
