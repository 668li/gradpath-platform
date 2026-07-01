# backend/app/skills/default_skill.py
"""默认通用职业咨询 Skill — 始终激活作为兜底。"""
from app.skills.base import BaseSkill


class DefaultSkill(BaseSkill):
    """通用职业咨询兜底 Skill。"""

    code = "default"
    name = "职业咨询"
    description = "通用职业规划咨询，回答各类职业发展问题"
    icon = "chat"

    def should_activate(self, message: str, context: dict) -> bool:
        """兜底 Skill，始终激活。"""
        return True

    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        knowledge_block = ""
        if knowledge:
            lines = ["【相关知识库参考】"]
            for k in knowledge:
                lines.append(f"- 《{k.get('title', '')}》[{k.get('category', '')}]")
                # 摘要前 200 字
                content = (k.get("content") or "")[:200]
                if content:
                    lines.append(f"  摘要：{content}")
            knowledge_block = "\n".join(lines) + "\n\n"

        return (
            "你是 GradPath 职业规划管家，一位资深的中国职场职业发展顾问，精通互联网、金融、"
            "通信、制造、国企等行业的求职与发展路径。\n\n"
            "你的任务：根据用户的个人数据（用户画像）与知识库参考，提供专业、个性化、可执行"
            "的职业建议。回答需结合用户实际情况，避免泛泛而谈。\n\n"
            "回答要求：\n"
            "1. 使用中文，语气专业且亲切。\n"
            "2. 结构清晰，必要时使用 Markdown 标题与列表。\n"
            "3. 结合用户画像给出针对性建议。\n"
            "4. 若引用知识库内容，自然融入而非生硬罗列。\n\n"
            f"{user_context}\n{knowledge_block}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户问题】\n{message}"
