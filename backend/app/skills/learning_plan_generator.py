# backend/app/skills/learning_plan_generator.py
"""学习计划生成器 Skill — 根据用户目标生成详细的学习计划和时间表。

V2（2026-09-05）：新增 micro_action_plan 落库通道——LLM 在总计划之外
额外产出"未来 7 天每天一个具体行动"，经 _validate_micro_action_plan
校验后由 chat_service 落库到 micro-actions（连击/D2 提醒闭环）。
校验不过则诚实降级为纯对话回复，绝不落半成品计划。
"""

from __future__ import annotations

import json
import re

from app.skills.base import BaseSkill

# 激活关键词
ACTIVATE_KEYWORDS = [
    "学习计划",
    "制定计划",
    "学习安排",
    "备考计划",
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
  "resources": ["推荐资源1", "推荐资源2"],
  "micro_action_plan": {
    "target_path": "kaoyan",
    "target_role": "目标一句话，如：三个月内完成计算机考研基础轮",
    "tasks": [
      {
        "day_number": 1,
        "task_type": "research",
        "title": "今天要做的具体行动（30 字内）",
        "description": "怎么做、做到什么程度算完成（50 字内）",
        "estimated_minutes": 30
      }
    ]
  }
}"""

VALID_TARGET_PATHS = ("kaoyan", "employment", "civil_service")
VALID_TASK_TYPES = ("research", "interview", "practice", "reflect")


class LearningPlanGeneratorSkill(BaseSkill):
    """学习计划生成器 Skill。"""

    code = "learning_plan_generator"
    name = "learning_plan_generator"
    description = "根据用户目标生成详细的学习计划、时间表和未来 7 天行动清单"
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
            "4. 推荐学习资源与方法\n"
            "5. 未来 7 天行动清单（micro_action_plan，会直接落库为用户的每日任务）\n\n"
            f"{OUTPUT_FORMAT}\n\n"
            "micro_action_plan 硬性规则：\n"
            "- tasks 给未来 7 天，day_number 从 1 连续编号到 7，每天 1 个任务\n"
            "- 每个任务必须小到 20-60 分钟能完成，title 是动词开头的具体行动，不写「学习 XX」这类笼统词\n"
            "- target_path 只能取 kaoyan（考研）/ employment（就业）/ civil_service（考公）之一，"
            "依据用户上下文判断；判断不了用 employment\n"
            "- task_type 只能取 research（搜集信息）/ practice（动手练习）/ interview（模拟面试/提问）/"
            " reflect（复盘反思）之一\n"
            "- 生成失败或信息不足时宁缺毋滥：整个 micro_action_plan 字段留空，不要编造任务\n\n"
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
        """解析 LLM 输出，提取学习计划与 7 天微行动计划。

        Returns:
            {content, total_weeks, phases, milestones, resources,
             micro_action_plan: 校验通过的落库载荷或 None, career_plan: None}
        """
        data = _safe_parse_json(llm_output)

        content = str(data.get("content", llm_output))

        return {
            "content": content,
            "total_weeks": _as_int(data.get("total_weeks")),
            "phases": _as_list(data.get("phases")),
            "milestones": _as_list(data.get("milestones")),
            "resources": _as_list(data.get("resources")),
            "micro_action_plan": _validate_micro_action_plan(data),
            "career_plan": None,
        }


def _validate_micro_action_plan(data: dict) -> dict | None:
    """校验 LLM 产出的微行动计划；不合格返回 None（诚实降级为纯对话回复）。"""
    raw = data.get("micro_action_plan")
    if not isinstance(raw, dict):
        return None
    tasks_raw = raw.get("tasks")
    if not isinstance(tasks_raw, list):
        return None

    target_path = str(raw.get("target_path") or "employment").strip()
    if target_path not in VALID_TARGET_PATHS:
        target_path = "employment"

    tasks: list[dict] = []
    for t in tasks_raw:
        if not isinstance(t, dict):
            continue
        title = str(t.get("title") or "").strip()
        desc = str(t.get("description") or "").strip()
        if not title or not desc:
            continue
        try:
            day = int(t.get("day_number"))
        except (TypeError, ValueError):
            continue
        day = min(max(day, 1), 7)
        task_type = str(t.get("task_type") or "practice").strip()
        if task_type not in VALID_TASK_TYPES:
            task_type = "practice"
        try:
            minutes = int(t.get("estimated_minutes") or 20)
        except (TypeError, ValueError):
            minutes = 20
        minutes = min(max(minutes, 5), 180)
        tasks.append(
            {
                "day_number": day,
                "task_type": task_type,
                "title": title[:200],
                "description": desc,
                "estimated_minutes": minutes,
            }
        )

    # 每天最多 1 个任务（day_number 去重保首个），少于 3 个有效任务不落库
    seen_days: set[int] = set()
    deduped: list[dict] = []
    for t in tasks:
        if t["day_number"] in seen_days:
            continue
        seen_days.add(t["day_number"])
        deduped.append(t)
    if len(deduped) < 3:
        return None

    return {
        "target_path": target_path,
        "target_role": str(raw.get("target_role") or "")[:100] or None,
        "tasks": deduped,
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
