"""考研社区 — 问答互助 API。"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user, get_current_user
from app.core.rate_limit import rate_limits
from app.database import get_db
from app.main import limiter
from app.models.qa import QA
from app.models.qa_answer import QAAnswer
from app.models.user import User
from app.schemas.common import CursorPaginatedResponse
from app.schemas.qa import (
    QAAnswerCreate,
    QAAnswerListResponse,
    QAAnswerResponse,
    QAAnswerUpdate,
    QACreate,
    QAListResponse,
    QAResponse,
    QAUpdate,
)
from app.services.qa_service import (
    accept_best_answer,
    create_answer,
    create_question,
    delete_answer,
    delete_question,
    get_answer,
    get_answers,
    get_question,
    get_questions,
    get_questions_cursor,
    increment_question_view,
    like_answer,
    update_answer,
    update_question,
)

router = APIRouter(prefix="/api/kaoyan/qa", tags=["考研社区-问答"])


def _check_question_owner(question: QA, user: User) -> None:
    if not user.is_admin and question.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作该问题",
        )


def _check_answer_owner(answer: QAAnswer, user: User) -> None:
    if not user.is_admin and answer.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作该回答",
        )


@router.get("", response_model=QAListResponse | CursorPaginatedResponse[QAResponse])
def list_questions(
    page: int = Query(1, ge=1, description="页码（offset 分页）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    cursor: Optional[str] = Query(None, description="游标（cursor 分页，传则忽略 page）"),
    tag: Optional[str] = Query(None, description="标签过滤"),
    status: Optional[str] = Query(None, description="审核状态过滤（默认 approved）"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    is_resolved: Optional[bool] = Query(None, description="是否已解决"),
    db: Session = Depends(get_db),
):
    """获取问题列表（默认展示已通过的内容）。

    支持两种分页模式：
    - offset 分页：传 page + page_size（默认）
    - cursor 分页：传 cursor + page_size（高性能，适合无限滚动）
    """
    if cursor:
        items, next_cursor, has_more = get_questions_cursor(
            db,
            page_size=page_size,
            cursor=cursor,
            tag=tag,
            status=status,
            search=search,
            is_resolved=is_resolved,
        )
        return CursorPaginatedResponse(
            items=[
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
                )
                for q in items
            ],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    questions, total = get_questions(
        db,
        page=page,
        page_size=page_size,
        tag=tag,
        status=status,
        search=search,
        is_resolved=is_resolved,
    )
    return QAListResponse(
        items=[
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
            )
            for q in questions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{question_id}", response_model=QAResponse)
def get_question_detail(
    question_id: UUID,
    db: Session = Depends(get_db),
):
    """获取问题详情（含回答列表，自动增加浏览数）。"""
    question = get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问题不存在")

    answers, _ = get_answers(db, question_id)
    increment_question_view(db, question_id)

    return QAResponse(
        id=question.id,
        title=question.title,
        content=question.content,
        tags=question.tags,
        user_id=question.user_id,
        status=question.status,
        view_count=question.view_count,
        answer_count=question.answer_count,
        is_resolved=question.is_resolved,
        best_answer_id=question.best_answer_id,
        answers=[QAAnswerResponse.model_validate(a) for a in answers],
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


@router.post(
    "",
    response_model=QAResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(rate_limits.QA_QUESTION_CREATE)
def create_question_endpoint(
    request: Request,
    response: Response,
    data: QACreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建问题（需登录）。"""
    question = create_question(db, user.id, data.model_dump())
    return QAResponse(
        id=question.id,
        title=question.title,
        content=question.content,
        tags=question.tags,
        user_id=question.user_id,
        status=question.status,
        view_count=question.view_count,
        answer_count=question.answer_count,
        is_resolved=question.is_resolved,
        best_answer_id=question.best_answer_id,
        answers=[],
        created_at=question.created_at,
        updated_at=question.updated_at,
    )


@router.put("/{question_id}", response_model=QAResponse)
def update_question_endpoint(
    question_id: UUID,
    data: QAUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新问题（作者或管理员）。"""
    question = get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问题不存在")
    _check_question_owner(question, user)

    updated = update_question(db, question_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问题不存在")

    return QAResponse(
        id=updated.id,
        title=updated.title,
        content=updated.content,
        tags=updated.tags,
        user_id=updated.user_id,
        status=updated.status,
        view_count=updated.view_count,
        answer_count=updated.answer_count,
        is_resolved=updated.is_resolved,
        best_answer_id=updated.best_answer_id,
        answers=[],
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_endpoint(
    question_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除问题（作者或管理员，级联删除回答）。"""
    question = get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问题不存在")
    _check_question_owner(question, user)

    delete_question(db, question_id)
    return None


# ===== 回答相关 =====


@router.get("/{question_id}/answers", response_model=QAAnswerListResponse)
def list_answers(
    question_id: UUID,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """获取问题回答列表。"""
    answers, total = get_answers(db, question_id, page=page, page_size=page_size)
    return QAAnswerListResponse(
        items=[QAAnswerResponse.model_validate(a) for a in answers],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{question_id}/answers",
    response_model=QAAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(rate_limits.QA_ANSWER_CREATE)
def create_answer_endpoint(
    request: Request,
    response: Response,
    question_id: UUID,
    data: QAAnswerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建回答（需登录）。"""
    question = get_question(db, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问题不存在")
    answer = create_answer(db, question_id, user.id, data.model_dump())
    return QAAnswerResponse.model_validate(answer)


@router.put("/answers/{answer_id}", response_model=QAAnswerResponse)
def update_answer_endpoint(
    answer_id: UUID,
    data: QAAnswerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新回答（作者或管理员）。"""
    answer = get_answer(db, answer_id)
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回答不存在")
    _check_answer_owner(answer, user)

    updated = update_answer(db, answer_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回答不存在")
    return QAAnswerResponse.model_validate(updated)


@router.post("/answers/{answer_id}/accept", response_model=QAResponse)
def accept_answer_endpoint(
    answer_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """采纳最佳回答（问题作者或管理员）。"""
    answer = get_answer(db, answer_id)
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回答不存在")

    question = get_question(db, answer.qa_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="问题不存在")

    _check_question_owner(question, user)

    updated = accept_best_answer(db, answer.qa_id, answer_id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="采纳失败")

    answers, _ = get_answers(db, updated.id)
    return QAResponse(
        id=updated.id,
        title=updated.title,
        content=updated.content,
        tags=updated.tags,
        user_id=updated.user_id,
        status=updated.status,
        view_count=updated.view_count,
        answer_count=updated.answer_count,
        is_resolved=updated.is_resolved,
        best_answer_id=updated.best_answer_id,
        answers=[QAAnswerResponse.model_validate(a) for a in answers],
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.post("/answers/{answer_id}/like")
@limiter.limit(rate_limits.COMMUNITY_LIKE)
def like_answer_endpoint(
    request: Request,
    response: Response,
    answer_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """点赞回答（需登录）。"""
    answer = like_answer(db, answer_id)
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回答不存在")
    return {"message": "点赞成功", "like_count": answer.like_count}
