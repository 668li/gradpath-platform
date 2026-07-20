"""初始化新模块的数据库表"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal, Base
from app.models.study_plan import StudyPlan
from app.models.learning_resource import LearningResource
from sqlalchemy import inspect

def check_and_create_tables():
    """检查并创建新表"""
    # 先创建所有表
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表已创建/更新")
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print(f"\n现有表数量: {len(existing_tables)}")
    
    # 插入测试数据
    db = SessionLocal()
    try:
        # 检查是否已有数据
        study_plan_count = db.query(StudyPlan).count()
        learning_resource_count = db.query(LearningResource).count()
        
        print(f"\n现有数据: {study_plan_count} 个学习计划, {learning_resource_count} 个学习资源")
        
        if study_plan_count == 0:
            print("\n插入测试学习计划...")
            test_plan = StudyPlan(
                user_id="00000000-0000-0000-0000-000000000001",
                title="408 计算机综合复习计划",
                start_date="2026-07-01",
                end_date="2026-12-25",
                subjects=["数据结构", "计算机组成原理", "操作系统", "计算机网络"],
                completed=False,
                progress=0
            )
            db.add(test_plan)
            db.commit()
            print("✓ 测试学习计划已插入")
        
        if learning_resource_count == 0:
            print("\n插入测试学习资源...")
            test_resources = [
                LearningResource(
                    user_id="00000000-0000-0000-0000-000000000001",
                    title="王道考研 408 全套视频",
                    url="https://example.com/wangdao",
                    resource_type="video",
                    subject="408",
                    difficulty="intermediate",
                    description="王道考研 408 计算机综合全套视频课程",
                    tags=["408", "王道", "考研"],
                    rating=5,
                    is_free=False,
                    view_count=1250
                ),
                LearningResource(
                    user_id="00000000-0000-0000-0000-000000000001",
                    title="数据结构考研复习指南",
                    url="https://example.com/ds-guide",
                    resource_type="article",
                    subject="数据结构",
                    difficulty="beginner",
                    description="数据结构考研复习入门指南",
                    tags=["数据结构", "考研", "入门"],
                    rating=4,
                    is_free=True,
                    view_count=856
                ),
            ]
            db.add_all(test_resources)
            db.commit()
            print("✓ 测试学习资源已插入")
        
        # 验证数据
        print(f"\n最终数据: {db.query(StudyPlan).count()} 个学习计划, {db.query(LearningResource).count()} 个学习资源")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    check_and_create_tables()
