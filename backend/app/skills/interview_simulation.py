# backend/app/skills/interview_simulation.py
"""面试模拟 Skill — 模拟面试问答，支持多轮对话。"""
from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = ["面试", "面经", "模拟面试", "interview", "面试题", "面试准备"]

OUTPUT_FORMAT = """\
请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "content": "给用户的 Markdown 格式面试指导总览",
  "questions": ["面试题1（含参考思路）", "面试题2（含参考思路）", "..."],
  "feedback": "对用户上一轮回答的评分和建议（如果是多轮对话）",
  "score": 85,
  "round": 1
}"""


class InterviewSimulationSkill(BaseSkill):
    """面试模拟 Skill，支持多轮对话。"""

    code = "interview_simulation"
    name = "面试模拟"
    description = "模拟面试场景，生成针对性面试题与答题思路，支持多轮面试模拟"
    icon = "mic"

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
            "你是 GradPath 面试模拟官，熟悉互联网、金融等行业的面试流程与考察重点。\n\n"
            "你的任务：根据用户的目标岗位与个人背景，模拟面试场景，生成针对性的面试题与"
            "答题思路指导。\n\n"
            "考察维度：\n"
            "1. 算法与数据结构\n"
            "2. 计算机基础（网络/操作系统/数据库）\n"
            "3. 项目经验深挖\n"
            "4. 系统设计\n"
            "5. 行为面试（STAR 法则）\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- questions 至少给 3 道题，每题含参考答题思路\n"
            "- 结合用户画像与目标岗位定制题目难度与方向\n"
            "- 所有内容使用中文\n"
            "- feedback 字段：如果是多轮对话，对用户上一轮回答给出评分(0-100)和改进建议\n"
            "- score 字段：对用户上一轮回答的评分(0-100)，首轮为0\n"
            "- round 字段：当前是第几轮面试（从1开始）\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户面试模拟请求】\n{message}\n\n请生成针对性的面试题与答题思路（严格按 JSON 格式输出）。"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出，支持多轮对话状态。

        Returns:
            {content, questions, feedback, score, round, career_plan}
        """
        data = _safe_parse_json(llm_output)
        content = str(data.get("content", llm_output))
        questions_raw = data.get("questions", [])
        if not isinstance(questions_raw, list):
            questions_raw = []
        questions = [str(q) for q in questions_raw]
        feedback = str(data.get("feedback", ""))
        score = int(data.get("score", 0))
        round_num = int(data.get("round", 1))
        return {
            "content": content,
            "questions": questions,
            "feedback": feedback,
            "score": score,
            "round": round_num,
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

    return {"content": content, "questions": []}
