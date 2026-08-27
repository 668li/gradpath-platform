"""用户公开主页 API。"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.experience_post import ExperiencePost
from app.models.qa import QA
from app.models.qa_answer import QAAnswer
from app.models.user import User
from app.schemas.experience_post import ExperiencePostResponse
from app.schemas.qa import QAAnswerResponse, QAResponse

router = APIRouter(prefix="/api/users", tags=["用户主页"])


class UserProfileResponse(BaseModel):
    """用户公开主页信息"""

    id: UUID
    nickname: str | None = None
    username: str | None = None
    name: str | None = None
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    current_stage: str | None = None
    school: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    created_at: datetime
    post_count: int = 0
    qa_count: int = 0
    answer_count: int = 0
    total_likes: int = 0

    model_config = ConfigDict(from_attributes=True)


def _get_display_name(user: User) -> str:
    return user.nickname or user.username or user.name or "匿名用户"


def _build_profile(user: User, db: Session) -> UserProfileResponse:
    post_count = (
        db.query(ExperiencePost)
        .filter(
            ExperiencePost.user_id == user.id,
            ExperiencePost.status == "approved",
        )
        .count()
    )
    qa_count = (
        db.query(QA)
        .filter(
            QA.user_id == user.id,
            QA.status == "approved",
        )
        .count()
    )
    answer_count = (
        db.query(QAAnswer)
        .filter(
            QAAnswer.user_id == user.id,
            QAAnswer.status == "approved",
        )
        .count()
    )
    total_likes = (
        db.query(ExperiencePost.like_count)
        .filter(
            ExperiencePost.user_id == user.id,
            ExperiencePost.status == "approved",
        )
        .all()
    )
    total_likes_sum = sum(r[0] for r in total_likes) if total_likes else 0

    return UserProfileResponse(
        id=user.id,
        nickname=user.nickname,
        username=user.username,
        name=user.name,
        display_name=_get_display_name(user),
        avatar_url=user.avatar_url,
        bio=user.bio,
        current_stage=user.current_stage.value if user.current_stage else None,
        school=user.school,
        major=user.major,
        graduation_year=user.graduation_year,
        created_at=user.created_at,
        post_count=post_count,
        qa_count=qa_count,
        answer_count=answer_count,
        total_likes=total_likes_sum,
    )


@router.get("/{user_id}/profile", response_model=UserProfileResponse)
def get_user_profile(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """获取用户公开主页信息。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return _build_profile(user, db)


@router.get("/{user_id}/posts", response_model=list[ExperiencePostResponse])
def get_user_posts(
    user_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取用户分享的经验贴。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    offset = (page - 1) * page_size
    posts = (
        db.query(ExperiencePost)
        .filter(
            ExperiencePost.user_id == user_id,
            ExperiencePost.status == "approved",
        )
        .order_by(ExperiencePost.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    author_name = _get_display_name(user)
    return [
        ExperiencePostResponse.model_validate(p).model_copy(
            update={"author_name": author_name, "author_avatar": user.avatar_url}
        )
        for p in posts
    ]


@router.get("/{user_id}/qa", response_model=list[QAResponse])
def get_user_qa(
    user_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取用户提出的问题。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    offset = (page - 1) * page_size
    questions = (
        db.query(QA)
        .filter(
            QA.user_id == user_id,
            QA.status == "approved",
        )
        .order_by(QA.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    author_name = _get_display_name(user)
    return [
        QAResponse(
            id=q.id,
            title=q.title,
            content=q.content,
            tags=q.tags,
            user_id=q.user_id,
            status=q.status,
            view_count=q.view_count,
            answer_count=q.answer_count,
            is_resolved=q.is_resolved,
            best_answer_id=q.best_answer_id,
            answers=[],
            created_at=q.created_at,
            updated_at=q.updated_at,
            author_name=author_name,
            author_avatar=user.avatar_url,
        )
        for q in questions
    ]


@router.get("/{user_id}/answers", response_model=list[QAAnswerResponse])
def get_user_answers(
    user_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取用户的回答。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    offset = (page - 1) * page_size
    answers = (
        db.query(QAAnswer)
        .filter(
            QAAnswer.user_id == user_id,
            QAAnswer.status == "approved",
        )
        .order_by(QAAnswer.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    author_name = _get_display_name(user)
    return [
        QAAnswerResponse.model_validate(a).model_copy(
            update={"author_name": author_name, "author_avatar": user.avatar_url}
        )
        for a in answers
    ]
