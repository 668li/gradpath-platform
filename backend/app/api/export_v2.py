# backend/app/api/export_v2.py
"""数据导出 V2 API — 院校报告、职业报告、个人报告、数据导出。

端点：
    GET /api/export-v2/school-report        院校报告 PDF
    GET /api/export-v2/career-report        职业报告 PDF
    GET /api/export-v2/profile-report       个人报告 PDF
    GET /api/export-v2/data-export          数据导出 CSV/JSON
"""
import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User

router = APIRouter(tags=["导出V2"])


# ======================================================================
# 院校报告 PDF
# ======================================================================

@router.get("/api/export-v2/school-report")
def school_report_pdf(
    school_id: str | None = Query(None, description="院校 ID"),
    school_name: str | None = Query(None, description="院校名称（与 school_id 二选一）"),
    db: Session = Depends(get_db),
):
    """导出院校报告为 PDF（公开接口）。"""
    if not school_id and not school_name:
        raise HTTPException(
            status_code=400,
            detail="请提供 school_id 或 school_name 参数",
        )

    from app.services.pdf_service import generate_school_report_pdf
    pdf_bytes = generate_school_report_pdf(db, school_id=school_id, school_name=school_name)

    # 文件名：使用院校名称
    filename = f"school-report-{school_name or school_id}.pdf"
    filename = filename.replace(" ", "-")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ======================================================================
# 职业报告 PDF
# ======================================================================

@router.get("/api/export-v2/career-report")
def career_report_pdf(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出职业规划报告为 PDF（需认证）。"""
    from app.services.pdf_service import generate_career_report_pdf
    pdf_bytes = generate_career_report_pdf(db, user.id)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=career-report.pdf"},
    )


# ======================================================================
# 个人报告 PDF
# ======================================================================

@router.get("/api/export-v2/profile-report")
def profile_report_pdf(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出个人综合报告为 PDF（需认证）。"""
    from app.services.pdf_service import generate_profile_report_pdf
    pdf_bytes = generate_profile_report_pdf(db, user.id)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=profile-report.pdf"},
    )


# ======================================================================
# 数据导出 CSV/JSON
# ======================================================================

@router.get("/api/export-v2/data-export")
def data_export(
    format: str = Query("json", description="导出格式：json 或 csv"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出个人数据为 JSON 或 CSV（需认证）。"""
    if format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="format 参数仅支持 json 或 csv")

    from app.services.export_service import export_profile_json

    data = export_profile_json(db, user.id)

    if format == "json":
        return Response(
            content=json.dumps(data, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=gradpath-data-export.json"},
        )

    # CSV 格式：扁平化为多节拼接
    buf = io.StringIO()
    writer = csv.writer(buf)

    # 用户信息
    writer.writerow(["=== 用户信息 ==="])
    profile = data.get("profile", {})
    for key, value in profile.items():
        writer.writerow([key, value or ""])
    writer.writerow([])

    # 游戏化
    writer.writerow(["=== 游戏化数据 ==="])
    game = data.get("gamification", {})
    for key, value in game.items():
        writer.writerow([key, value or ""])
    writer.writerow([])

    # 决策记录
    writer.writerow(["=== 决策记录 ==="])
    decisions = data.get("decisions", [])
    if decisions:
        writer.writerow(["日期", "类型", "状态", "信心", "说明"])
        for d in decisions:
            writer.writerow([
                d.get("decision_date", ""),
                d.get("destination_type", ""),
                d.get("status", ""),
                d.get("confidence", ""),
                d.get("reasoning", ""),
            ])
    writer.writerow([])

    # 事件记录
    writer.writerow(["=== 职业事件 ==="])
    events = data.get("events", [])
    if events:
        writer.writerow(["日期", "类型", "标题", "描述"])
        for e in events:
            writer.writerow([
                e.get("event_date", ""),
                e.get("event_type", ""),
                e.get("title", ""),
                e.get("description", ""),
            ])
    writer.writerow([])

    # 技能
    writer.writerow(["=== 技能树 ==="])
    skills = data.get("skills", [])
    if skills:
        writer.writerow(["名称", "类别", "等级", "获得日期"])
        for s in skills:
            writer.writerow([
                s.get("name", ""),
                s.get("category", ""),
                s.get("level", ""),
                s.get("acquired_date", ""),
            ])
    writer.writerow([])

    # 复盘
    writer.writerow(["=== 复盘记录 ==="])
    retros = data.get("retrospectives", [])
    if retros:
        writer.writerow(["周期开始", "周期结束", "标题", "满意度"])
        for r in retros:
            writer.writerow([
                r.get("period_start", ""),
                r.get("period_end", ""),
                r.get("title", ""),
                r.get("satisfaction", ""),
            ])

    csv_content = buf.getvalue()
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=gradpath-data-export.csv"},
    )
