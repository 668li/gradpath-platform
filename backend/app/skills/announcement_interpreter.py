# backend/app/skills/announcement_interpreter.py
"""公告解读器 Skill — 把站内官方公告翻译成「对用户意味着什么 + 行动项」。

数据面：kaoyan_news 正式表（source_platform=official，审核后），
暂存表 t_external_research_item（APPROVED）兜底；全部带来源 URL。
公告没提的不猜，与用户无关的如实说无关——信息差翻译器，不是编造器。
"""

from __future__ import annotations

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = [
    "公告", "简章", "招生简章", "调剂公告", "招考通知", "招生信息",
]


class AnnouncementInterpreterSkill(BaseSkill):
    """公告解读器 Skill。"""

    code = "announcement_interpreter"
    name = "announcement_interpreter"
    description = "解读站内官方公告：对你的影响、关键日期、本周行动项，带原文来源"
    icon = "megaphone"
    # announcements 域由本 skill 的 inject_data 负责，chat 通用搜索层跳过
    covered_data_domains = frozenset({"announcements"})

    def should_activate(self, message: str, context: dict) -> bool:
        msg = (message or "").lower()
        return any(kw in msg for kw in ACTIVATE_KEYWORDS)

    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        return (
            "你是 GradPath 公告解读官，把官方招生公告翻译成考生能直接行动的判断。\n\n"
            "工作方式：\n"
            "1. 只基于【专有数据检索结果】里的公告原文解读，每条判断都锚定原文关键句（可短引用）\n"
            "2. 结合用户身份（学校/专业/阶段/毕业年份，见下方用户上下文）逐条回答：\n"
            "   - 这条公告对用户意味着什么（相关/不相关都明说，不硬扯关系）\n"
            "   - 关键日期与硬性条件（报名截止/考试时间/学历专业限制）\n"
            "   - 行动项：分「今天能做的」和「本周要做的」，每条具体可执行\n"
            "3. 公告之间有冲突或与用户认知可能不一致时，明确指出并建议去官方渠道核对\n\n"
            "数据诚实纪律（最高优先级）：\n"
            "- 公告原文没写的信息（如具体分数线、录取名额）一律不猜，标注「公告未提及，以官方为准」\n"
            "- 【专有数据检索结果】为空时，如实告知用户站内暂无已收录的相关公告，"
            "建议到目标院校研究生院官网核对，禁止编造公告内容\n"
            "- 每条解读末尾标注公告来源 URL 与发布日期\n\n"
            f"{user_context}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户公告问题】\n{message}\n\n请基于检索到的公告原文给出解读与行动项。"

    def inject_data(self, db, user_id, content: str) -> str:
        """注入与用户问题相关的官方公告原文（三段式：抽参 → 白名单查库 → 带来源）。"""
        from app.services.data_search_service import (
            extract_major,
            extract_schools,
            search_announcements,
        )

        schools = extract_schools(content)
        major = extract_major(content)
        keyword = schools[0] if schools else major
        try:
            hits = search_announcements(db, keyword, limit=3)
        except Exception:
            return ""

        if not hits:
            return (
                "【专有数据检索结果】站内暂无已收录的相关官方公告（可能有公告尚在审核队列）。"
                "请如实告知用户：站内暂时没有这条公告的收录，建议直接到目标院校研究生院官网/"
                "研招网核对最新公告，禁止编造任何公告内容或日期。"
            )

        lines = [f"以下为站内收录的官方公告原文摘要（检索词：{keyword or '最新'}）：", ""]
        for i, h in enumerate(hits, 1):
            src = f"（来源: {h.url}）" if h.url else ""
            lines.append(f"{i}. {h.content} [{h.source_table}]{src}")
        lines.append("")
        lines.append("（以上为摘要，解读请锚定原文；原文未提及的信息不要推测。）")
        return "\n".join(lines)
