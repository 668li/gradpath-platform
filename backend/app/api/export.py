# backend/app/api/export.py
"""数据导出 API 路由 — PDF 时间线、JSON 备份、公开技能分享。"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.export_service import (
    export_profile_json,
    export_timeline_pdf,
    get_shareable_skills,
)
from app.services.path_comparison_service import get_shareable_report

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
        headers={"Content-Disposition": "attachment; filename=gradpath-timeline.pdf"},
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


@router.get("/api/share/decision/{token}")
def share_decision(token: str, db: Session = Depends(get_db)):
    """公开决策报告分享页面数据（无需认证）。

    返回匿名化的「我的报考决策报告」：三路指标 / 综合建议 / 岗位与院校分析 /
    同分人群去向，不含用户名、结果回传等个人数据。
    """
    result = get_shareable_report(db, token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分享链接无效或已关闭",
        )
    return result
