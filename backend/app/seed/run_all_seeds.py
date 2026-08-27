# backend/app/seed/run_all_seeds.py
"""运行真实种子数据脚本。

使用方法：
    cd backend
    python -m app.seed.run_all_seeds

数据合规说明：
- 薪资基准种子已改为导入真实调研数据（salary_real.json / salary_expand.json），
  不再生成推导假数据（原 kaggle 标榜实为推导的版本已摘除）。
- 演示种子（考研情报/暗知识、考研社区、生成的社区内容、分数线）已删除，
  不再提供 --include-demo 注入路径；真实数据一律走导入管道 + 人工确认入库。
"""

from uuid import UUID

from app.database import SessionLocal
from app.models.user import User
from app.seed.seed_civil_service import seed_civil_service_dark_knowledge, seed_civil_service_intel
from app.seed.seed_community import seed_community
from app.seed.seed_companies import seed_companies
from app.seed.seed_knowledge import seed_knowledge
from app.seed.seed_market_data import seed_market_data
from app.seed.seed_salary_benchmarks import seed_salary_benchmarks
from app.seed.seed_schools import seed_schools

# 系统用户 UUID（用于无用户关联的种子数据）
SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


def create_system_user(db):
    """创建系统用户（如果不存在）。"""
    user = db.query(User).filter(User.id == SYSTEM_USER_ID).first()
    if not user:
        user = User(
            id=SYSTEM_USER_ID,
            email="system@gradpath.local",
            name="系统",
            password_hash="",  # 系统用户不登录
        )
        db.add(user)
        db.commit()
        print("   ✓ 创建系统用户")
    return user


def run_all_seeds():
    """运行所有真实种子数据脚本。"""
    db = SessionLocal()
    try:
        print("开始注入种子数据...")

        # 创建系统用户
        print("\n0. 创建系统用户...")
        create_system_user(db)

        # 院校数据
        print("\n1. 注入院校数据...")
        n = seed_schools(db)
        print(f"   ✓ 新增 {n} 所院校")

        # 考公情报
        print("\n2. 注入考公情报...")
        n = seed_civil_service_intel(db)
        print(f"   ✓ 新增 {n} 条考公情报")

        # 考公暗知识
        print("\n3. 注入考公暗知识...")
        n = seed_civil_service_dark_knowledge(db)
        print(f"   ✓ 新增 {n} 条暗知识")

        # 社区讨论
        print("\n4. 注入社区讨论...")
        n = seed_community(db)
        print(f"   ✓ 新增 {n} 条讨论帖")

        # 公司数据
        print("\n5. 注入公司数据...")
        n = seed_companies(db)
        print(f"   ✓ 新增 {n} 家公司")

        # 薪资基准（真实调研数据）
        print("\n6. 注入薪资基准（真实调研数据）...")
        n = seed_salary_benchmarks(db)
        print(f"   ✓ 新增 {n} 条薪资记录")

        # 市场数据
        print("\n7. 注入市场数据...")
        n = seed_market_data(db)
        print(f"   ✓ 新增 {n} 条市场数据")

        # 知识库
        print("\n8. 注入知识库...")
        n = seed_knowledge(db)
        print(f"   ✓ 新增 {n} 条知识条目")

        print("\n" + "=" * 50)
        print("所有种子数据注入完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_all_seeds()
