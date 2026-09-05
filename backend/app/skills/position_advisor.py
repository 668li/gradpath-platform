# backend/app/skills/position_advisor.py
"""选岗参谋 Skill — 基于条件账本+真实职位表的考公选岗对话。

数据面：gwy_position（国考）/ gwy_province_position（省考）/ gwy_score_line（进面分），
全部经 data_search_service 白名单查询器，带来源注入；绝不编造职位或分数线。
"""

from __future__ import annotations

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = [
    "选岗", "报岗", "职位", "岗位", "国考", "省考", "公务员",
    "招录", "招考", "岗位表", "考公",
]


class PositionAdvisorSkill(BaseSkill):
    """选岗参谋 Skill。"""

    code = "position_advisor"
    name = "选岗参谋"
    description = "按你的学历/专业/意向地区筛选真实公务员岗位，附进面分与来源"
    icon = "🎯"
    # positions 域由本 skill 的 inject_data 负责，chat 通用搜索层跳过
    covered_data_domains = frozenset({"positions"})

    def should_activate(self, message: str, context: dict) -> bool:
        msg = (message or "").lower()
        return any(kw in msg for kw in ACTIVATE_KEYWORDS)

    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        knowledge_block = ""
        if knowledge:
            lines = ["【相关知识库参考】"]
            for k in knowledge[:3]:
                content = (k.get("content") or "")[:150]
                lines.append(f"- 《{k.get('title', '')}》{content}")
            knowledge_block = "\n".join(lines) + "\n\n"

        return (
            "你是 GradPath 选岗参谋，帮用户从真实公务员职位表中筛选能报、值得报的岗位。\n\n"
            "工作方式：\n"
            "1. 先看【专有数据检索结果】：里面是按用户条件从站内职位表筛出的真实岗位（含招录人数、"
            "学历要求、专业要求、部分岗位附去年进面最低分），每条带来源\n"
            "2. 基于这些岗位做分析：可报性判断、竞争度提示（招录人数少的岗位竞争通常更激烈）、"
            "结合用户身份给梯度建议（稳妥/可冲）\n"
            "3. 结论前置：先给 2-3 个最值得考虑的岗位和理由，再列其余可选\n\n"
            "数据诚实纪律（最高优先级）：\n"
            "- 岗位、招录人数、学历/专业要求、进面分数只能引用【专有数据检索结果】，站内没有就明说"
            "「暂无匹配岗位」，绝不编造职位或数字\n"
            "- 「去年进面最低分」仅数据库已收录的岗位才有，未附带的岗位不要猜分\n"
            "- 职位表为最新收录年份，政策每年会变，提醒用户以官方公告为准\n\n"
            "澄清纪律：\n"
            "- 若【专有数据检索结果】提示信息不足，用选项化问题澄清（A/B/C 选项，问学历/意向地区/"
            "意向系统三选一即可），一次最多问 2 个\n"
            "- 用户专业模糊时（如只说文科），请他给出具体专业名称再精筛\n\n"
            f"{knowledge_block}{user_context}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户选岗请求】\n{message}\n\n请基于检索到的真实岗位数据给出选岗建议。"

    def inject_data(self, db, user_id, content: str) -> str:
        """筛选真实岗位注入（三段式：规则抽参 → 白名单查库 → 带来源）。"""
        from app.services.data_search_service import (
            extract_dept,
            extract_education,
            extract_major,
            extract_province,
            search_positions,
        )

        education = extract_education(content)
        province = extract_province(content)
        dept = extract_dept(content)
        major = extract_major(content)

        # 消息里没提的条件 → 从用户档案兜底（education/major 为注册档案字段）
        if not major or not education:
            try:
                from app.models.user import User

                user = db.get(User, user_id)
                if user is not None:
                    major = major or getattr(user, "major", None) or None
                    education = education or getattr(user, "education", None) or None
            except Exception:
                pass

        if not any([education, province, dept, major]):
            return (
                "【专有数据检索结果】用户条件不足，未能从职位表筛选。请先用选项化问题澄清："
                "①学历层次（专科/本科/硕士/博士）②意向地区（省份）③意向系统（如税务/海关/法院等），"
                "澄清后再分析。禁止在没有数据的情况下罗列岗位。"
            )

        try:
            hits = search_positions(
                db, education=education, province=province, dept=dept, major=major, limit=12
            )
        except Exception:
            return ""

        if not hits:
            return (
                "【专有数据检索结果】按当前条件（"
                f"学历={education or '未指定'}，地区={province or '未指定'}，"
                f"系统={dept or '未指定'}，专业={major or '未指定'}）"
                "未筛到匹配岗位。请如实告知用户暂无匹配记录，可建议放宽地区/专业条件，"
                "禁止编造岗位。"
            )

        lines = [f"筛选条件：学历={education or '不限'}，地区={province or '不限'}，系统={dept or '不限'}，专业={major or '不限'}", ""]
        sources_note = []
        for i, h in enumerate(hits, 1):
            src = f"（来源: {h.url}）" if h.url else ""
            lines.append(f"{i}. {h.content} [{h.source_table}·{h.year}年]{src}")
            sources_note.append(h.title[:30])
        lines.append("")
        lines.append("（以上为站内职位表最新收录年份的真实记录；招录人数为招考公告口径，以官方公告为准。）")
        return "\n".join(lines)
