"""种子脚本：初始化导师和评价数据"""
import sys
from pathlib import Path

# 添加 backend 到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.mentor import Mentor
from app.models.mentor_review import MentorReview
from uuid import uuid4
from datetime import datetime


def create_tables():
    """创建数据库表"""
    print("创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表创建完成")


def seed_mentors(db: Session):
    """导入导师数据"""
    print("\n导入导师数据...")
    
    # 检查是否已有数据
    existing_count = db.query(Mentor).count()
    if existing_count > 0:
        print(f"✓ 已存在 {existing_count} 位导师，跳过导入")
        return
    
    # 从爬虫模块导入数据
    from app.crawlers.grad.mentor_crawler import _MENTOR_DATA
    
    mentors_created = 0
    for data in _MENTOR_DATA:
        (name, university, department, title, research_directions,
         paper_count, project_count, citation_count, h_index,
         enrollment_status, enrollment_directions, contact_email, tags) = data
        
        mentor = Mentor(
            id=uuid4(),
            name=name,
            university=university,
            department=department,
            title=title,
            research_directions=research_directions,
            paper_count=paper_count,
            project_count=project_count,
            citation_count=citation_count,
            h_index=h_index,
            enrollment_status=enrollment_status,
            enrollment_directions=enrollment_directions,
            contact_email=contact_email,
            tags=tags,
            avg_rating=0.0,
            review_count=0,
            rating_academic=0.0,
            rating_guidance=0.0,
            rating_relationship=0.0,
            rating_funding=0.0,
            rating_workload=0.0,
            rating_career=0.0,
            source_platform="official",
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(mentor)
        mentors_created += 1
    
    db.commit()
    print(f"✓ 成功导入 {mentors_created} 位导师")


def seed_reviews(db: Session):
    """导入评价数据"""
    print("\n导入评价数据...")
    
    # 检查是否已有数据
    existing_count = db.query(MentorReview).count()
    if existing_count > 0:
        print(f"✓ 已存在 {existing_count} 条评价，跳过导入")
        return
    
    # 从聚合器模块导入数据
    from app.crawlers.grad.mentor_review_aggregator import _MENTOR_REVIEW_DATA
    
    reviews_created = 0
    for data in _MENTOR_REVIEW_DATA:
        (mentor_name, university, department, reviewer_identity, is_anonymous,
         rating_academic, rating_guidance, rating_relationship,
         rating_funding, rating_workload, rating_career,
         title, content, pros, cons, like_count) = data
        
        # 查找对应的导师
        mentor = db.query(Mentor).filter(
            Mentor.name == mentor_name,
            Mentor.university == university,
            Mentor.department == department
        ).first()
        
        if not mentor:
            print(f"⚠ 未找到导师：{mentor_name} ({university} {department})，跳过")
            continue
        
        # 计算综合评分
        overall_rating = (
            rating_academic + rating_guidance + rating_relationship +
            rating_funding + rating_workload + rating_career
        ) / 6
        
        review = MentorReview(
            id=uuid4(),
            mentor_id=mentor.id,
            user_id=uuid4(),  # 虚拟用户ID
            is_anonymous=is_anonymous,
            anonymous_id=reviewer_identity if is_anonymous else None,
            rating_academic=rating_academic,
            rating_guidance=rating_guidance,
            rating_relationship=rating_relationship,
            rating_funding=rating_funding,
            rating_workload=rating_workload,
            rating_career=rating_career,
            overall_rating=overall_rating,
            title=title,
            content=content,
            pros=pros,
            cons=cons,
            review_status="approved",
            like_count=like_count,
            submitted_at=datetime.utcnow().isoformat(),
            reviewer_identity=reviewer_identity,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(review)
        reviews_created += 1
    
    db.commit()
    print(f"✓ 成功导入 {reviews_created} 条评价")


def update_mentor_stats(db: Session):
    """更新导师评分统计"""
    print("\n更新导师评分统计...")
    
    mentors = db.query(Mentor).all()
    updated_count = 0
    
    for mentor in mentors:
        reviews = db.query(MentorReview).filter(
            MentorReview.mentor_id == mentor.id,
            MentorReview.review_status == "approved"
        ).all()
        
        if reviews:
            mentor.review_count = len(reviews)
            mentor.avg_rating = sum(r.overall_rating for r in reviews) / len(reviews)
            mentor.rating_academic = sum(r.rating_academic for r in reviews) / len(reviews)
            mentor.rating_guidance = sum(r.rating_guidance for r in reviews) / len(reviews)
            mentor.rating_relationship = sum(r.rating_relationship for r in reviews) / len(reviews)
            mentor.rating_funding = sum(r.rating_funding for r in reviews) / len(reviews)
            mentor.rating_workload = sum(r.rating_workload for r in reviews) / len(reviews)
            mentor.rating_career = sum(r.rating_career for r in reviews) / len(reviews)
            updated_count += 1
    
    db.commit()
    print(f"✓ 更新了 {updated_count} 位导师的评分统计")


def main():
    """主函数"""
    print("=" * 60)
    print("考研导师数据初始化脚本")
    print("=" * 60)
    
    # 创建数据库表
    create_tables()
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 导入导师数据
        seed_mentors(db)
        
        # 导入评价数据
        seed_reviews(db)
        
        # 更新导师评分统计
        update_mentor_stats(db)
        
        print("\n" + "=" * 60)
        print("✓ 数据初始化完成！")
        print("=" * 60)
        
        # 打印统计信息
        mentor_count = db.query(Mentor).count()
        review_count = db.query(MentorReview).count()
        print(f"\n统计信息：")
        print(f"  - 导师数量：{mentor_count}")
        print(f"  - 评价数量：{review_count}")
        
    except Exception as e:
        print(f"\n✗ 数据初始化失败：{e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
