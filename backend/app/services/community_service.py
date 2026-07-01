# backend/app/services/community_service.py
"""社区毕业去向报告服务层 — 提交、查询、删除与聚合统计。"""
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.community_report import CommunityReport
from app.schemas.community import (
    AggregateResponse,
    CommunityStats,
    CommunitySubmit,
)
from app.services.employment_service import escape_like

# 样本量不足阈值：低于此值时不返回分布数据，仅返回样本数
MIN_SAMPLE = 3


def submit_report(db: Session, user_id: UUID, data: CommunitySubmit) -> CommunityReport:
    """提交社区报告（upsert：同一用户 + 同一毕业年份唯一）。"""
    existing = (
        db.query(CommunityReport)
        .filter(
            CommunityReport.user_id == user_id,
            CommunityReport.graduation_year == data.graduation_year,
        )
        .first()
    )
    if existing:
        # 更新已有记录
        for key, value in data.model_dump().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    report = CommunityReport(user_id=user_id, **data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_my_reports(db: Session, user_id: UUID) -> list[CommunityReport]:
    """获取当前用户提交的所有社区报告。"""
    return (
        db.query(CommunityReport)
        .filter(CommunityReport.user_id == user_id)
        .order_by(CommunityReport.graduation_year.desc())
        .all()
    )


def list_my_reports_paginated(
    db: Session, user_id: UUID, page: int = 1, page_size: int = 20
) -> tuple[list[CommunityReport], int]:
    """分页查询当前用户提交的社区报告（按毕业年份降序）。"""
    query = db.query(CommunityReport).filter(CommunityReport.user_id == user_id)
    total = query.count()
    items = (
        query.order_by(CommunityReport.graduation_year.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def delete_report(db: Session, user_id: UUID, report_id: str) -> None:
    """删除当前用户指定的社区报告。"""
    try:
        rid = uuid.UUID(report_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在"
        )
    report = (
        db.query(CommunityReport)
        .filter(
            CommunityReport.id == rid,
            CommunityReport.user_id == user_id,
        )
        .first()
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在"
        )
    db.delete(report)
    db.commit()


def aggregate(
    db: Session, school: str, major: str, year: int | None = None
) -> AggregateResponse:
    """聚合统计：模糊匹配学校与专业，返回去向分布、热门雇主/城市/行业、薪资分布。

    当样本量 < MIN_SAMPLE 时仅返回 sample_count，不返回分布数据（隐私保护）。
    """
    filters = [
        CommunityReport.school_name.ilike(
            f"%{escape_like(school)}%", escape="\\"
        ),
        CommunityReport.major.ilike(
            f"%{escape_like(major)}%", escape="\\"
        ),
    ]
    if year is not None:
        filters.append(CommunityReport.graduation_year == year)

    sample_count = (
        db.query(func.count(CommunityReport.id)).filter(*filters).scalar() or 0
    )

    if sample_count < MIN_SAMPLE:
        return AggregateResponse(
            school=school,
            major=major,
            sample_count=sample_count,
            sufficient=False,
        )

    # 去向类型分布（比例）
    dest_rows = (
        db.query(
            CommunityReport.destination_type,
            func.count(CommunityReport.id),
        )
        .filter(*filters)
        .group_by(CommunityReport.destination_type)
        .all()
    )
    destination_distribution = {
        dt.value: count / sample_count for dt, count in dest_rows
    }

    # 热门雇主（按数量降序，取前10）
    emp_rows = (
        db.query(CommunityReport.employer, func.count(CommunityReport.id))
        .filter(*filters, CommunityReport.employer.isnot(None))
        .group_by(CommunityReport.employer)
        .order_by(func.count(CommunityReport.id).desc())
        .limit(10)
        .all()
    )
    top_employers = [{"name": name, "count": count} for name, count in emp_rows]

    # 热门城市（按数量降序，取前10）
    city_rows = (
        db.query(CommunityReport.city, func.count(CommunityReport.id))
        .filter(*filters, CommunityReport.city.isnot(None))
        .group_by(CommunityReport.city)
        .order_by(func.count(CommunityReport.id).desc())
        .limit(10)
        .all()
    )
    top_cities = [{"name": name, "count": count} for name, count in city_rows]

    # 热门行业（按数量降序，取前10）
    ind_rows = (
        db.query(CommunityReport.industry, func.count(CommunityReport.id))
        .filter(*filters, CommunityReport.industry.isnot(None))
        .group_by(CommunityReport.industry)
        .order_by(func.count(CommunityReport.id).desc())
        .limit(10)
        .all()
    )
    top_industries = [{"name": name, "count": count} for name, count in ind_rows]

    # 薪资分布
    sal_rows = (
        db.query(
            CommunityReport.salary_range,
            func.count(CommunityReport.id),
        )
        .filter(*filters, CommunityReport.salary_range.isnot(None))
        .group_by(CommunityReport.salary_range)
        .all()
    )
    salary_distribution = {sr.value: count for sr, count in sal_rows}

    return AggregateResponse(
        school=school,
        major=major,
        sample_count=sample_count,
        sufficient=True,
        destination_distribution=destination_distribution,
        top_employers=top_employers,
        top_cities=top_cities,
        top_industries=top_industries,
        salary_distribution=salary_distribution,
    )


def get_stats(db: Session) -> CommunityStats:
    """全局统计：报告总数、覆盖学校数、覆盖专业数。"""
    total = db.query(func.count(CommunityReport.id)).scalar() or 0
    school_count = (
        db.query(func.count(func.distinct(CommunityReport.school_name)))
        .scalar()
        or 0
    )
    major_count = (
        db.query(func.count(func.distinct(CommunityReport.major))).scalar() or 0
    )
    return CommunityStats(
        total_reports=total,
        school_count=school_count,
        major_count=major_count,
    )
