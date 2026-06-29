# backend/pipeline/seed.py
"""种子数据脚本：配置标杆高校并生成模拟数据用于验证"""
from app.database import SessionLocal
from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree


SEED_SCHOOLS = [
    {
        "name": "清华大学", "slug": "tsinghua", "code": "10003",
        "report_index_url": "https://career.tsinghua.edu.cn/",
        "province": "北京", "level": "985",
    },
    {
        "name": "北京大学", "slug": "pku", "code": "10001",
        "report_index_url": "https://scc.pku.edu.cn/",
        "province": "北京", "level": "985",
    },
    {
        "name": "浙江大学", "slug": "zju", "code": "10335",
        "report_index_url": "https://www.career.zju.edu.cn/",
        "province": "浙江", "level": "985",
    },
]

SEED_DATA = [
    # (school_slug, major, year, degree, total, emp_rate, study_rate, civil_rate, abroad_rate, employers, industries, regions, schools)
    ("tsinghua", "机械工程", 2024, "bachelor", 120, 0.45, 0.35, 0.08, 0.12,
     [{"name": "三一重工", "count": 15}, {"name": "比亚迪", "count": 12}, {"name": "华为", "count": 8}],
     {"制造业": 0.4, "互联网": 0.2, "金融": 0.1},
     {"北京": 0.3, "上海": 0.15, "广东": 0.1},
     [{"name": "清华大学", "count": 20}, {"name": "北京大学", "count": 5}]),
    ("tsinghua", "计算机科学与技术", 2024, "bachelor", 180, 0.55, 0.25, 0.05, 0.15,
     [{"name": "字节跳动", "count": 25}, {"name": "腾讯", "count": 20}, {"name": "阿里巴巴", "count": 15}],
     {"互联网": 0.5, "金融": 0.15, "制造业": 0.1},
     {"北京": 0.4, "上海": 0.2, "广东": 0.15},
     [{"name": "清华大学", "count": 30}, {"name": "斯坦福大学", "count": 8}]),
    ("tsinghua", "电子工程", 2024, "bachelor", 150, 0.50, 0.30, 0.07, 0.13,
     [{"name": "华为", "count": 20}, {"name": "中兴", "count": 10}, {"name": "大疆", "count": 8}],
     {"通讯": 0.35, "互联网": 0.25, "制造业": 0.15},
     {"北京": 0.35, "广东": 0.2, "上海": 0.1},
     [{"name": "清华大学", "count": 25}, {"name": "MIT", "count": 6}]),
    ("pku", "计算机科学与技术", 2024, "bachelor", 160, 0.52, 0.28, 0.06, 0.14,
     [{"name": "百度", "count": 18}, {"name": "字节跳动", "count": 15}, {"name": "腾讯", "count": 12}],
     {"互联网": 0.45, "金融": 0.2, "教育": 0.1},
     {"北京": 0.45, "上海": 0.15, "广东": 0.1},
     [{"name": "北京大学", "count": 28}, {"name": "清华大学", "count": 8}]),
    ("pku", "金融学", 2024, "bachelor", 100, 0.48, 0.32, 0.10, 0.10,
     [{"name": "中金公司", "count": 10}, {"name": "中信证券", "count": 8}, {"name": "工商银行", "count": 6}],
     {"金融": 0.6, "互联网": 0.1, "咨询": 0.1},
     {"北京": 0.5, "上海": 0.25, "深圳": 0.1},
     [{"name": "北京大学", "count": 15}, {"name": "清华大学", "count": 5}]),
    ("pku", "法学", 2024, "bachelor", 90, 0.40, 0.35, 0.15, 0.10,
     [{"name": "金杜律所", "count": 8}, {"name": "方达律所", "count": 6}, {"name": "最高法", "count": 5}],
     {"法律": 0.55, "金融": 0.15, "政府": 0.1},
     {"北京": 0.55, "上海": 0.2, "广东": 0.08},
     [{"name": "北京大学", "count": 18}, {"name": "中国政法大学", "count": 6}]),
    ("zju", "计算机科学与技术", 2024, "bachelor", 200, 0.58, 0.22, 0.05, 0.15,
     [{"name": "阿里巴巴", "count": 30}, {"name": "网易", "count": 18}, {"name": "字节跳动", "count": 15}],
     {"互联网": 0.55, "制造业": 0.1, "金融": 0.1},
     {"浙江": 0.4, "上海": 0.15, "北京": 0.15},
     [{"name": "浙江大学", "count": 35}, {"name": "清华大学", "count": 10}]),
    ("zju", "机械工程", 2024, "bachelor", 130, 0.50, 0.30, 0.08, 0.12,
     [{"name": "吉利汽车", "count": 12}, {"name": "海康威视", "count": 10}, {"name": "大华", "count": 8}],
     {"制造业": 0.45, "互联网": 0.15, "汽车": 0.15},
     {"浙江": 0.45, "上海": 0.15, "江苏": 0.1},
     [{"name": "浙江大学", "count": 22}, {"name": "上海交大", "count": 8}]),
    ("zju", "化学", 2024, "bachelor", 80, 0.42, 0.38, 0.05, 0.15,
     [{"name": "药明康德", "count": 8}, {"name": "恒瑞医药", "count": 6}, {"name": "巴斯夫", "count": 5}],
     {"化工": 0.4, "医药": 0.25, "材料": 0.1},
     {"浙江": 0.35, "上海": 0.2, "江苏": 0.15},
     [{"name": "浙江大学", "count": 20}, {"name": "北大", "count": 6}]),
]

# 2023年数据（简化版，只调整比例略变化）
SEED_DATA_2023 = [
    (*d[:4], d[4], d[5] + 0.03, d[6] - 0.02, d[7], d[8], d[9], d[10], d[11], d[12])
    for d in SEED_DATA
]


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
        for year_data in [SEED_DATA, SEED_DATA_2023]:
            year = 2024 if year_data is SEED_DATA else 2023
            for row in year_data:
                slug, major, _, degree, total, emp_rate, study_rate, civil_rate, abroad_rate, \
                    employers, industries, regions, schools = row

                school = db.query(School).filter(School.slug == slug).first()
                if not school:
                    continue

                # 查找或创建报告（每校每年一份，受 uq_school_year 约束）
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

                # 检查就业数据是否已存在（避免重复）
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
                    startup_rate=0.0,
                    gap_year_rate=0.0,
                    employer_ranking=employers,
                    industry_distribution=industries,
                    destination_region=regions,
                    school_for_further_study=schools,
                )
                db.add(emp)
                db.commit()

        print(f"种子数据导入完成")
        # 统计
        from sqlalchemy import func
        sc = db.query(School).count()
        rc = db.query(ReportRecord).filter(ReportRecord.parse_status == ParseStatus.published).count()
        ec = db.query(EmploymentData).count()
        print(f"学校: {sc}, 已发布报告: {rc}, 就业数据记录: {ec}")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
