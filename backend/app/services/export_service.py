# backend/app/services/export_service.py
"""数据导出服务 — PDF 时间线、JSON 备份、公开技能分享页面。"""
import io
from datetime import date
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.community_report import CommunityReport
from app.models.destination_decision import DestinationDecision
from app.models.interview_report import InterviewReport
from app.models.retrospective import Retrospective
from app.models.skill_node import SkillNode
from app.models.user import User
from app.models.user_setting import UserSetting
from app.services.gamification_service import calculate_xp, get_level


# ======================================================================
# 工具函数
# ======================================================================

def _iso(d) -> str | None:
    """将日期/日期时间转换为 ISO 字符串，None 保持为 None。"""
    if d is None:
        return None
    if hasattr(d, "isoformat"):
        return d.isoformat()
    return str(d)


def _to_str(v) -> str:
    """安全转换为字符串（用于表格单元格）。"""
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return str(v)
    return str(v)


# ======================================================================
# PDF 导出
# ======================================================================

def export_timeline_pdf(db: Session, user_id: UUID) -> bytes:
    """生成 PDF 时间线。

    Sections:
        1. Profile header (name, email)
        2. XP / Level summary
        3. Timeline (decisions + events sorted by date)
        4. Skills summary
        5. Retrospectives list

    使用 reportlab.platypus: SimpleDocTemplate / Paragraph / Spacer / Table,
    通过 io.BytesIO 获取 bytes。
    """
    user = db.query(User).filter(User.id == user_id).first()
    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.asc())
        .all()
    )
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.event_date.asc())
        .all()
    )
    skills = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == user_id)
        .order_by(SkillNode.category.asc(), SkillNode.name.asc())
        .all()
    )
    retros = (
        db.query(Retrospective)
        .filter(Retrospective.user_id == user_id)
        .order_by(Retrospective.period_end.desc())
        .all()
    )

    xp = calculate_xp(db, user_id)
    level, level_name, current_min, next_min = get_level(xp)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(21 * cm, 29.7 * cm),  # A4
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="GradPath 时间线",
        author="GradPath",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "GPTitle",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=6,
        textColor=colors.HexColor("#1e3a8a"),
    )
    subtitle_style = ParagraphStyle(
        "GPSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "GPH2",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=14,
        spaceAfter=6,
    )
    normal_style = styles["Normal"]

    story: list = []

    # ----- Section 1: Profile header -----
    name = user.name if user else "未知用户"
    email = user.email if user else ""
    story.append(Paragraph("GradPath 成长时间线", title_style))
    profile_lines = [f"<b>姓名：</b>{name}"]
    if email:
        profile_lines.append(f"<b>邮箱：</b>{email}")
    if user and user.school:
        profile_lines.append(f"<b>学校：</b>{user.school}")
    if user and user.major:
        profile_lines.append(f"<b>专业：</b>{user.major}")
    if user and user.graduation_year:
        profile_lines.append(f"<b>毕业年份：</b>{user.graduation_year}")
    story.append(Paragraph("&nbsp;&nbsp;|&nbsp;&nbsp;".join(profile_lines), subtitle_style))
    story.append(Spacer(1, 6))

    # ----- Section 2: XP / Level summary -----
    story.append(Paragraph("游戏化概览", h2_style))
    xp_rows = [
        ["XP", str(xp)],
        ["等级", f"{level} - {level_name}"],
        ["当前等级区间", f"{current_min} - {next_min}"],
        ["去向决策数", str(len(decisions))],
        ["职业事件数", str(len(events))],
        ["技能节点数", str(len(skills))],
        ["复盘数", str(len(retros))],
    ]
    xp_table = Table(xp_rows, colWidths=[5 * cm, 11 * cm])
    xp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1e3a8a")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dbeafe")),
            ]
        )
    )
    story.append(xp_table)

    # ----- Section 3: Timeline (decisions + events sorted by date) -----
    story.append(Paragraph("成长时间线（决策 + 事件）", h2_style))

    timeline_items: list[tuple[date, str, str]] = []
    for d in decisions:
        timeline_items.append(
            (
                d.decision_date,
                f"[决策] {d.destination_type.value}（{d.status.value}）",
                f"信心：{d.confidence}/5；{d.reasoning or ''}".strip("；"),
            )
        )
    for e in events:
        desc = e.title
        if e.description:
            desc += f" — {e.description}"
        timeline_items.append(
            (
                e.event_date,
                f"[事件] {e.event_type.value}",
                desc,
            )
        )
    timeline_items.sort(key=lambda x: x[0])

    if not timeline_items:
        story.append(Paragraph("暂无时间线数据。", normal_style))
    else:
        timeline_rows = [["日期", "类型", "说明"]]
        for d, t, note in timeline_items:
            timeline_rows.append([_iso(d), t, Paragraph(_to_str(note), normal_style)])
        timeline_table = Table(timeline_rows, colWidths=[2.8 * cm, 4.2 * cm, 9 * cm])
        timeline_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#f8fafc")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                ]
            )
        )
        story.append(timeline_table)

    # ----- Section 4: Skills summary -----
    story.append(Paragraph("技能树概览", h2_style))
    if not skills:
        story.append(Paragraph("暂无技能节点。", normal_style))
    else:
        skill_rows = [["类别", "名称", "等级", "获得日期", "备注"]]
        for s in skills:
            skill_rows.append(
                [
                    _to_str(s.category),
                    _to_str(s.name),
                    _to_str(s.level),
                    _to_str(_iso(s.acquired_date)),
                    Paragraph(_to_str(s.notes or ""), normal_style),
                ]
            )
        skill_table = Table(
            skill_rows, colWidths=[3 * cm, 4 * cm, 1.5 * cm, 2.8 * cm, 4.7 * cm]
        )
        skill_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (2, 0), (2, -1), "CENTER"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#f8fafc")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                ]
            )
        )
        story.append(skill_table)

    # ----- Section 5: Retrospectives list -----
    story.append(Paragraph("阶段复盘", h2_style))
    if not retros:
        story.append(Paragraph("暂无复盘记录。", normal_style))
    else:
        retro_rows = [["周期", "标题", "满意度", "挑战", "收获"]]
        for r in retros:
            retro_rows.append(
                [
                    f"{_iso(r.period_start)} ~ {_iso(r.period_end)}",
                    Paragraph(_to_str(r.title), normal_style),
                    _to_str(r.satisfaction),
                    Paragraph(_to_str(r.challenges or ""), normal_style),
                    Paragraph(_to_str(r.lessons_learned or ""), normal_style),
                ]
            )
        retro_table = Table(
            retro_rows, colWidths=[3.5 * cm, 3 * cm, 1.5 * cm, 4 * cm, 4 * cm]
        )
        retro_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (2, 0), (2, -1), "CENTER"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#f8fafc")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                ]
            )
        )
        story.append(retro_table)

    # 页脚生成时间
    story.append(Spacer(1, 20))
    story.append(
        Paragraph(
            f"由 GradPath 自动生成 · {_iso(date.today())}",
            ParagraphStyle(
                "GPFooter",
                parent=normal_style,
                fontSize=8,
                textColor=colors.grey,
                alignment=2,  # right
            ),
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ======================================================================
# JSON 备份
# ======================================================================

def export_profile_json(db: Session, user_id: UUID) -> dict:
    """导出全部用户数据为 JSON dict。

    结构：
        profile: {name, email, school, major, graduation_year}
        gamification: {xp, level, level_name}
        decisions / events / skills / retrospectives /
        community_reports / interview_reports
    日期序列化为 ISO 字符串，UUID 序列化为字符串。
    """
    user = db.query(User).filter(User.id == user_id).first()

    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.asc())
        .all()
    )
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.event_date.asc())
        .all()
    )
    skills = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == user_id)
        .all()
    )
    retros = (
        db.query(Retrospective)
        .filter(Retrospective.user_id == user_id)
        .order_by(Retrospective.period_end.desc())
        .all()
    )
    community = (
        db.query(CommunityReport)
        .filter(CommunityReport.user_id == user_id)
        .all()
    )
    interviews = (
        db.query(InterviewReport)
        .filter(InterviewReport.user_id == user_id)
        .all()
    )

    xp = calculate_xp(db, user_id)
    level, level_name, _, _ = get_level(xp)

    profile = {
        "name": user.name if user else None,
        "email": user.email if user else None,
        "school": user.school if user else None,
        "major": user.major if user else None,
        "graduation_year": user.graduation_year if user else None,
    }

    decisions_data = [
        {
            "id": str(d.id),
            "decision_date": _iso(d.decision_date),
            "destination_type": d.destination_type.value if d.destination_type else None,
            "status": d.status.value if d.status else None,
            "details": d.details,
            "reasoning": d.reasoning,
            "confidence": d.confidence,
            "reference_snapshot_id": str(d.reference_snapshot_id) if d.reference_snapshot_id else None,
        }
        for d in decisions
    ]

    events_data = [
        {
            "id": str(e.id),
            "event_date": _iso(e.event_date),
            "event_type": e.event_type.value if e.event_type else None,
            "title": e.title,
            "description": e.description,
            "situation": e.situation,
            "task": e.task,
            "action": e.action,
            "result": e.result,
            "reflection": e.reflection,
            "skills_gained": e.skills_gained,
            "impact_metrics": e.impact_metrics,
            "mood": e.mood,
        }
        for e in events
    ]

    skills_data = [
        {
            "id": str(s.id),
            "name": s.name,
            "category": s.category,
            "level": s.level,
            "parent_id": str(s.parent_id) if s.parent_id else None,
            "acquired_date": _iso(s.acquired_date),
            "notes": s.notes,
        }
        for s in skills
    ]

    retros_data = [
        {
            "id": str(r.id),
            "period_type": r.period_type.value if r.period_type else None,
            "period_start": _iso(r.period_start),
            "period_end": _iso(r.period_end),
            "title": r.title,
            "achievements": r.achievements,
            "challenges": r.challenges,
            "lessons_learned": r.lessons_learned,
            "next_steps": r.next_steps,
            "satisfaction": r.satisfaction,
        }
        for r in retros
    ]

    community_data = [
        {
            "id": str(c.id),
            "school_name": c.school_name,
            "major": c.major,
            "graduation_year": c.graduation_year,
            "degree": c.degree.value if c.degree else None,
            "destination_type": c.destination_type.value if c.destination_type else None,
            "employer": c.employer,
            "city": c.city,
            "industry": c.industry,
            "salary_range": c.salary_range.value if c.salary_range else None,
        }
        for c in community
    ]

    interview_data = [
        {
            "id": str(i.id),
            "company": i.company,
            "position": i.position,
            "city": i.city,
            "interview_year": i.interview_year,
            "rounds": i.rounds,
            "result": i.result.value if i.result else None,
            "dimensions": i.dimensions,
            "difficulty": i.difficulty,
            "summary": i.summary,
        }
        for i in interviews
    ]

    return {
        "profile": profile,
        "gamification": {
            "xp": xp,
            "level": level,
            "level_name": level_name,
        },
        "decisions": decisions_data,
        "events": events_data,
        "skills": skills_data,
        "retrospectives": retros_data,
        "community_reports": community_data,
        "interview_reports": interview_data,
    }


# ======================================================================
# 公开技能分享
# ======================================================================

def get_shareable_skills(db: Session, share_token: str) -> dict | None:
    """根据分享令牌返回公开技能数据。

    - 根据 share_token 查找 UserSetting；未找到或 share_skills_enabled=False 返回 None。
    - 找到后查询该用户姓名与技能树。
    - 返回 {user_name, skills: [...]}，不包含任何其他个人数据。
    """
    if not share_token:
        return None

    setting = (
        db.query(UserSetting)
        .filter(UserSetting.share_token == share_token)
        .first()
    )
    if not setting or not setting.share_skills_enabled:
        return None

    user = db.query(User).filter(User.id == setting.user_id).first()
    if not user:
        return None

    skills = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == setting.user_id)
        .order_by(SkillNode.category.asc(), SkillNode.name.asc())
        .all()
    )

    return {
        "user_name": user.name,
        "skills": [
            {
                "id": str(s.id),
                "name": s.name,
                "category": s.category,
                "level": s.level,
                "parent_id": str(s.parent_id) if s.parent_id else None,
                "acquired_date": _iso(s.acquired_date),
                "notes": s.notes,
            }
            for s in skills
        ],
    }
