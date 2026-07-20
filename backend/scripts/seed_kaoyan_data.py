"""种子脚本：初始化研招网真实考研数据。

填充三张新表：
- grad_yanzhao_programs（研招网专业目录）
- grad_scoreline_records（院校复试分数线）
- grad_adjustment_info（调剂信息）

使用方法：
    cd backend
    python scripts/seed_kaoyan_data.py
"""
import sys
from pathlib import Path

# 添加 backend 到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.crawlers.grad.adjustment_crawler import AdjustmentCrawler
from app.crawlers.grad.scoreline_real_crawler import ScorelineRealCrawler
from app.crawlers.grad.yanzhao_crawler import YanzhaoProgramCrawler
from app.database import Base, SessionLocal, engine


def create_tables() -> None:
    """创建数据库表（基于 SQLAlchemy Base 元数据）。"""
    print("创建/检查数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表准备完成")


def seed_yanzhao_programs(db) -> int:
    """填充研招网专业目录数据。"""
    crawler = YanzhaoProgramCrawler()
    result = crawler.run(db)
    return result.get("stored", 0)


def seed_scoreline_records(db) -> int:
    """填充院校复试分数线数据。"""
    crawler = ScorelineRealCrawler()
    result = crawler.run(db)
    return result.get("stored", 0)


def seed_adjustment_info(db) -> int:
    """填充调剂信息数据。"""
    crawler = AdjustmentCrawler()
    result = crawler.run(db)
    return result.get("stored", 0)


def main() -> None:
    """主函数：运行所有考研真实数据种子脚本。"""
    print("=" * 60)
    print("研招网真实考研数据初始化脚本")
    print("=" * 60)

    create_tables()

    db = SessionLocal()
    try:
        print("\n1. 导入研招网专业目录...")
        n_programs = seed_yanzhao_programs(db)
        print(f"   ✓ 新增/更新 {n_programs} 条专业目录记录")

        print("\n2. 导入院校复试分数线...")
        n_scorelines = seed_scoreline_records(db)
        print(f"   ✓ 新增/更新 {n_scorelines} 条分数线记录")

        print("\n3. 导入调剂信息...")
        n_adjustments = seed_adjustment_info(db)
        print(f"   ✓ 新增/更新 {n_adjustments} 条调剂记录")

        print("\n" + "=" * 60)
        print("✓ 研招网真实考研数据初始化完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 数据初始化失败：{e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
