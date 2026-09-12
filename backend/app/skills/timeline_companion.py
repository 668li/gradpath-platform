# backend/app/skills/timeline_companion.py
"""流程伴随官 Skill — 考公流程时间线的对话伴随面。

数据面：Phase1 Exam/ExamNode（诚实三态 OFFICIAL/PREDICTED/UNKNOWN），
经 timeline_service VO 层（契约级诚实校验）取数；本站不代办动作，
只回答"到哪一步/接下来做什么/官方入口在哪"并引导订阅提醒。

文案纪律与提醒层同源（timeline_reminder.ASSERTIVE_WORDS）：
非 OFFICIAL 节点禁断言，PREDICTED 只许试探句——这是宪法第 4 条（时间诚实）
在对话面的落点，与 UI 徽章、提醒模板三处同一口径。
"""

from __future__ import annotations

from app.skills.base import BaseSkill

ACTIVATE_KEYWORDS = [
    "时间线", "考试流程", "到哪一步", "下一步该", "报名截止", "报名时间",
    "准考证", "笔试时间", "查分时间", "国考时间", "省考时间", "考试安排",
    "流程是什么",
]


class TimelineCompanionSkill(BaseSkill):
    """流程伴随官 Skill。"""

    code = "timeline_companion"
    name = "timeline_companion"
    description = "考公流程伴随：你现在到哪一步、接下来做什么、官方入口在哪、要备什么材料"
    icon = "route"
    # timeline 域由本 skill 的 inject_data 负责，chat 通用搜索层跳过
    covered_data_domains = frozenset({"timeline"})

    def should_activate(self, message: str, context: dict) -> bool:
        msg = (message or "").lower()
        return any(kw in msg for kw in ACTIVATE_KEYWORDS)

    def build_system_prompt(self, user_context: str, knowledge: list[dict]) -> str:
        from app.services.timeline_reminder import ASSERTIVE_WORDS

        forbidden = "、".join(ASSERTIVE_WORDS)
        return (
            "你是 GradPath 流程伴随官，陪用户走完考公全流程：告诉他现在到哪一步、"
            "接下来该做什么、官方入口在哪、要备什么材料。\n\n"
            "工作方式：\n"
            "1. 只基于【专有数据检索结果】里的节点数据回答；用户问『到哪一步』时，"
            "以「下一节点」为锚点说明判断依据\n"
            "2. 每个节点按数据里的三态口径表述：官方（可断言，附官方入口/来源）、"
            "预计（只许说『预计 X，公告后自动更新』）、日期待定（说『暂无可核验来源，"
            "官方公告后自动点亮』）\n"
            "3. 本站不代办任何动作：报名、缴费、打印准考证都在官方页面完成，"
            "你只负责『什么时候该做什么+官方入口』\n"
            "4. 行动建议落到本周能做的事（准备材料/收藏入口/留意公告），并提醒用户"
            "可在考公中心的『考试流程』页订阅节点提醒\n\n"
            f"时间诚实纪律（最高优先级）：非官方日期节点禁用这些断言词：{forbidden}；"
            "预测日期一律试探句式；日期未知就说暂无可核验来源。禁止编造任何日期、"
            "入口或材料要求。\n\n"
            f"{user_context}"
        )

    def build_user_prompt(self, message: str) -> str:
        return f"【用户流程问题】\n{message}\n\n请基于节点数据给出伴随式回答。"

    def inject_data(self, db, user_id, content: str) -> str:
        """注入考次时间线全节点（三态口径），以下一节点为锚点。"""
        from app.services import timeline_service as tl
        from app.services.data_search_service import (
            STAGE_KEY_WORDS,
            _enum_val,
            _pick_timeline_exam,
            _timeline_date_label,
        )

        text = content or ""
        track = "shengkao" if "省考" in text else ("guokao" if "国考" in text else None)
        stage = next((k for w, k in STAGE_KEY_WORDS if w in text), None)

        exam = _pick_timeline_exam(db, track)
        if exam is None:
            return (
                "【专有数据检索结果】站内暂无考试时间线数据。请如实告知用户暂无已收录"
                "考次，建议关注官方招考网站，禁止编造任何日期或流程。"
            )
        try:
            detail = tl.get_exam_detail(db, exam["code"])
        except Exception:
            return ""

        lines = [
            f"考次：{detail.get('name')}（{detail.get('status')}）"
            + (
                f"，官方入口：{detail.get('official_home_url')}"
                if detail.get("official_home_url")
                else ""
            ),
        ]
        nxt = detail.get("next_node")
        if nxt:
            stage_title = next(
                (
                    n.get("title")
                    for n in detail.get("nodes") or []
                    if _enum_val(n.get("stage_key")) == _enum_val(nxt.get("stage_key"))
                ),
                "",
            )
            lines.append(
                f"【当前进度锚点】下一节点：{stage_title or _enum_val(nxt.get('stage_key'))}"
                f"（{_status_label(nxt.get('date_status'), nxt.get('planned_date'))}）"
            )
        if stage:
            lines.append(f"（用户特别问到的环节：{stage}）")
        lines.append("")
        for n in detail.get("nodes") or []:
            date_part = _timeline_date_label(n)
            entry = f" 官方入口：{n.get('official_entry_url')}" if n.get("official_entry_url") else ""
            lines.append(f"- {n.get('title')}（{date_part}）{entry}")
        lines.append("")
        lines.append("（以上为站内时间线三态口径；非官方日期不要断言，动作引导去官方页面。）")
        return "\n".join(lines)

    def collect_sources(self, db, user_id, content: str) -> list[dict]:
        """回传节点官方入口，点亮前端「参考来源」标签。"""
        from app.services import timeline_service as tl
        from app.services.data_search_service import _pick_timeline_exam

        text = content or ""
        track = "shengkao" if "省考" in text else ("guokao" if "国考" in text else None)
        exam = _pick_timeline_exam(db, track)
        if exam is None:
            return []
        try:
            detail = tl.get_exam_detail(db, exam["code"])
        except Exception:
            return []
        sources = []
        if detail.get("official_home_url"):
            sources.append(
                {
                    "type": "db",
                    "title": f"{detail.get('name')}·官方专题"[:40],
                    "content": "考次官方入口",
                    "url": detail["official_home_url"],
                }
            )
        for n in detail.get("nodes") or []:
            url = n.get("official_entry_url") or n.get("source_url") or ""
            if not url:
                continue
            sources.append(
                {
                    "type": "db",
                    "title": f"{detail.get('name')}·{n.get('title')}"[:40],
                    "content": n.get("title") or "",
                    "url": url,
                }
            )
        return sources[:8]


def _status_label(date_status, planned_date) -> str:
    status = date_status.value if hasattr(date_status, "value") else date_status
    if status == "OFFICIAL" and planned_date:
        return f"官方：{planned_date.isoformat()}"
    if status == "PREDICTED" and planned_date:
        return f"预计 {planned_date.isoformat()}，公告后自动更新"
    return "日期待定（暂无可核验来源）"
