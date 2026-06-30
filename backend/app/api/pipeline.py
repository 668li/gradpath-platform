# backend/app/api/pipeline.py
"""Pipeline API 路由 — 管理员专用。"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.database import get_db
from app.models.user import User
from app.schemas.pipeline import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    IngestAPIRequest,
    IngestURLRequest,
    PipelineStats,
    ReportDetail,
    ReportListResponse,
)
from app.services.pipeline_service import (
    create_source,
    delete_report,
    delete_source,
    get_pipeline_stats,
    get_report_detail,
    ingest_api,
    ingest_file,
    ingest_url,
    list_reports,
    list_sources,
    publish_report,
    reparse_report,
    update_source,
    MAX_FILE_SIZE,
)

router = APIRouter(prefix="/api/pipeline", tags=["数据管道"])


@router.post("/ingest/url", response_model=ReportDetail)
def ingest_url_endpoint(
    body: IngestURLRequest,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """URL 抓取模式接入。"""
    try:
        return ingest_url(db, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/ingest/file", response_model=ReportDetail)
async def ingest_file_endpoint(
    school_slug: str = Form(...),
    year: int = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """文件上传模式接入。"""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件过大，最大 20MB")
    try:
        report = ingest_file(db, content, file.filename or "upload.html", school_slug, year)
        return report
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/ingest/api", response_model=ReportDetail)
def ingest_api_endpoint(
    body: IngestAPIRequest,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """外部 API 对接模式接入。"""
    try:
        return ingest_api(db, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reports", response_model=ReportListResponse)
def list_reports_endpoint(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """报告列表。"""
    return list_reports(db, status_filter=status, page=page, page_size=page_size)


@router.get("/reports/{report_id}", response_model=ReportDetail)
def get_report_endpoint(
    report_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """报告详情。"""
    from uuid import UUID
    try:
        return get_report_detail(db, UUID(report_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report_endpoint(
    report_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        delete_report(db, UUID(report_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/reports/{report_id}/reparse", response_model=ReportDetail)
def reparse_endpoint(
    report_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        return reparse_report(db, UUID(report_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/reports/{report_id}/publish", response_model=ReportDetail)
def publish_endpoint(
    report_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        return publish_report(db, UUID(report_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/stats", response_model=PipelineStats)
def stats_endpoint(
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return get_pipeline_stats(db)


# ===== DataSource CRUD =====

@router.get("/sources", response_model=list[DataSourceResponse])
def list_sources_endpoint(
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return list_sources(db)


@router.post("/sources", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def create_source_endpoint(
    body: DataSourceCreate,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    return create_source(db, body)


@router.put("/sources/{source_id}", response_model=DataSourceResponse)
def update_source_endpoint(
    source_id: str,
    body: DataSourceUpdate,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        return update_source(db, UUID(source_id), body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source_endpoint(
    source_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from uuid import UUID
    try:
        delete_source(db, UUID(source_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
