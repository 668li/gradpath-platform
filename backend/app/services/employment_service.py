# backend/app/services/employment_service.py
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models.employment_data import EmploymentData
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School


def escape_like(value: str) -> str:
    """转义 LIKE/ILIKE 通配符（``%`` 与 ``_``），避免用户输入被当作通配符。

    同时转义反斜杠本身，确保其作为字面量参与匹配。配合 ``ilike(..., escape="\\\\")``
    使用。
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_employment(
    db: Session,
    school: str,
    major: str,
    year: int | None = None,
    degree: str | None = None,
) -> dict:
    """搜索就业数据"""
    # 模糊匹配学校（转义 LIKE 通配符，避免 %/_ 被当作通配符）
    school_obj = (
        db.query(School)
        .filter(School.name.ilike(f"%{escape_like(school)}%", escape="\\"))
        .first()
    )

    if not school_obj:
        return {"school": None, "major": None, "records": [], "trend": None}

    # 查询已发布的报告
    query = (
        db.query(EmploymentData)
        .join(ReportRecord)
        .filter(
            ReportRecord.school_id == school_obj.id,
            ReportRecord.parse_status == ParseStatus.published,
            EmploymentData.major.ilike(f"%{escape_like(major)}%", escape="\\"),
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
    """列出已收录学校（含已发布报告数）。

    使用单条 ``GROUP BY`` 聚合查询一次性获取所有学校的 ``report_count`` 与
    ``major_count``，避免对每个学校执行 N+1 次查询（原实现为 2N+1 次）。

    - ``ReportRecord`` 使用 INNER JOIN：仅保留有已发布报告的学校（等价于原
      ``report_count > 0`` 的过滤）。
    - ``EmploymentData`` 使用 LEFT JOIN：保留有报告但暂无就业明细的学校，
      此时 ``major_count`` 为 0，与原实现行为一致。
    - 使用 ``COUNT(DISTINCT ...)`` 避免一对多 JOIN 导致的重复计数。
    """
    rows = (
        db.query(
            School.id,
            School.name,
            School.slug,
            School.code,
            func.count(distinct(ReportRecord.id)).label("report_count"),
            func.count(distinct(EmploymentData.major)).label("major_count"),
        )
        .join(ReportRecord, ReportRecord.school_id == School.id)
        .outerjoin(EmploymentData, EmploymentData.report_id == ReportRecord.id)
        .filter(ReportRecord.parse_status == ParseStatus.published)
        .group_by(School.id, School.name, School.slug, School.code)
        .all()
    )
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "slug": row.slug,
            "code": row.code,
            "report_count": row.report_count,
            "major_count": row.major_count,
        }
        for row in rows
    ]


def list_majors(db: Session, school: str) -> list[str]:
    """列出某校已收录专业"""
    school_obj = (
        db.query(School)
        .filter(School.name.ilike(f"%{escape_like(school)}%", escape="\\"))
        .first()
    )
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
    """全局统计。

    使用单条聚合查询获取 ``report_count`` / ``school_count`` / ``major_count`` /
    ``year_range``，避免将整张 ``report_records`` 表载入内存仅为计算 ``len()``、
    ``min(year)``、``max(year)``。

    - ``COUNT(DISTINCT ReportRecord.id)``：已发布报告数（LEFT JOIN 后需去重，
      避免一对多复制导致计数膨胀）。
    - ``COUNT(DISTINCT ReportRecord.school_id)``：覆盖学校数。
    - ``COUNT(DISTINCT EmploymentData.major)``：覆盖专业数。
    - ``MIN/MAX(ReportRecord.year)``：年份范围。
    """
    row = (
        db.query(
            func.count(distinct(ReportRecord.id)).label("report_count"),
            func.count(distinct(ReportRecord.school_id)).label("school_count"),
            func.count(distinct(EmploymentData.major)).label("major_count"),
            func.min(ReportRecord.year).label("min_year"),
            func.max(ReportRecord.year).label("max_year"),
        )
        .select_from(ReportRecord)
        .outerjoin(EmploymentData, EmploymentData.report_id == ReportRecord.id)
        .filter(ReportRecord.parse_status == ParseStatus.published)
        .one()
    )
    return {
        "school_count": row.school_count or 0,
        "report_count": row.report_count or 0,
        "major_count": row.major_count or 0,
        "year_range": [row.min_year, row.max_year],
    }
