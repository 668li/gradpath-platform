# backend/pipeline/seed_community.py
"""社区报告种子数据脚本。

为 10 所高校创建约 40 条社区毕业去向报告，每条关联到一名种子用户。
种子用户邮箱：community_seed_1@test.com ~ community_seed_10@test.com
统一密码：Test1234!

注意：由于 CommunityReport 的唯一约束为 (user_id, graduation_year)，
每个用户的报告必须使用不同的毕业年份。
"""
from sqlalchemy import func

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.community_report import CommunityReport, DestinationType, SalaryRange
from app.models.employment_data import Degree
from app.models.user import User

SEED_PASSWORD = "Test1234!"

# 每个种子用户及其提交的社区报告列表
# 关键约束：同一用户内 graduation_year 不可重复
SEED_DATA = [
    # ---- 用户1: 清华大学 (4条, 年份 2021-2024) ----
    {
        "email": "community_seed_1@test.com",
        "name": "社区用户1",
        "reports": [
            {"school_name": "清华大学", "major": "计算机科学与技术", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "字节跳动", "city": "北京", "industry": "互联网",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "清华大学", "major": "电子工程", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "华为", "city": "深圳", "industry": "通讯",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "清华大学", "major": "机械工程", "graduation_year": 2022,
             "degree": Degree.master, "destination_type": DestinationType.employment,
             "employer": "三一重工", "city": "北京", "industry": "制造业",
             "salary_range": SalaryRange.r15k_25k},
            {"school_name": "清华大学", "major": "计算机科学与技术", "graduation_year": 2021,
             "degree": Degree.bachelor, "destination_type": DestinationType.further_study,
             "employer": None, "city": None, "industry": None, "salary_range": None},
        ],
    },
    # ---- 用户2: 北京大学 (5条, 年份 2020-2024) ----
    {
        "email": "community_seed_2@test.com",
        "name": "社区用户2",
        "reports": [
            {"school_name": "北京大学", "major": "计算机科学与技术", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "百度", "city": "北京", "industry": "互联网",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "北京大学", "major": "金融学", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "中金公司", "city": "北京", "industry": "金融",
             "salary_range": SalaryRange.above_50k},
            {"school_name": "北京大学", "major": "法学", "graduation_year": 2022,
             "degree": Degree.bachelor, "destination_type": DestinationType.civil_service,
             "employer": "最高人民法院", "city": "北京", "industry": "法律",
             "salary_range": SalaryRange.r15k_25k},
            {"school_name": "北京大学", "major": "计算机科学与技术", "graduation_year": 2021,
             "degree": Degree.master, "destination_type": DestinationType.abroad,
             "employer": "Google", "city": None, "industry": None, "salary_range": None},
            {"school_name": "北京大学", "major": "金融学", "graduation_year": 2020,
             "degree": Degree.bachelor, "destination_type": DestinationType.further_study,
             "employer": None, "city": None, "industry": None, "salary_range": None},
        ],
    },
    # ---- 用户3: 浙江大学 (3条, 年份 2022-2024) ----
    {
        "email": "community_seed_3@test.com",
        "name": "社区用户3",
        "reports": [
            {"school_name": "浙江大学", "major": "计算机科学与技术", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "阿里巴巴", "city": "杭州", "industry": "互联网",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "浙江大学", "major": "机械工程", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "吉利汽车", "city": "杭州", "industry": "制造业",
             "salary_range": SalaryRange.r15k_25k},
            {"school_name": "浙江大学", "major": "化学", "graduation_year": 2022,
             "degree": Degree.bachelor, "destination_type": DestinationType.further_study,
             "employer": None, "city": None, "industry": None, "salary_range": None},
        ],
    },
    # ---- 用户4: 上海交通大学 (4条, 年份 2021-2024) ----
    {
        "email": "community_seed_4@test.com",
        "name": "社区用户4",
        "reports": [
            {"school_name": "上海交通大学", "major": "计算机科学与技术", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "字节跳动", "city": "上海", "industry": "互联网",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "上海交通大学", "major": "电子信息", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "华为", "city": "上海", "industry": "通讯",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "上海交通大学", "major": "船舶与海洋工程", "graduation_year": 2022,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "中船集团", "city": "上海", "industry": "制造业",
             "salary_range": SalaryRange.r8k_15k},
            {"school_name": "上海交通大学", "major": "机械工程", "graduation_year": 2021,
             "degree": Degree.master, "destination_type": DestinationType.employment,
             "employer": "上汽集团", "city": "上海", "industry": "制造业",
             "salary_range": SalaryRange.r15k_25k},
        ],
    },
    # ---- 用户5: 复旦大学 (3条, 年份 2022-2024) ----
    {
        "email": "community_seed_5@test.com",
        "name": "社区用户5",
        "reports": [
            {"school_name": "复旦大学", "major": "金融学", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "中信证券", "city": "上海", "industry": "金融",
             "salary_range": SalaryRange.above_50k},
            {"school_name": "复旦大学", "major": "新闻学", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "新华社", "city": "北京", "industry": "媒体",
             "salary_range": SalaryRange.r8k_15k},
            {"school_name": "复旦大学", "major": "数学", "graduation_year": 2022,
             "degree": Degree.bachelor, "destination_type": DestinationType.further_study,
             "employer": None, "city": None, "industry": None, "salary_range": None},
        ],
    },
    # ---- 用户6: 中国科学技术大学 (5条, 年份 2020-2024) ----
    {
        "email": "community_seed_6@test.com",
        "name": "社区用户6",
        "reports": [
            {"school_name": "中国科学技术大学", "major": "物理学", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.further_study,
             "employer": None, "city": None, "industry": None, "salary_range": None},
            {"school_name": "中国科学技术大学", "major": "化学", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.further_study,
             "employer": None, "city": None, "industry": None, "salary_range": None},
            {"school_name": "中国科学技术大学", "major": "计算机科学", "graduation_year": 2022,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "华为", "city": "合肥", "industry": "互联网",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "中国科学技术大学", "major": "数学", "graduation_year": 2021,
             "degree": Degree.bachelor, "destination_type": DestinationType.abroad,
             "employer": "MIT", "city": None, "industry": None, "salary_range": None},
            {"school_name": "中国科学技术大学", "major": "物理学", "graduation_year": 2020,
             "degree": Degree.master, "destination_type": DestinationType.employment,
             "employer": "中科院物理所", "city": "北京", "industry": "科研",
             "salary_range": SalaryRange.r15k_25k},
        ],
    },
    # ---- 用户7: 南京大学 (3条, 年份 2022-2024) ----
    {
        "email": "community_seed_7@test.com",
        "name": "社区用户7",
        "reports": [
            {"school_name": "南京大学", "major": "计算机科学与技术", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "华为", "city": "南京", "industry": "互联网",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "南京大学", "major": "汉语言文学", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.civil_service,
             "employer": "江苏广电", "city": "南京", "industry": "媒体",
             "salary_range": SalaryRange.r8k_15k},
            {"school_name": "南京大学", "major": "物理学", "graduation_year": 2022,
             "degree": Degree.bachelor, "destination_type": DestinationType.further_study,
             "employer": None, "city": None, "industry": None, "salary_range": None},
        ],
    },
    # ---- 用户8: 武汉大学 (4条, 年份 2021-2024) ----
    {
        "email": "community_seed_8@test.com",
        "name": "社区用户8",
        "reports": [
            {"school_name": "武汉大学", "major": "计算机科学与技术", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "字节跳动", "city": "武汉", "industry": "互联网",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "武汉大学", "major": "法学", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "君合律所", "city": "北京", "industry": "法律",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "武汉大学", "major": "测绘工程", "graduation_year": 2022,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "中铁集团", "city": "武汉", "industry": "建筑",
             "salary_range": SalaryRange.r15k_25k},
            {"school_name": "武汉大学", "major": "遥感科学与技术", "graduation_year": 2021,
             "degree": Degree.bachelor, "destination_type": DestinationType.further_study,
             "employer": None, "city": None, "industry": None, "salary_range": None},
        ],
    },
    # ---- 用户9: 华中科技大学 (4条, 年份 2021-2024) ----
    {
        "email": "community_seed_9@test.com",
        "name": "社区用户9",
        "reports": [
            {"school_name": "华中科技大学", "major": "计算机科学与技术", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "腾讯", "city": "深圳", "industry": "互联网",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "华中科技大学", "major": "光电信息科学与工程", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "华为", "city": "武汉", "industry": "光电",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "华中科技大学", "major": "机械工程", "graduation_year": 2022,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "三一重工", "city": "武汉", "industry": "制造业",
             "salary_range": SalaryRange.r15k_25k},
            {"school_name": "华中科技大学", "major": "临床医学", "graduation_year": 2021,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "同济医院", "city": "武汉", "industry": "医疗",
             "salary_range": SalaryRange.r15k_25k},
        ],
    },
    # ---- 用户10: 中山大学 (5条, 年份 2020-2024) ----
    {
        "email": "community_seed_10@test.com",
        "name": "社区用户10",
        "reports": [
            {"school_name": "中山大学", "major": "计算机科学与技术", "graduation_year": 2024,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "腾讯", "city": "深圳", "industry": "互联网",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "中山大学", "major": "临床医学", "graduation_year": 2023,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "中山一院", "city": "广州", "industry": "医疗",
             "salary_range": SalaryRange.r15k_25k},
            {"school_name": "中山大学", "major": "工商管理", "graduation_year": 2022,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "毕马威", "city": "广州", "industry": "咨询",
             "salary_range": SalaryRange.r25k_50k},
            {"school_name": "中山大学", "major": "生物学", "graduation_year": 2021,
             "degree": Degree.bachelor, "destination_type": DestinationType.further_study,
             "employer": None, "city": None, "industry": None, "salary_range": None},
            {"school_name": "中山大学", "major": "口腔医学", "graduation_year": 2020,
             "degree": Degree.bachelor, "destination_type": DestinationType.employment,
             "employer": "中大光华口腔", "city": "广州", "industry": "医疗",
             "salary_range": SalaryRange.r25k_50k},
        ],
    },
]


def run_seed():
    """执行种子数据导入。

    幂等：先清理旧种子数据，再重新导入。
    """
    db = SessionLocal()
    try:
        # ---- 清理旧种子数据 ----
        seed_users = (
            db.query(User)
            .filter(User.email.like("community_seed_%@test.com"))
            .all()
        )
        for user in seed_users:
            db.query(CommunityReport).filter(
                CommunityReport.user_id == user.id
            ).delete()
            db.delete(user)
        db.commit()

        # ---- 重新导入 ----
        total_reports = 0
        for user_data in SEED_DATA:
            user = User(
                email=user_data["email"],
                password_hash=hash_password(SEED_PASSWORD),
                name=user_data["name"],
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            for report_data in user_data["reports"]:
                report = CommunityReport(user_id=user.id, **report_data)
                db.add(report)
                db.commit()
                total_reports += 1

        print("社区报告种子数据导入完成")
        # 统计

        user_count = (
            db.query(User)
            .filter(User.email.like("community_seed_%@test.com"))
            .count()
        )
        report_count = db.query(CommunityReport).count()
        school_count = (
            db.query(func.count(func.distinct(CommunityReport.school_name)))
            .scalar()
            or 0
        )
        major_count = (
            db.query(func.count(func.distinct(CommunityReport.major))).scalar() or 0
        )
        print(
            f"种子用户: {user_count}, 社区报告: {report_count}, "
            f"覆盖学校: {school_count}, 覆盖专业: {major_count}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
