# backend/pipeline/seed_interview.py
"""面试经验种子数据脚本。

为 10 家公司创建约 40 条面试经验报告。
复用 Phase 3 的社区种子用户（community_seed_1~10@test.com）。
统一密码：Test1234!

注意：InterviewReport 的唯一约束为 (user_id, company, position, interview_year)，
同一用户对同一公司同岗位同年只能有一条记录。
"""
from sqlalchemy import func

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.interview_report import (
    InterviewDimension,
    InterviewReport,
    InterviewResult,
)
from app.models.user import User

SEED_PASSWORD = "Test1234!"

# 每个种子用户及其提交的面试报告列表
SEED_DATA = [
    # ---- 用户1: 腾讯 (4条) ----
    {
        "email": "interview_seed_1@test.com",
        "name": "面试用户1",
        "reports": [
            {"company": "腾讯", "position": "后端开发", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design", "project_depth"], "difficulty": 4,
             "summary": "三轮技术面，算法题中等难度，系统设计考了短链接"},
            {"company": "腾讯", "position": "前端开发", "interview_year": 2023, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "project_depth", "communication"], "difficulty": 3,
             "summary": "前端框架原理问得多，有手写代码环节"},
            {"company": "字节跳动", "position": "后端开发", "interview_year": 2024, "city": "北京",
             "rounds": 4, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "system_design"], "difficulty": 5,
             "summary": "算法题偏难，第四轮挂了"},
            {"company": "阿里巴巴", "position": "数据分析", "interview_year": 2022, "city": "杭州",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["project_depth", "communication", "behavior"], "difficulty": 3,
             "summary": "偏业务理解，有案例分析环节"},
        ],
    },
    # ---- 用户2: 字节跳动 (4条) ----
    {
        "email": "interview_seed_2@test.com",
        "name": "面试用户2",
        "reports": [
            {"company": "字节跳动", "position": "后端开发", "interview_year": 2024, "city": "北京",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design", "project_depth"], "difficulty": 5,
             "summary": "算法题难度高，系统设计考了Feed流"},
            {"company": "字节跳动", "position": "客户端开发", "interview_year": 2023, "city": "北京",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "project_depth", "domain"], "difficulty": 4,
             "summary": "客户端性能优化问得多"},
            {"company": "腾讯", "position": "后端开发", "interview_year": 2022, "city": "深圳",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "system_design"], "difficulty": 4,
             "summary": "二面系统设计没答好"},
            {"company": "百度", "position": "算法工程师", "interview_year": 2024, "city": "北京",
             "rounds": 4, "result": InterviewResult.pending,
             "dimensions": ["algorithm", "domain", "project_depth"], "difficulty": 4,
             "summary": "NLP方向，问了Transformer原理"},
        ],
    },
    # ---- 用户3: 阿里巴巴 (3条) ----
    {
        "email": "interview_seed_3@test.com",
        "name": "面试用户3",
        "reports": [
            {"company": "阿里巴巴", "position": "后端开发", "interview_year": 2024, "city": "杭州",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["system_design", "project_depth", "culture_fit"], "difficulty": 4,
             "summary": "系统设计考了电商秒杀，有HR文化面"},
            {"company": "阿里巴巴", "position": "数据分析", "interview_year": 2023, "city": "杭州",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["project_depth", "communication"], "difficulty": 3,
             "summary": "业务案例不够深入"},
            {"company": "字节跳动", "position": "后端开发", "interview_year": 2022, "city": "北京",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design"], "difficulty": 5,
             "summary": "算法考了动态规划"},
        ],
    },
    # ---- 用户4: 华为 (4条) ----
    {
        "email": "interview_seed_4@test.com",
        "name": "面试用户4",
        "reports": [
            {"company": "华为", "position": "硬件工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth", "culture_fit"], "difficulty": 3,
             "summary": "专业知识问得细，有上机测试"},
            {"company": "华为", "position": "算法工程师", "interview_year": 2023, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "domain", "project_depth"], "difficulty": 4,
             "summary": "CV方向，问了目标检测算法"},
            {"company": "大疆", "position": "算法工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "project_depth"], "difficulty": 4,
             "summary": "二面项目深挖没答好"},
            {"company": "腾讯", "position": "后端开发", "interview_year": 2022, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design"], "difficulty": 4,
             "summary": "常规后端面试"},
        ],
    },
    # ---- 用户5: 中金公司 (3条) ----
    {
        "email": "interview_seed_5@test.com",
        "name": "面试用户5",
        "reports": [
            {"company": "中金公司", "position": "投行分析师", "interview_year": 2024, "city": "北京",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "communication", "behavior"], "difficulty": 4,
             "summary": "财务建模+行为面试，英文面占比较大"},
            {"company": "中金公司", "position": "研究员", "interview_year": 2023, "city": "北京",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["domain", "communication"], "difficulty": 4,
             "summary": "行业研究深度不够"},
            {"company": "中信证券", "position": "研究员", "interview_year": 2024, "city": "北京",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["domain", "behavior", "communication"], "difficulty": 3,
             "summary": "面试相对常规，偏行业理解"},
        ],
    },
    # ---- 用户6: 百度 (4条) ----
    {
        "email": "interview_seed_6@test.com",
        "name": "面试用户6",
        "reports": [
            {"company": "百度", "position": "算法工程师", "interview_year": 2024, "city": "北京",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design", "domain"], "difficulty": 4,
             "summary": "推荐系统方向，考了召回排序"},
            {"company": "百度", "position": "后端开发", "interview_year": 2023, "city": "北京",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "system_design"], "difficulty": 4,
             "summary": "系统设计没答好"},
            {"company": "字节跳动", "position": "算法工程师", "interview_year": 2022, "city": "北京",
             "rounds": 4, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "domain", "project_depth"], "difficulty": 5,
             "summary": "NLP方向，考了BERT"},
            {"company": "腾讯", "position": "算法工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.pending,
             "dimensions": ["algorithm", "domain"], "difficulty": 4,
             "summary": "还在等结果"},
        ],
    },
    # ---- 用户7: 三一重工 (3条) ----
    {
        "email": "interview_seed_7@test.com",
        "name": "面试用户7",
        "reports": [
            {"company": "三一重工", "position": "机械工程师", "interview_year": 2024, "city": "长沙",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth", "culture_fit"], "difficulty": 2,
             "summary": "偏专业知识，面试氛围友好"},
            {"company": "三一重工", "position": "项目经理", "interview_year": 2023, "city": "长沙",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["project_depth", "communication", "behavior"], "difficulty": 3,
             "summary": "项目管理案例面试"},
            {"company": "比亚迪", "position": "电池工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["domain", "culture_fit"], "difficulty": 2,
             "summary": "专业面+HR面，比较顺利"},
        ],
    },
    # ---- 用户8: 比亚迪 (3条) ----
    {
        "email": "interview_seed_8@test.com",
        "name": "面试用户8",
        "reports": [
            {"company": "比亚迪", "position": "嵌入式工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 2, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth", "culture_fit"], "difficulty": 3,
             "summary": "嵌入式基础+项目经验"},
            {"company": "比亚迪", "position": "电池工程师", "interview_year": 2023, "city": "深圳",
             "rounds": 2, "result": InterviewResult.rejected,
             "dimensions": ["domain"], "difficulty": 3,
             "summary": "专业知识不够深"},
            {"company": "华为", "position": "硬件工程师", "interview_year": 2022, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth"], "difficulty": 3,
             "summary": "硬件基础+电路设计"},
        ],
    },
    # ---- 用户9: 大疆 (4条) ----
    {
        "email": "interview_seed_9@test.com",
        "name": "面试用户9",
        "reports": [
            {"company": "大疆", "position": "算法工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "project_depth", "domain"], "difficulty": 4,
             "summary": "视觉算法方向，考了SLAM"},
            {"company": "大疆", "position": "嵌入式工程师", "interview_year": 2023, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "project_depth", "algorithm"], "difficulty": 4,
             "summary": "C++底层+RTOS"},
            {"company": "华为", "position": "算法工程师", "interview_year": 2024, "city": "深圳",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["algorithm", "domain"], "difficulty": 4,
             "summary": "一面算法没做好"},
            {"company": "腾讯", "position": "算法工程师", "interview_year": 2022, "city": "深圳",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "system_design"], "difficulty": 4,
             "summary": "推荐系统方向"},
        ],
    },
    # ---- 用户10: 中信证券 (4条) ----
    {
        "email": "interview_seed_10@test.com",
        "name": "面试用户10",
        "reports": [
            {"company": "中信证券", "position": "研究员", "interview_year": 2024, "city": "北京",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["domain", "communication", "behavior"], "difficulty": 4,
             "summary": "行业研究+财务分析"},
            {"company": "中信证券", "position": "投行", "interview_year": 2023, "city": "北京",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["domain", "behavior"], "difficulty": 4,
             "summary": "估值建模环节不够熟练"},
            {"company": "中金公司", "position": "投行分析师", "interview_year": 2022, "city": "北京",
             "rounds": 3, "result": InterviewResult.rejected,
             "dimensions": ["domain", "communication", "behavior"], "difficulty": 5,
             "summary": "全英文面试，准备不充分"},
            {"company": "百度", "position": "数据分析", "interview_year": 2024, "city": "北京",
             "rounds": 3, "result": InterviewResult.offer,
             "dimensions": ["algorithm", "project_depth", "communication"], "difficulty": 3,
             "summary": "SQL+业务理解"},
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
            .filter(User.email.like("interview_seed_%@test.com"))
            .all()
        )
        for user in seed_users:
            db.query(InterviewReport).filter(
                InterviewReport.user_id == user.id
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
                report = InterviewReport(user_id=user.id, **report_data)
                db.add(report)
                db.commit()
                total_reports += 1

        print("面试经验种子数据导入完成")

        user_count = (
            db.query(User)
            .filter(User.email.like("interview_seed_%@test.com"))
            .count()
        )
        report_count = db.query(InterviewReport).count()
        company_count = (
            db.query(func.count(func.distinct(InterviewReport.company)))
            .scalar()
            or 0
        )
        position_count = (
            db.query(func.count(func.distinct(InterviewReport.position)))
            .scalar()
            or 0
        )
        print(
            f"种子用户: {user_count}, 面试报告: {report_count}, "
            f"覆盖公司: {company_count}, 覆盖岗位: {position_count}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
