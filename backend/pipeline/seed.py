# backend/pipeline/seed.py
"""种子数据脚本：导入 seed_data 中的常量并执行数据库写入。"""
from sqlalchemy import func

from app.database import SessionLocal
from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree
from pipeline.seed_data import SEED_SCHOOLS, SEED_DATA, SEED_DATA_2023, SEED_DATA_2022


def run_seed():
    db = SessionLocal()
    try:
        # 创建学校
        for s in SEED_SCHOOLS:
            existing = db.query(School).filter(School.slug == s["slug"]).first()
            if not existing:
                db.add(School(**s))
        db.commit()

        # 创建报告和就业数据
        for year_data, year in [(SEED_DATA, 2024), (SEED_DATA_2023, 2023), (SEED_DATA_2022, 2022)]:
            for row in year_data:
                slug = row[0]
                major = row[1]
                degree = row[3]
                total = row[4]
                emp_rate = row[5]
                study_rate = row[6]
                civil_rate = row[7]
                abroad_rate = row[8]
                employers = row[9]
                industries = row[10]
                regions = row[11]
                schools = row[12]
                startup_rate = row[13] if len(row) > 13 else 0.0
                gap_year_rate = row[14] if len(row) > 14 else 0.0

                school = db.query(School).filter(School.slug == slug).first()
                if not school:
                    continue

                report = db.query(ReportRecord).filter(
                    ReportRecord.school_id == school.id,
                    ReportRecord.year == year,
                ).first()
                if not report:
                    report = ReportRecord(
                        school_id=school.id,
                        year=year,
                        source_url=f"https://{school.report_index_url}{year}/report.htm",
                        parse_status=ParseStatus.published,
                    )
                    db.add(report)
                    db.commit()

                existing_emp = db.query(EmploymentData).filter(
                    EmploymentData.report_id == report.id,
                    EmploymentData.major == major,
                    EmploymentData.degree == Degree(degree),
                ).first()
                if existing_emp:
                    continue

                emp = EmploymentData(
                    report_id=report.id,
                    major=major,
                    degree=Degree(degree),
                    total_graduates=total,
                    employment_rate=emp_rate,
                    further_study_rate=study_rate,
                    civil_service_rate=civil_rate,
                    abroad_rate=abroad_rate,
                    startup_rate=startup_rate,
                    gap_year_rate=gap_year_rate,
                    employer_ranking=employers,
                    industry_distribution=industries,
                    destination_region=regions,
                    school_for_further_study=schools,
                )
                db.add(emp)
                db.commit()

        print(f"种子数据导入完成")
        sc = db.query(School).count()
        rc = db.query(ReportRecord).filter(ReportRecord.parse_status == ParseStatus.published).count()
        ec = db.query(EmploymentData).count()
        print(f"学校: {sc}, 已发布报告: {rc}, 就业数据记录: {ec}")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()