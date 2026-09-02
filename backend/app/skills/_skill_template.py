# backend/app/skills/_skill_template.py
"""【新 Skill 模板】— 复制本文件并按下方注释改成你自己的数据型 Skill。

本轮只建框架，不编 skill 内容。你后续指定的 skill 内容直接套本模板零摩擦上线。

本模板演示的是"数据型 Skill"蓝图：它覆写 inject_data 钩子，拉取 GradPath 专有数据
（进面线 / 条件账本 / 测评 / 专业前景）追加进 system prompt，成为别人给不了的差异化能力。
如果只是通用 coach skill（不需要专有数据），可省略 inject_data，让基类默认返回空串。

注册（三处，缺一不可）见 docs/skill-registration-checklist.md：
  1. 本文件里的 SkillInfo 元信息加进 registry._SKILLS
  2. 类加入 registry._load_skill_classes 的 import 与 _SKILL_CLASSES 注册表
  3. （可选）若希望用户在 AI 下拉里直接看到，确保 _SKILLS 里 is_active=True
"""

from __future__ import annotations

from app.skills.base import BaseSkill

# 建议把触发词集中在 ACTIVATE_KEYWORDS，注册表 _SKILLS.trigger_words 与其保持一致
ACTIVATE_KEYWORDS = [
    # TODO(你): 填你的 skill 触发词，如 "查进面线", "我这个专业前景", "能报什么岗"
    "示例触发词A",
    "示例触发词B",
]

# 情景组归属（Phase C1）：如果想被"选岗/查线/升学"等模糊场景命中，把本 skill 的 code
# 加进 registry._SCENARIOS 里对应 scenarios 的 "skills" 列表。不加则只能精确触发词命中。
SCENARIO_BELONGING = ["scoreline", "choice"]  # TODO(你): 从 _SCENARIOS 的 id 里挑，或留空 []


class YourSkillNameSkill(BaseSkill):
    """TODO(你): 描述你的 skill。"""

    # code 必须是唯一标识，且与注册表 _SKILL_CLASSES[cls.code] 的键一致（通常小写下划线）
    code = "your_skill_name"
    name = "your_skill_name"  # 通常与 code 相同（_load_skill_classes 按 name 匹配）
    description = "TODO(你): 一句话说明这个 skill 帮用户解决什么问题"
    icon = "sparkles"  # 可选 lucide 图标名
    # 结构化输出模板（可选）：让 LLM 返回可被 parse_response 解析的 JSON。
    # 参考 industry_analyzer.py 的 OUTPUT_FORMAT；不需要结构化时可删除。
    OUTPUT_FORMAT = "请输出 JSON 结构（参考 industry_analyzer.py 的写法）。"

    def should_activate(self, message: str, context: dict) -> bool:
        """判断是否激活此 skill。返回 True 即命中也参与 registry 精确触发词打分。"""
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in ACTIVATE_KEYWORDS)

    def inject_data(self, db, user_id, content: str) -> str:
        """数据注入钩子（Phase C2）：拉取专有数据拼成一段追加到 system prompt。

        Args:
            db: SQLAlchemy Session
            user_id: 当前用户 id
            content: 用户本次消息原文（可按需筛选数据，避免每次都全量查）

        Returns:
            一段可直接追加到 system prompt 的文本；无需数据时返回 ""。
        """
        # 示例：读用户测评 → 条件账本 → 进面线。全部使用真实专有数据，绝不编造。
        # from app.models.assessment import Assessment
        # latest = db.query(Assessment).filter(Assessment.user_id == user_id)\
        #     .order_by(Assessment.created_at.desc()).first()
        # if latest is None:
        #     return "（用户尚未完成测评，暂无专有数据）"
        # return f"用户测评类型：{latest.type}，编码：{latest.result_code or '无'}"
        return ""

    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        """构建 system prompt。inject_data 的结果由 chat_service 在 build 之后自动追加。"""
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
            "你是 GradPath 的 XXX 专家。\n\n"
            "你的任务：…（TODO(你) 写清楚职责与边界，避免泛泛而谈）\n\n"
            # 结构化输出模板（可选）：让 LLM 返回可被 parse_response 解析的 JSON
            f"{self.OUTPUT_FORMAT}\n\n"
            "注意事项：\n"
            "- 只用中文\n"
            "- 结合用户画像给出个性化建议，绝不编造没有数据支撑的结论\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户请求】\n{message}\n\n请按上述要求处理。\n"

    def parse_response(self, llm_output: str) -> dict:
        """解析 LLM 输出。默认返回原始文本；需要结构化字段时参考 industry_analyzer.py 的
        _safe_parse_json + _coerce_xxx 写法（容错 JSON + 强制结构兜底）。"""
        return {"content": llm_output, "career_plan": None}
