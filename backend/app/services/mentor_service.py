"""导师服务层 - 处理导师相关业务逻辑"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.models.mentor import Mentor
from app.models.mentor_review import MentorReview
from app.schemas.mentor import MentorCreate, MentorUpdate, MentorReviewCreate


def _atomic_increment(
    db: Session, model_cls, item_id: UUID, column: str, delta: int = 1
) -> bool:
    """原子 UPDATE — 避免 read-modify-write 在高并发下丢失更新。"""
    col = getattr(model_cls, column)
    rows = (
        db.query(model_cls)
        .filter(model_cls.id == item_id)
        .update({col: col + delta})
    )
    return rows > 0


def create_mentor(db: Session, mentor_data: MentorCreate) -> Mentor:
    """创建导师"""
    db_mentor = Mentor(**mentor_data.model_dump())
    db.add(db_mentor)
    db.commit()
    db.refresh(db_mentor)
    return db_mentor


def get_mentor(db: Session, mentor_id: UUID) -> Optional[Mentor]:
    """获取单个导师"""
    return db.query(Mentor).filter(Mentor.id == mentor_id).first()


def get_mentors(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    university: Optional[str] = None,
    department: Optional[str] = None,
    research_direction: Optional[str] = None,
    min_rating: Optional[float] = None,
    enrollment_status: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[List[Mentor], int]:
    """获取导师列表（支持筛选）"""
    query = db.query(Mentor)
    
    # 筛选条件
    if university:
        query = query.filter(Mentor.university.ilike(f"%{university}%"))
    if department:
        query = query.filter(Mentor.department.ilike(f"%{department}%"))
    if research_direction:
        # JSON 数组包含查询
        query = query.filter(
            Mentor.research_directions.contains([research_direction])
        )
    if min_rating is not None:
        query = query.filter(Mentor.avg_rating >= min_rating)
    if enrollment_status:
        query = query.filter(Mentor.enrollment_status == enrollment_status)
    if search:
        # 搜索导师姓名或研究方向
        query = query.filter(
            or_(
                Mentor.name.ilike(f"%{search}%"),
                Mentor.research_directions.contains([search])
            )
        )
    
    # 统计总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    mentors = query.order_by(Mentor.avg_rating.desc(), Mentor.review_count.desc()).offset(offset).limit(page_size).all()
    
    return mentors, total


def update_mentor(db: Session, mentor_id: UUID, mentor_data: MentorUpdate) -> Optional[Mentor]:
    """更新导师信息"""
    db_mentor = db.query(Mentor).filter(Mentor.id == mentor_id).first()
    if not db_mentor:
        return None
    
    update_data = mentor_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_mentor, field, value)
    
    db.commit()
    db.refresh(db_mentor)
    return db_mentor


def create_mentor_review(
    db: Session,
    mentor_id: UUID,
    user_id: UUID,
    review_data: MentorReviewCreate,
    ip_address: Optional[str] = None,
) -> MentorReview:
    """创建导师评价"""
    # 计算综合评分
    ratings = [
        review_data.rating_academic,
        review_data.rating_guidance,
        review_data.rating_relationship,
        review_data.rating_funding,
        review_data.rating_workload,
        review_data.rating_career,
    ]
    overall_rating = sum(ratings) / len(ratings)
    
    # 创建评价
    db_review = MentorReview(
        mentor_id=mentor_id,
        user_id=user_id,
        rating_academic=review_data.rating_academic,
        rating_guidance=review_data.rating_guidance,
        rating_relationship=review_data.rating_relationship,
        rating_funding=review_data.rating_funding,
        rating_workload=review_data.rating_workload,
        rating_career=review_data.rating_career,
        overall_rating=overall_rating,
        title=review_data.title,
        content=review_data.content,
        pros=review_data.pros,
        cons=review_data.cons,
        is_anonymous=review_data.is_anonymous,
        anonymous_id=review_data.anonymous_id,
        reviewer_identity=review_data.reviewer_identity,
        ip_address=ip_address,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        review_status="pending",  # 默认待审核
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    
    # 更新导师评分统计
    _update_mentor_rating_stats(db, mentor_id)
    
    return db_review


def get_mentor_reviews(
    db: Session,
    mentor_id: UUID,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
) -> tuple[List[MentorReview], int]:
    """获取导师评价列表"""
    query = db.query(MentorReview).filter(MentorReview.mentor_id == mentor_id)
    
    # 默认只返回已通过的评价
    if status:
        query = query.filter(MentorReview.review_status == status)
    else:
        query = query.filter(MentorReview.review_status == "approved")
    
    total = query.count()
    offset = (page - 1) * page_size
    reviews = query.order_by(MentorReview.created_at.desc()).offset(offset).limit(page_size).all()
    
    return reviews, total


def approve_review(db: Session, review_id: UUID) -> Optional[MentorReview]:
    """审核通过评价"""
    db_review = db.query(MentorReview).filter(MentorReview.id == review_id).first()
    if not db_review:
        return None
    
    db_review.review_status = "approved"
    db.commit()
    db.refresh(db_review)
    
    # 更新导师评分统计
    _update_mentor_rating_stats(db, db_review.mentor_id)
    
    return db_review


def reject_review(db: Session, review_id: UUID) -> Optional[MentorReview]:
    """拒绝评价"""
    db_review = db.query(MentorReview).filter(MentorReview.id == review_id).first()
    if not db_review:
        return None
    
    db_review.review_status = "rejected"
    db.commit()
    db.refresh(db_review)
    
    return db_review


def like_review(db: Session, review_id: UUID) -> Optional[MentorReview]:
    """点赞评价"""
    db_review = db.query(MentorReview).filter(MentorReview.id == review_id).first()
    if not db_review:
        return None
    # C3: 原子 UPDATE 替换 db_review.like_count += 1
    _atomic_increment(db, MentorReview, review_id, "like_count", 1)
    db.commit()
    db.refresh(db_review)
    return db_review


def _update_mentor_rating_stats(db: Session, mentor_id: UUID):
    """更新导师评分统计"""
    # 查询所有已通过的评价
    reviews = db.query(MentorReview).filter(
        and_(
            MentorReview.mentor_id == mentor_id,
            MentorReview.review_status == "approved"
        )
    ).all()
    
    if not reviews:
        return
    
    # 计算平均分
    mentor = db.query(Mentor).filter(Mentor.id == mentor_id).first()
    if not mentor:
        return
    
    mentor.review_count = len(reviews)
    mentor.avg_rating = sum(r.overall_rating for r in reviews) / len(reviews)
    mentor.rating_academic = sum(r.rating_academic for r in reviews) / len(reviews)
    mentor.rating_guidance = sum(r.rating_guidance for r in reviews) / len(reviews)
    mentor.rating_relationship = sum(r.rating_relationship for r in reviews) / len(reviews)
    mentor.rating_funding = sum(r.rating_funding for r in reviews) / len(reviews)
    mentor.rating_workload = sum(r.rating_workload for r in reviews) / len(reviews)
    mentor.rating_career = sum(r.rating_career for r in reviews) / len(reviews)
    
    db.commit()


def check_duplicate_review(db: Session, user_id: UUID, mentor_id: UUID, ip_address: Optional[str] = None) -> bool:
    """检查是否重复评价（同一用户或同一 IP 30 天内）"""
    from datetime import datetime, timedelta
    
    # 检查用户是否已评价
    user_review = db.query(MentorReview).filter(
        and_(
            MentorReview.user_id == user_id,
            MentorReview.mentor_id == mentor_id,
            MentorReview.review_status != "rejected"
        )
    ).first()
    
    if user_review:
        return True
    
    # 检查 IP 30 天内是否评价过
    if ip_address:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        ip_review = db.query(MentorReview).filter(
            and_(
                MentorReview.ip_address == ip_address,
                MentorReview.mentor_id == mentor_id,
                MentorReview.created_at >= thirty_days_ago,
                MentorReview.review_status != "rejected"
            )
        ).first()
        
        if ip_review:
            return True
    
    return False
