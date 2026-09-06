# backend/app/seed/run_all_seeds.py
"""运行真实种子数据脚本。

使用方法：
    cd backend
    python -m app.seed.run_all_seeds

数据合规说明：
- 薪资基准种子已改为导入真实调研数据（salary_real.json / salary_expand.json），
  不再生成推导假数据（原 kaggle 标榜实为推导的版本已摘除）。
- 演示种子（考研情报/暗知识、分数线）已删除，不再提供 --include-demo 注入路径。
- 社区讨论种子（seed_community，8 个假用户+编造讨论帖）已于 2026-09-05 移除并删除：
  社区只允许用户自己发布的内容，禁止任何脚本灌入非用户内容（用户拍板）。
- 考公岗位情报种子（seed_civil_service_intel，43 条手编竞争比/进面分/薪资）
  已于 2026-09-05 移除并生产清零（用户拍板"可"）：编造统计数据与 581 假进面线
  同性质。考公暗知识种子（编辑性内容）保留。
  真实数据一律走导入管道 + 人工确认入库。
"""

from uuid import UUID

from app.database import SessionLocal
from app.models.user import User
from app.seed.seed_civil_service import seed_civil_service_dark_knowledge
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

        # 考公暗知识
        print("\n2. 注入考公暗知识...")
        n = seed_civil_service_dark_knowledge(db)
        print(f"   ✓ 新增 {n} 条暗知识")

        # 公司数据
        print("\n3. 注入公司数据...")
        n = seed_companies(db)
        print(f"   ✓ 新增 {n} 家公司")

        # 薪资基准（真实调研数据）
        print("\n4. 注入薪资基准（真实调研数据）...")
        n = seed_salary_benchmarks(db)
        print(f"   ✓ 新增 {n} 条薪资记录")

        # 市场数据
        print("\n5. 注入市场数据...")
        n = seed_market_data(db)
        print(f"   ✓ 新增 {n} 条市场数据")

        # 知识库
        print("\n6. 注入知识库...")
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
