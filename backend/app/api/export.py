# backend/app/api/export.py
"""数据导出 API 路由 — PDF 时间线、JSON 备份、公开技能分享。"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.export_service import (
    export_dark_knowledge_by_stage_pdf,
    export_grad_intel_csv,
    export_grad_intel_excel,
    export_grad_intel_json,
    export_grad_intel_pdf,
    export_profile_json,
    export_timeline_pdf,
    get_shareable_skills,
)

router = APIRouter(tags=["导出"])


@router.get("/api/export/timeline.pdf")
def export_pdf(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出 PDF 时间线（需认证）。"""
    pdf_bytes = export_timeline_pdf(db, user.id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=gradpath-timeline.pdf"
        },
    )


@router.get("/api/export/profile.json")
def export_json(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出 JSON 备份（需认证）。"""
    return export_profile_json(db, user.id)


@router.get("/api/share/skills/{token}")
def share_skills(token: str, db: Session = Depends(get_db)):
    """公开技能分享页面数据（无需认证）。"""
    result = get_shareable_skills(db, token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分享链接无效或已关闭",
        )
    return result


@router.get("/api/export/grad-intel")
def export_grad_intel_json_endpoint(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出考研情报数据为 JSON（需认证）。"""
    return export_grad_intel_json(db, user.id)


@router.get("/api/export/grad-intel/csv")
def export_grad_intel_csv_endpoint(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出考研情报数据为 CSV（需认证）。"""
    csv_content = export_grad_intel_csv(db, user.id)
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=grad-intel-export.csv"
        },
    )


@router.get("/api/export/grad-intel/pdf")
def export_grad_intel_pdf_endpoint(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出考研情报报告为 PDF（需认证）。"""
    pdf_bytes = export_grad_intel_pdf(db, user.id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=grad-intel-report.pdf"
        },
    )


@router.get("/api/export/dark-knowledge/pdf")
def export_dark_knowledge_pdf_endpoint(
    stage: str | None = None,
    db: Session = Depends(get_db),
):
    """按阶段导出暗知识为 PDF（公开接口）。"""
    pdf_bytes = export_dark_knowledge_by_stage_pdf(db, stage)
    filename = f"dark-knowledge-{stage}.pdf" if stage else "dark-knowledge-all.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/api/export/grad-intel/excel")
def export_grad_intel_excel_endpoint(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出考研情报数据为 Excel（需认证）。"""
    excel_bytes = export_grad_intel_excel(db, user.id)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=grad-intel-export.xlsx"
        },
    )
