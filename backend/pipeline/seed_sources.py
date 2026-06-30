# backend/pipeline/seed_sources.py
"""数据源种子数据脚本。"""
from app.database import SessionLocal
from app.models.data_source import DataSource
from app.models.user import User
from app.core.security import hash_password


SEED_SOURCES = [
    {
        "name": "教育部高校毕业生就业统计（示例）",
        "source_type": "api",
        "api_url": "https://api.example.edu.gov.cn/employment/stats",
        "api_key": "demo-key-001",
        "data_mapping": {
            "majors_path": "data.majors",
            "field_map": {
                "major_name": "name",
                "employment_rate": "employment",
                "further_study_rate": "further_study",
            },
        },
        "is_active": False,
    },
    {
        "name": "麦可思就业数据（示例）",
        "source_type": "api",
        "api_url": "https://api.mycos.example.com/v1/reports",
        "api_key": "demo-key-002",
        "data_mapping": {
            "majors_path": "result.list",
            "field_map": {
                "major_name": "major",
                "employment_rate": "emp_rate",
            },
        },
        "is_active": False,
    },
]


def run_seed():
    """执行种子数据导入。幂等：先清理旧种子数据，再重新导入。"""
    db = SessionLocal()
    try:
        # 清理旧数据源
        db.query(DataSource).delete()

        # 导入数据源
        for src in SEED_SOURCES:
            db.add(DataSource(**src))

        # 确保 test@test.com 用户是管理员
        admin_user = db.query(User).filter(User.email == "test@test.com").first()
        if admin_user:
            admin_user.is_admin = True

        db.commit()
        print(f"已导入 {len(SEED_SOURCES)} 个数据源配置")
        if admin_user:
            print("已将 test@test.com 设为管理员")
        else:
            print("提示: 未找到 test@test.com 用户，跳过管理员设置")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
