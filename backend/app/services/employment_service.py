# backend/app/services/employment_service.py
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.models.employment_data import EmploymentData
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School


def search_employment(
    db: Session,
    school: str,
    major: str,
    year: int | None = None,
    degree: str | None = None,
) -> dict:
    """搜索就业数据"""
    # 模糊匹配学校
    school_obj = db.query(School).filter(School.name.ilike(f"%{school}%")).first()

    if not school_obj:
        return {"school": None, "major": None, "records": [], "trend": None}

    # 查询已发布的报告
    query = (
        db.query(EmploymentData)
        .join(ReportRecord)
        .filter(
            ReportRecord.school_id == school_obj.id,
            ReportRecord.parse_status == ParseStatus.published,
            EmploymentData.major.ilike(f"%{major}%"),
        )
    )
    if year:
        query = query.filter(ReportRecord.year == year)
    if degree:
        query = query.filter(EmploymentData.degree == degree)

    query = query.order_by(ReportRecord.year.desc())
    results = query.all()

    # 构建记录
    records = []
    for emp in results:
        report = emp.report
        records.append({
            "year": report.year,
            "degree": emp.degree.value,
            "total_graduates": emp.total_graduates,
            "rates": {
                "employment": emp.employment_rate,
                "further_study": emp.further_study_rate,
                "civil_service": emp.civil_service_rate,
                "abroad": emp.abroad_rate,
                "startup": emp.startup_rate,
                "gap_year": emp.gap_year_rate,
            },
            "employer_ranking": emp.employer_ranking,
            "industry_distribution": emp.industry_distribution,
            "destination_region": emp.destination_region,
            "school_for_further_study": emp.school_for_further_study,
        })

    # 构建趋势
    trend = _build_trend(results)

    return {
        "school": {"id": str(school_obj.id), "name": school_obj.name, "slug": school_obj.slug, "code": school_obj.code},
        "major": results[0].major if results else None,
        "records": records,
        "trend": trend,
    }


def _build_trend(results: list[EmploymentData]) -> dict | None:
    if len(results) < 1:
        return None
    # 按年份升序
    sorted_results = sorted(results, key=lambda x: x.report.year)
    years = [r.report.year for r in sorted_results]
    return {
        "years": years,
        "employment_rate": [r.employment_rate for r in sorted_results],
        "further_study_rate": [r.further_study_rate for r in sorted_results],
        "civil_service_rate": [r.civil_service_rate for r in sorted_results],
        "abroad_rate": [r.abroad_rate for r in sorted_results],
    }


def list_schools(db: Session) -> list[dict]:
    """列出已收录学校（含已发布报告数）"""
    schools = db.query(School).all()
    result = []
    for s in schools:
        report_count = (
            db.query(func.count(ReportRecord.id))
            .filter(ReportRecord.school_id == s.id, ReportRecord.parse_status == ParseStatus.published)
            .scalar() or 0
        )
        major_count = (
            db.query(distinct(EmploymentData.major))
            .join(ReportRecord)
            .filter(ReportRecord.school_id == s.id, ReportRecord.parse_status == ParseStatus.published)
            .count()
        )
        if report_count > 0:
            result.append({
                "id": str(s.id), "name": s.name, "slug": s.slug, "code": s.code,
                "report_count": report_count, "major_count": major_count,
            })
    return result


def list_majors(db: Session, school: str) -> list[str]:
    """列出某校已收录专业"""
    school_obj = db.query(School).filter(School.name.ilike(f"%{school}%")).first()
    if not school_obj:
        return []
    majors = (
        db.query(distinct(EmploymentData.major))
        .join(ReportRecord)
        .filter(ReportRecord.school_id == school_obj.id, ReportRecord.parse_status == ParseStatus.published)
        .all()
    )
    return [m[0] for m in majors]


def get_stats(db: Session) -> dict:
    """全局统计"""
    published_reports = (
        db.query(ReportRecord)
        .filter(ReportRecord.parse_status == ParseStatus.published)
        .all()
    )
    school_ids = set(r.school_id for r in published_reports)
    major_count = (
        db.query(distinct(EmploymentData.major))
        .join(ReportRecord)
        .filter(ReportRecord.parse_status == ParseStatus.published)
        .count()
    )
    years = [r.year for r in published_reports]
    return {
        "school_count": len(school_ids),
        "report_count": len(published_reports),
        "major_count": major_count,
        "year_range": [min(years) if years else None, max(years) if years else None],
    }
