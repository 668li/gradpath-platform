# backend/app/services/pipeline_service.py
"""Pipeline 业务逻辑。"""
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.data_source import DataSource
from app.models.employment_data import Degree, EmploymentData
from app.models.pipeline_enums import ContentType, SourceType
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School
from app.schemas.pipeline import (
    DataSourceCreate,
    DataSourceUpdate,
    IngestAPIRequest,
    IngestURLRequest,
)
from pipeline.extractors import ExtractResult
from pipeline.extractors.csv_extractor import extract_csv
from pipeline.extractors.excel_extractor import extract_excel
from pipeline.extractors.html_extractor import extract_html
from pipeline.extractors.pdf_extractor import extract_pdf
from pipeline.extractor import call_llm, MAX_TEXT_LENGTH
from pipeline.router import route_content

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv"}


def get_or_create_report(
    db: Session, school_id: UUID, year: int, source_url: str = "", source_type: SourceType = SourceType.crawl
) -> ReportRecord:
    """获取或创建报告记录。同校同年存在则返回已有记录。"""
    existing = db.query(ReportRecord).filter(
        ReportRecord.school_id == school_id,
        ReportRecord.year == year,
    ).first()
    if existing:
        return existing
    report = ReportRecord(
        school_id=school_id,
        year=year,
        source_url=source_url,
        source_type=source_type,
        parse_status=ParseStatus.pending,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def ingest_url(db: Session, req: IngestURLRequest) -> ReportRecord:
    """URL 抓取模式。"""
    school = db.query(School).filter(School.slug == req.school_slug).first()
    if not school:
        raise ValueError(f"学校 '{req.school_slug}' 不存在")

    report = get_or_create_report(db, school.id, req.year, req.url, SourceType.crawl)
    if report.parse_status not in (ParseStatus.pending, ParseStatus.failed):
        return report  # 已有处理结果

    # 抓取内容
    try:
        resp = httpx.get(req.url, timeout=30, follow_redirects=True,
                         headers={"User-Agent": "GradPathBot/1.0"})
        resp.raise_for_status()
        raw_content = resp.text
        mime_type = resp.headers.get("content-type", "").split(";")[0].strip()
    except Exception as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"抓取失败: {e}"
        db.commit()
        return report

    # 路由
    content_type = route_content(url=req.url, mime_type=mime_type)
    report.content_type = content_type
    report.raw_html = raw_content
    db.commit()

    # 提取 + 解析
    _extract_and_parse(db, report, content_type, raw_content)
    return report


def ingest_file(
    db: Session, file_content: bytes, filename: str, school_slug: str, year: int
) -> ReportRecord:
    """文件上传模式。"""
    school = db.query(School).filter(School.slug == school_slug).first()
    if not school:
        raise ValueError(f"学校 '{school_slug}' 不存在")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}")

    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError("文件过大，最大 20MB")

    # 保存文件
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    saved_name = f"{school_slug}_{year}_{timestamp}{ext}"
    file_path = UPLOAD_DIR / saved_name
    file_path.write_bytes(file_content)

    report = get_or_create_report(db, school.id, year, str(file_path), SourceType.upload)
    report.file_path = str(file_path)
    report.source_url = str(file_path)

    # 路由
    content_type = route_content(filename=filename)
    report.content_type = content_type
    db.commit()

    # 提取
    if content_type == ContentType.pdf:
        result = extract_pdf(str(file_path))
    elif content_type == ContentType.excel:
        result = extract_excel(str(file_path))
    elif content_type == ContentType.csv:
        result = extract_csv(file_content.decode("utf-8"))
    else:
        result = extract_html(file_content.decode("utf-8", errors="replace"))

    report.raw_html = result.text
    db.commit()

    # 解析
    _run_llm_parse(db, report)
    return report


def ingest_api(db: Session, req: IngestAPIRequest) -> ReportRecord:
    """外部 API 对接模式。"""
    school = db.query(School).filter(School.slug == req.school_slug).first()
    if not school:
        raise ValueError(f"学校 '{req.school_slug}' 不存在")

    source = db.query(DataSource).filter(DataSource.id == UUID(req.api_source_id)).first()
    if not source:
        raise ValueError("数据源不存在")
    if not source.is_active:
        raise ValueError("数据源已禁用")

    report = get_or_create_report(db, school.id, req.year, source.api_url or "", SourceType.api)

    # 调用外部 API
    try:
        headers = {}
        if source.api_key:
            headers["Authorization"] = f"Bearer {source.api_key}"
        resp = httpx.get(source.api_url, headers=headers, timeout=30)
        resp.raise_for_status()
        raw_content = resp.text
        mime_type = resp.headers.get("content-type", "").split(";")[0].strip()
    except Exception as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"API 调用失败: {e}"
        db.commit()
        return report

    # 路由
    content_type = route_content(mime_type=mime_type)
    report.content_type = content_type
    report.raw_html = raw_content
    db.commit()

    # 提取 + 解析
    _extract_and_parse(db, report, content_type, raw_content)
    return report


def _extract_and_parse(db: Session, report: ReportRecord, content_type: ContentType, raw_content: str):
    """提取文本（如需要）并运行 LLM 解析。"""
    if content_type == ContentType.html:
        result = extract_html(raw_content)
        report.raw_html = result.text
    elif content_type == ContentType.csv:
        result = extract_csv(raw_content)
        report.raw_html = result.text
    else:
        # PDF/Excel 已在 ingest_file 中提取
        result = ExtractResult(text=raw_content, content_type=content_type)
    db.commit()
    _run_llm_parse(db, report)


def _run_llm_parse(db: Session, report: ReportRecord):
    """运行 LLM 结构化解析。"""
    if not settings.LLM_API_KEY:
        # LLM 未配置，保持 pending
        return

    text = report.raw_html or ""
    if not text.strip():
        report.parse_status = ParseStatus.failed
        report.parse_error = "未提取到有效内容"
        db.commit()
        return

    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    try:
        llm_response = call_llm(text)
        data = json.loads(llm_response)
    except json.JSONDecodeError as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"LLM 返回无效 JSON: {e}"
        db.commit()
        return
    except Exception as e:
        report.parse_status = ParseStatus.failed
        report.parse_error = f"LLM 调用失败: {e}"
        db.commit()
        return

    # 写入 EmploymentData
    db.query(EmploymentData).filter(EmploymentData.report_id == report.id).delete()
    for major_data in data.get("majors", []):
        try:
            emp = EmploymentData(
                report_id=report.id,
                major=major_data.get("major", "未知专业"),
                degree=Degree(major_data.get("degree", "all")),
                total_graduates=major_data.get("total_graduates"),
                employment_rate=major_data.get("employment_rate"),
                further_study_rate=major_data.get("further_study_rate"),
                civil_service_rate=major_data.get("civil_service_rate"),
                abroad_rate=major_data.get("abroad_rate"),
                startup_rate=major_data.get("startup_rate"),
                gap_year_rate=major_data.get("gap_year_rate"),
                employer_ranking=major_data.get("employer_ranking", []),
                industry_distribution=major_data.get("industry_distribution", {}),
                destination_region=major_data.get("destination_region", {}),
                school_for_further_study=major_data.get("school_for_further_study", []),
            )
            db.add(emp)
        except Exception as e:
            logger.warning("跳过专业 %r: %s", major_data.get("major"), e)
            continue

    report.parse_status = ParseStatus.parsed
    report.parsed_at = datetime.now(timezone.utc)
    report.parse_error = None
    db.commit()


def reparse_report(db: Session, report_id: UUID) -> ReportRecord:
    """重新解析报告。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        raise ValueError("报告不存在")
    _run_llm_parse(db, report)
    return report


def publish_report(db: Session, report_id: UUID) -> ReportRecord:
    """发布报告。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        raise ValueError("报告不存在")
    report.parse_status = ParseStatus.published
    db.commit()
    return report


def delete_report(db: Session, report_id: UUID):
    """删除报告及其关联数据。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        raise ValueError("报告不存在")
    db.delete(report)
    db.commit()


def list_reports(
    db: Session, status_filter: str | None = None, page: int = 1, page_size: int = 20
) -> dict:
    """报告列表。"""
    query = db.query(ReportRecord).join(School)
    if status_filter:
        query = query.filter(ReportRecord.parse_status == status_filter)
    total = query.count()
    items = (
        query.order_by(ReportRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_report_detail(db: Session, report_id: UUID) -> ReportRecord:
    """报告详情。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report:
        raise ValueError("报告不存在")
    return report


def get_pipeline_stats(db: Session) -> dict:
    """管道统计。"""
    total = db.query(ReportRecord).count()
    published = db.query(ReportRecord).filter(ReportRecord.parse_status == ParseStatus.published).count()
    pending = db.query(ReportRecord).filter(
        ReportRecord.parse_status.in_([ParseStatus.pending, ParseStatus.parsed, ParseStatus.reviewed])
    ).count()
    failed = db.query(ReportRecord).filter(ReportRecord.parse_status == ParseStatus.failed).count()
    return {
        "total_reports": total,
        "published_count": published,
        "pending_count": pending,
        "failed_count": failed,
    }


# ===== DataSource CRUD =====

def list_sources(db: Session) -> list[DataSource]:
    return db.query(DataSource).order_by(DataSource.created_at.desc()).all()


def create_source(db: Session, data: DataSourceCreate) -> DataSource:
    source = DataSource(**data.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def update_source(db: Session, source_id: UUID, data: DataSourceUpdate) -> DataSource:
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise ValueError("数据源不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source


def delete_source(db: Session, source_id: UUID):
    source = db.query(DataSource).filter(DataSource.id == source_id).first()
    if not source:
        raise ValueError("数据源不存在")
    db.delete(source)
    db.commit()
