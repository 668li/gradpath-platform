# backend/pipeline/reviewer.py
"""报告审核与发布模块"""
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.employment_data import EmploymentData
from app.models.report_record import ParseStatus, ReportRecord


def review_report(db: Session, report_id: UUID) -> ReportRecord | None:
    """终端输出解析结果摘要，人工确认。

    仅 parse_status == parsed 的报告可审核。
    """
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report or report.parse_status != ParseStatus.parsed:
        print(f"无法审核：报告不存在或状态不是 parsed（当前: {report.parse_status if report else '不存在'}）")
        return None

    # 输出摘要
    data_list = db.query(EmploymentData).filter(EmploymentData.report_id == report_id).all()
    print(f"\n{'='*60}")
    print(f"报告审核：{report.year}年（{report.source_url}）")
    print(f"{'='*60}")
    for i, data in enumerate(data_list, 1):
        print(f"\n[{i}] 专业: {data.major} ({data.degree.value})")
        print(f"    毕业人数: {data.total_graduates}")
        print(f"    就业率: {data.employment_rate}, 升学率: {data.further_study_rate}")
        print(f"    考公率: {data.civil_service_rate}, 出国率: {data.abroad_rate}")
        if data.employer_ranking:
            print(f"    Top5 雇主:")
            for emp in data.employer_ranking[:5]:
                print(f"      - {emp['name']}: {emp['count']}人")
        if data.school_for_further_study:
            print(f"    Top5 升学去向:")
            for sch in data.school_for_further_study[:5]:
                print(f"      - {sch['name']}: {sch['count']}人")
    print(f"\n{'='*60}")

    choice = input("确认解析结果正确？(y/n): ").strip().lower()
    if choice == "y":
        report.parse_status = ParseStatus.reviewed
        db.commit()
        print("已标记为 reviewed")
    else:
        report.parse_status = ParseStatus.pending
        db.commit()
        print("已回退为 pending，可调整后重新 extract")
    return report


def publish_report(db: Session, report_id: UUID) -> ReportRecord | None:
    """发布报告，仅 reviewed 状态可发布。"""
    report = db.query(ReportRecord).filter(ReportRecord.id == report_id).first()
    if not report or report.parse_status != ParseStatus.reviewed:
        print(f"无法发布：报告不存在或状态不是 reviewed")
        return None

    report.parse_status = ParseStatus.published
    db.commit()
    print(f"报告已发布，数据对前端搜索可见")
    return report
