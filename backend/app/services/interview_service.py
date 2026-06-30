# backend/app/services/interview_service.py
"""公司面试经验报告服务层 — 提交、查询、删除与聚合统计。"""
import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.interview_report import InterviewReport
from app.schemas.interview import (
    InterviewAggregateResponse,
    InterviewStats,
    InterviewSubmit,
)
from app.services.employment_service import escape_like

MIN_SAMPLE = 3


def submit_report(db: Session, user_id: UUID, data: InterviewSubmit) -> InterviewReport:
    """提交面试报告（upsert：同一用户 + 同一公司 + 同一岗位 + 同一年唯一）。"""
    existing = (
        db.query(InterviewReport)
        .filter(
            InterviewReport.user_id == user_id,
            InterviewReport.company == data.company,
            InterviewReport.position == data.position,
            InterviewReport.interview_year == data.interview_year,
        )
        .first()
    )
    if existing:
        for key, value in data.model_dump().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    report = InterviewReport(user_id=user_id, **data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_my_reports(db: Session, user_id: UUID) -> list[InterviewReport]:
    """获取当前用户提交的所有面试报告。"""
    return (
        db.query(InterviewReport)
        .filter(InterviewReport.user_id == user_id)
        .order_by(InterviewReport.interview_year.desc())
        .all()
    )


def delete_report(db: Session, user_id: UUID, report_id: str) -> None:
    """删除当前用户指定的面试报告。"""
    try:
        rid = uuid.UUID(report_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在"
        )
    report = (
        db.query(InterviewReport)
        .filter(
            InterviewReport.id == rid,
            InterviewReport.user_id == user_id,
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
    db: Session, company: str, position: str | None = None
) -> InterviewAggregateResponse:
    """聚合统计：模糊匹配公司与岗位，返回考察维度频率、难度分布、结果分布。

    当样本量 < MIN_SAMPLE 时仅返回 sample_count，不返回分布数据（隐私保护）。
    """
    filters = [
        InterviewReport.company.ilike(f"%{escape_like(company)}%", escape="\\"),
    ]
    if position:
        filters.append(
            InterviewReport.position.ilike(f"%{escape_like(position)}%", escape="\\")
        )

    sample_count = (
        db.query(func.count(InterviewReport.id)).filter(*filters).scalar() or 0
    )

    if sample_count < MIN_SAMPLE:
        return InterviewAggregateResponse(
            company=company,
            position=position,
            sample_count=sample_count,
            sufficient=False,
        )

    # 平均难度（仅非空值）
    avg_difficulty = (
        db.query(func.avg(InterviewReport.difficulty))
        .filter(*filters, InterviewReport.difficulty.isnot(None))
        .scalar()
    )

    # 平均轮数（仅非空值）
    avg_rounds = (
        db.query(func.avg(InterviewReport.rounds))
        .filter(*filters, InterviewReport.rounds.isnot(None))
        .scalar()
    )

    # 结果分布（比例）
    result_rows = (
        db.query(
            InterviewReport.result,
            func.count(InterviewReport.id),
        )
        .filter(*filters)
        .group_by(InterviewReport.result)
        .all()
    )
    result_distribution = {
        r.value: count / sample_count for r, count in result_rows
    }

    # 考察维度频率：由于 dimensions 存在 JSONB 数组中，
    # 需要逐行统计（SQLite 测试环境不支持 JSONB 查询）
    all_reports = (
        db.query(InterviewReport.dimensions)
        .filter(*filters)
        .all()
    )
    dim_count: dict[str, int] = {}
    for (dims,) in all_reports:
        if dims:
            for d in dims:
                dim_count[d] = dim_count.get(d, 0) + 1
    dimension_frequency = {
        d: count / sample_count for d, count in dim_count.items()
    }

    # 常见岗位（仅在不指定岗位时返回）
    common_positions = None
    if not position:
        pos_rows = (
            db.query(
                InterviewReport.position,
                func.count(InterviewReport.id),
            )
            .filter(*filters)
            .group_by(InterviewReport.position)
            .order_by(func.count(InterviewReport.id).desc())
            .limit(10)
            .all()
        )
        common_positions = [
            {"name": name, "count": count} for name, count in pos_rows
        ]

    return InterviewAggregateResponse(
        company=company,
        position=position,
        sample_count=sample_count,
        sufficient=True,
        avg_difficulty=round(float(avg_difficulty), 1) if avg_difficulty else None,
        avg_rounds=round(float(avg_rounds), 1) if avg_rounds else None,
        result_distribution=result_distribution,
        dimension_frequency=dimension_frequency,
        common_positions=common_positions,
    )


def get_stats(db: Session) -> InterviewStats:
    """全局统计：报告总数、覆盖公司数、覆盖岗位数。"""
    total = db.query(func.count(InterviewReport.id)).scalar() or 0
    company_count = (
        db.query(func.count(func.distinct(InterviewReport.company))).scalar() or 0
    )
    position_count = (
        db.query(func.count(func.distinct(InterviewReport.position))).scalar() or 0
    )
    return InterviewStats(
        total_reports=total,
        company_count=company_count,
        position_count=position_count,
    )


def list_companies(db: Session, keyword: str = "") -> list[dict]:
    """已收录公司列表（含样本数），支持模糊搜索。"""
    filters = []
    if keyword:
        filters.append(
            InterviewReport.company.ilike(
                f"%{escape_like(keyword)}%", escape="\\"
            )
        )
    rows = (
        db.query(
            InterviewReport.company,
            func.count(InterviewReport.id),
        )
        .filter(*filters)
        .group_by(InterviewReport.company)
        .order_by(func.count(InterviewReport.id).desc())
        .limit(50)
        .all()
    )
    return [{"name": name, "count": count} for name, count in rows]
