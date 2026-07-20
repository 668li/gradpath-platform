# backend/app/services/pdf_service.py
"""PDF 报告生成服务 — 院校报告、职业报告、个人报告。

使用 reportlab 生成个性化 PDF 报告。
"""
import io
from datetime import date

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


def _iso(d) -> str | None:
    """将日期转换为 ISO 字符串。"""
    if d is None:
        return None
    if hasattr(d, "isoformat"):
        return d.isoformat()
    return str(d)


def _to_str(v) -> str:
    """安全转换为字符串。"""
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return str(v)
    return str(v)


# ======================================================================
# 公共样式
# ======================================================================

def _get_styles():
    """获取报告共用样式。"""
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
    h3_style = ParagraphStyle(
        "GPH3",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=colors.HexColor("#374151"),
        spaceBefore=10,
        spaceAfter=4,
    )
    normal_style = styles["Normal"]
    small_style = ParagraphStyle(
        "GPSmall",
        parent=normal_style,
        fontSize=8,
        textColor=colors.grey,
        alignment=2,
    )
    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "h2": h2_style,
        "h3": h3_style,
        "normal": normal_style,
        "small": small_style,
    }


def _make_table_style() -> TableStyle:
    """创建统一的表格样式。"""
    return TableStyle([
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
    ])


def _add_footer(story: list, styles: dict, title: str):
    """添加页脚。"""
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        f"{title} · 由 GradPath 自动生成 · {_iso(date.today())}",
        styles["small"],
    ))


# ======================================================================
# 院校报告 PDF
# ======================================================================

def generate_school_report_pdf(
    db: Session,
    school_id: str | None = None,
    school_name: str | None = None,
) -> bytes:
    """生成院校报告 PDF。

    包含：
    1. 院校基本信息
    2. 就业数据汇总
    3. 分数线趋势
    4. 院校对比建议
    """
    from uuid import UUID
    from app.models.school import School
    from app.models.employment_data import EmploymentData
    from app.models.report_record import ReportRecord
    from app.models.grad_intel import GradScorelineRecord, GradSchoolIntel

    # 查询学校信息
    school = None
    if school_id:
        try:
            school = db.query(School).filter(School.id == UUID(school_id)).first()
        except (ValueError, Exception):
            pass
    if not school and school_name:
        school = db.query(School).filter(School.name == school_name).first()
    if not school:
        # 返回空报告模板
        return _generate_empty_pdf("院校报告", "未找到指定院校信息")

    styles = _get_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(21 * cm, 29.7 * cm),
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"GradPath 院校报告 - {school.name}",
        author="GradPath",
    )

    story: list = []

    # ----- 封面 -----
    story.append(Paragraph(f"院校报告", styles["title"]))
    story.append(Paragraph(
        f"{school.name} | 生成日期：{_iso(date.today())}",
        styles["subtitle"],
    ))
    story.append(Spacer(1, 10))

    # ----- 基本信息 -----
    story.append(Paragraph("院校基本信息", styles["h2"]))
    info_rows = [
        ["属性", "信息"],
        ["院校名称", _to_str(school.name)],
        ["所在省份", _to_str(school.province)],
        ["院校层次", _to_str(school.level)],
        ["全国排名", _to_str(school.ranking) if school.ranking else "暂无"],
        ["就业率", f"{school.employment_rate}%" if school.employment_rate else "暂无"],
        ["考研率", f"{school.grad_school_rate}%" if school.grad_school_rate else "暂无"],
        ["出国率", f"{school.abroad_rate}%" if school.abroad_rate else "暂无"],
    ]
    if school.key_majors:
        info_rows.append(["优势专业", _to_str(school.key_majors)])

    info_table = Table(info_rows, colWidths=[4 * cm, 12 * cm])
    info_table.setStyle(_make_table_style())
    story.append(info_table)

    # ----- 就业数据 -----
    story.append(Paragraph("就业数据", styles["h2"]))
    employment_data = (
        db.query(EmploymentData)
        .filter(
            EmploymentData.school_name == school.name,
            EmploymentData.year.isnot(None),
        )
        .order_by(EmploymentData.year.desc())
        .limit(20)
        .all()
    )

    if not employment_data:
        story.append(Paragraph("暂无就业数据。", styles["normal"]))
    else:
        emp_rows = [["年份", "专业类别", "学历", "就业率", "升学率", "平均薪资"]]
        for ed in employment_data[:10]:
            emp_rows.append([
                _to_str(ed.year),
                _to_str(ed.major_category),
                _to_str(ed.degree.value if ed.degree else "all"),
                f"{ed.employment_rate}%" if ed.employment_rate else "-",
                f"{ed.further_study_rate}%" if ed.further_study_rate else "-",
                f"¥{ed.average_salary:.0f}" if ed.average_salary else "-",
            ])
        emp_table = Table(emp_rows, colWidths=[1.8*cm, 3*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        emp_table.setStyle(_make_table_style())
        story.append(emp_table)

    # ----- 分数线记录 -----
    story.append(Paragraph("复试分数线记录", styles["h2"]))
    scorelines = (
        db.query(GradScorelineRecord)
        .filter(GradScorelineRecord.university_name == school.name)
        .order_by(GradScorelineRecord.year.desc())
        .limit(10)
        .all()
    )

    if not scorelines:
        story.append(Paragraph("暂无分数线记录。", styles["normal"]))
    else:
        sl_rows = [["年份", "专业", "总分线", "政治", "外语", "业务课一", "业务课二"]]
        for sl in scorelines:
            sl_rows.append([
                _to_str(sl.year),
                _to_str(sl.major_name),
                _to_str(sl.total_score_line),
                _to_str(sl.politics_score),
                _to_str(sl.foreign_language_score),
                _to_str(sl.business_1_score),
                _to_str(sl.business_2_score),
            ])
        sl_table = Table(sl_rows, colWidths=[1.5*cm, 3.5*cm, 2*cm, 1.5*cm, 1.5*cm, 2*cm, 2*cm])
        sl_table.setStyle(_make_table_style())
        story.append(sl_table)

    # ----- 社区评价 -----
    story.append(Paragraph("社区情报", styles["h2"]))
    intel_records = (
        db.query(GradSchoolIntel)
        .filter(GradSchoolIntel.school_name == school.name)
        .order_by(GradSchoolIntel.created_at.desc())
        .limit(5)
        .all()
    )

    if not intel_records:
        story.append(Paragraph("暂无社区评价。", styles["normal"]))
    else:
        for g in intel_records:
            story.append(Paragraph(
                f"<b>{_to_str(g.major_name)}</b> ({_to_str(g.school_tier)})",
                styles["h3"],
            ))
            if g.insider_notes:
                story.append(Paragraph(f"内部备注：{_to_str(g.insider_notes)}", styles["normal"]))
            if g.ai_summary:
                story.append(Paragraph(f"AI 摘要：{_to_str(g.ai_summary)}", styles["normal"]))
            story.append(Spacer(1, 6))

    _add_footer(story, styles, f"院校报告 - {school.name}")
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ======================================================================
# 职业报告 PDF
# ======================================================================

def generate_career_report_pdf(
    db: Session,
    user_id,
    simulation_data: dict | None = None,
) -> bytes:
    """生成职业规划报告 PDF。

    包含：
    1. 用户背景
    2. 职业画像
    3. 模拟路径分析（如有）
    4. 建议与总结
    """
    from uuid import UUID
    from app.models.user import User
    from app.models.career_profile import CareerProfile
    from app.models.destination_decision import DestinationDecision

    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(CareerProfile).filter(CareerProfile.user_id == user_id).first()
    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .limit(10)
        .all()
    )

    styles = _get_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(21 * cm, 29.7 * cm),
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="GradPath 职业规划报告",
        author="GradPath",
    )

    story: list = []

    # ----- 封面 -----
    story.append(Paragraph("职业规划报告", styles["title"]))
    user_name = user.name if user else "未知用户"
    story.append(Paragraph(
        f"{user_name} | 生成日期：{_iso(date.today())}",
        styles["subtitle"],
    ))
    story.append(Spacer(1, 10))

    # ----- 用户背景 -----
    story.append(Paragraph("个人背景", styles["h2"]))
    bg_rows = [["属性", "信息"]]
    if user:
        bg_rows.extend([
            ["姓名", _to_str(user.name)],
            ["学校", _to_str(user.school)],
            ["专业", _to_str(user.major)],
            ["毕业年份", _to_str(user.graduation_year)],
            ["当前阶段", _to_str(user.current_stage.value if user.current_stage else "")],
        ])
    bg_table = Table(bg_rows, colWidths=[4 * cm, 12 * cm])
    bg_table.setStyle(_make_table_style())
    story.append(bg_table)

    # ----- 职业画像 -----
    story.append(Paragraph("职业画像", styles["h2"]))
    if not profile:
        story.append(Paragraph("暂未创建职业画像。", styles["normal"]))
    else:
        profile_rows = [
            ["属性", "评估"],
            ["教育层次", _to_str(profile.education_level)],
            ["目标方向", _to_str(profile.target_direction)],
            ["目标行业", _to_str(profile.target_industry)],
            ["技术能力", f"{'★' * profile.technical_skill}{'☆' * (5 - profile.technical_skill)}"],
            ["沟通能力", f"{'★' * profile.communication_skill}{'☆' * (5 - profile.communication_skill)}"],
            ["领导力", f"{'★' * profile.leadership_skill}{'☆' * (5 - profile.leadership_skill)}"],
            ["创造力", f"{'★' * profile.creativity_skill}{'☆' * (5 - profile.creativity_skill)}"],
        ]
        profile_table = Table(profile_rows, colWidths=[4 * cm, 12 * cm])
        profile_table.setStyle(_make_table_style())
        story.append(profile_table)

        if profile.self_introduction:
            story.append(Spacer(1, 8))
            story.append(Paragraph("自我介绍", styles["h3"]))
            story.append(Paragraph(_to_str(profile.self_introduction), styles["normal"]))

    # ----- 去向决策记录 -----
    story.append(Paragraph("去向决策记录", styles["h2"]))
    if not decisions:
        story.append(Paragraph("暂无决策记录。", styles["normal"]))
    else:
        dec_rows = [["日期", "类型", "状态", "信心", "说明"]]
        for d in decisions:
            dec_rows.append([
                _iso(d.decision_date),
                _to_str(d.destination_type.value if d.destination_type else ""),
                _to_str(d.status.value if d.status else ""),
                f"{d.confidence}/5" if d.confidence else "-",
                Paragraph(_to_str(d.reasoning or ""), styles["normal"]),
            ])
        dec_table = Table(dec_rows, colWidths=[2.5*cm, 2.5*cm, 2*cm, 1.5*cm, 7*cm])
        dec_table.setStyle(_make_table_style())
        story.append(dec_table)

    # ----- 模拟路径分析 -----
    if simulation_data and simulation_data.get("paths"):
        story.append(Paragraph("职业路径模拟分析", styles["h2"]))
        paths = simulation_data["paths"]

        path_rows = [["路径名称", "总薪资(万)", "满意度", "稳定性", "风险", "推荐"]]
        for p in paths[:5]:
            path_rows.append([
                _to_str(p.get("name", "")),
                f"{p.get('total_income', 0) / 10000:.1f}",
                f"{p.get('avg_satisfaction', 0)}/10",
                f"{p.get('stability_score', 0)}/10",
                _to_str(p.get("overall_risk", "")),
                _to_str(p.get("recommendation", "")),
            ])
        path_table = Table(path_rows, colWidths=[3*cm, 2.5*cm, 2*cm, 2*cm, 2*cm, 4*cm])
        path_table.setStyle(_make_table_style())
        story.append(path_table)

    _add_footer(story, styles, "职业规划报告")
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ======================================================================
# 个人报告 PDF
# ======================================================================

def generate_profile_report_pdf(
    db: Session,
    user_id,
) -> bytes:
    """生成个人综合报告 PDF。

    包含：
    1. 个人信息
    2. 游戏化数据
    3. 技能树
    4. 复盘记录
    5. 收藏列表
    """
    from uuid import UUID
    from app.models.user import User
    from app.models.skill_node import SkillNode
    from app.models.retrospective import Retrospective
    from app.models.destination_decision import DestinationDecision
    from app.models.career_event import CareerEvent
    from app.models.bookmark import Bookmark
    from app.services.gamification_service import calculate_xp, get_level

    user = db.query(User).filter(User.id == user_id).first()
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
        .limit(10)
        .all()
    )
    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .limit(10)
        .all()
    )
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.event_date.desc())
        .limit(10)
        .all()
    )
    bookmarks = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == user_id)
        .order_by(Bookmark.created_at.desc())
        .limit(20)
        .all()
    )

    xp = calculate_xp(db, user_id)
    level, level_name, _, _ = get_level(xp)

    styles = _get_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(21 * cm, 29.7 * cm),
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="GradPath 个人报告",
        author="GradPath",
    )

    story: list = []

    # ----- 封面 -----
    story.append(Paragraph("个人综合报告", styles["title"]))
    user_name = user.name if user else "未知用户"
    story.append(Paragraph(
        f"{user_name} | 生成日期：{_iso(date.today())}",
        styles["subtitle"],
    ))
    story.append(Spacer(1, 10))

    # ----- 基本信息 -----
    story.append(Paragraph("基本信息", styles["h2"]))
    info_rows = [
        ["属性", "信息"],
        ["姓名", _to_str(user.name) if user else ""],
        ["邮箱", _to_str(user.email) if user else ""],
        ["学校", _to_str(user.school) if user else ""],
        ["专业", _to_str(user.major) if user else ""],
        ["毕业年份", _to_str(user.graduation_year) if user else ""],
    ]
    info_table = Table(info_rows, colWidths=[4 * cm, 12 * cm])
    info_table.setStyle(_make_table_style())
    story.append(info_table)

    # ----- 游戏化概览 -----
    story.append(Paragraph("游戏化概览", styles["h2"]))
    game_rows = [
        ["属性", "数值"],
        ["经验值 (XP)", str(xp)],
        ["等级", f"{level} - {level_name}"],
        ["决策记录", f"{len(decisions)} 条"],
        ["职业事件", f"{len(events)} 条"],
        ["技能节点", f"{len(skills)} 个"],
        ["复盘记录", f"{len(retros)} 条"],
        ["收藏", f"{len(bookmarks)} 条"],
    ]
    game_table = Table(game_rows, colWidths=[4 * cm, 12 * cm])
    game_table.setStyle(_make_table_style())
    story.append(game_table)

    # ----- 技能树 -----
    story.append(Paragraph("技能树", styles["h2"]))
    if not skills:
        story.append(Paragraph("暂无技能节点。", styles["normal"]))
    else:
        skill_rows = [["类别", "名称", "等级", "获得日期"]]
        for s in skills[:20]:
            skill_rows.append([
                _to_str(s.category),
                _to_str(s.name),
                _to_str(s.level),
                _iso(s.acquired_date),
            ])
        skill_table = Table(skill_rows, colWidths=[4*cm, 4*cm, 3*cm, 3*cm])
        skill_table.setStyle(_make_table_style())
        story.append(skill_table)

    # ----- 复盘记录 -----
    story.append(Paragraph("阶段复盘", styles["h2"]))
    if not retros:
        story.append(Paragraph("暂无复盘记录。", styles["normal"]))
    else:
        retro_rows = [["周期", "标题", "满意度"]]
        for r in retros:
            retro_rows.append([
                f"{_iso(r.period_start)} ~ {_iso(r.period_end)}",
                Paragraph(_to_str(r.title), styles["normal"]),
                _to_str(r.satisfaction),
            ])
        retro_table = Table(retro_rows, colWidths=[5*cm, 7*cm, 2*cm])
        retro_table.setStyle(_make_table_style())
        story.append(retro_table)

    # ----- 收藏列表 -----
    story.append(Paragraph("收藏列表", styles["h2"]))
    if not bookmarks:
        story.append(Paragraph("暂无收藏。", styles["normal"]))
    else:
        bk_rows = [["类型", "标题", "创建时间"]]
        for bk in bookmarks[:10]:
            bk_rows.append([
                _to_str(bk.item_type) if hasattr(bk, 'item_type') else "-",
                Paragraph(_to_str(bk.title) if hasattr(bk, 'title') else "-", styles["normal"]),
                _iso(bk.created_at),
            ])
        bk_table = Table(bk_rows, colWidths=[3*cm, 9*cm, 3*cm])
        bk_table.setStyle(_make_table_style())
        story.append(bk_table)

    _add_footer(story, styles, "个人综合报告")
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _generate_empty_pdf(title: str, message: str) -> bytes:
    """生成一个包含提示信息的空白 PDF。"""
    styles = _get_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(21 * cm, 29.7 * cm),
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"GradPath {title}",
        author="GradPath",
    )

    story = [
        Paragraph(title, styles["title"]),
        Spacer(1, 20),
        Paragraph(message, styles["normal"]),
    ]
    _add_footer(story, styles, title)
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
