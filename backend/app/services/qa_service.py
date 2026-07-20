"""考研问答服务层 — 社区交流系统。"""
from typing import Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.cursor_pagination import apply_cursor_filter, encode_cursor
from app.models.qa import QA
from app.models.qa_answer import QAAnswer


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


def create_question(
    db: Session,
    user_id: UUID,
    data: dict,
) -> QA:
    """创建问题（默认待审核）。"""
    question = QA(
        user_id=user_id,
        title=data["title"],
        content=data["content"],
        tags=data.get("tags") or [],
        status="pending",
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def get_question(db: Session, question_id: UUID) -> Optional[QA]:
    """获取单个问题。"""
    return (
        db.query(QA)
        .options(selectinload(QA.answers))
        .filter(QA.id == question_id)
        .first()
    )


def get_questions(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    is_resolved: Optional[bool] = None,
) -> tuple[list[QA], int]:
    """获取问题列表（支持筛选）。

    默认只返回 approved 状态的问题；传入 status 可覆盖。
    """
    query = db.query(QA)

    if status:
        query = query.filter(QA.status == status)
    else:
        query = query.filter(QA.status == "approved")

    if tag:
        query = query.filter(QA.tags.contains([tag]))
    if is_resolved is not None:
        query = query.filter(QA.is_resolved == is_resolved)
    if search:
        query = query.filter(
            or_(
                QA.title.ilike(f"%{search}%"),
                QA.content.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    questions = (
        query.order_by(QA.is_resolved.asc(), QA.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return questions, total


def get_questions_cursor(
    db: Session,
    *,
    page_size: int = 20,
    cursor: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    is_resolved: Optional[bool] = None,
) -> tuple[list[QA], Optional[str], bool]:
    """游标分页获取问题列表。

    Returns:
        (items, next_cursor, has_more)
    """
    query = db.query(QA)

    if status:
        query = query.filter(QA.status == status)
    else:
        query = query.filter(QA.status == "approved")

    if tag:
        query = query.filter(QA.tags.contains([tag]))
    if is_resolved is not None:
        query = query.filter(QA.is_resolved == is_resolved)
    if search:
        query = query.filter(
            or_(
                QA.title.ilike(f"%{search}%"),
                QA.content.ilike(f"%{search}%"),
            )
        )

    query = apply_cursor_filter(
        query,
        cursor,
        time_col=QA.created_at,
        id_col=QA.id,
    )

    query = query.order_by(QA.is_resolved.asc(), QA.created_at.desc())

    items = query.limit(page_size + 1).all()
    has_more = len(items) > page_size
    if has_more:
        items = items[:page_size]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.created_at, str(last.id))

    return items, next_cursor, has_more


def update_question(
    db: Session,
    question_id: UUID,
    data: dict,
) -> Optional[QA]:
    """更新问题。"""
    question = get_question(db, question_id)
    if not question:
        return None

    for field in ("title", "content", "tags"):
        if field in data and data[field] is not None:
            setattr(question, field, data[field])

    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, question_id: UUID) -> bool:
    """删除问题（级联删除回答）。"""
    question = get_question(db, question_id)
    if not question:
        return False
    db.delete(question)
    db.commit()
    return True


def increment_question_view(db: Session, question_id: UUID) -> bool:
    """增加问题浏览数。"""
    # C3: 原子 UPDATE 替换 question.view_count += 1
    return _atomic_increment(db, QA, question_id, "view_count", 1) and (
        db.commit() or True
    )


# ===== 回答相关 =====


def create_answer(
    db: Session,
    question_id: UUID,
    user_id: UUID,
    data: dict,
) -> QAAnswer:
    """创建回答（默认待审核）。"""
    answer = QAAnswer(
        qa_id=question_id,
        user_id=user_id,
        content=data["content"],
        status="pending",
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    # 更新问题回答数
    _update_answer_count(db, question_id)

    return answer


def get_answer(db: Session, answer_id: UUID) -> Optional[QAAnswer]:
    """获取单个回答。"""
    return db.query(QAAnswer).filter(QAAnswer.id == answer_id).first()


def get_answers(
    db: Session,
    question_id: UUID,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
) -> tuple[list[QAAnswer], int]:
    """获取问题回答列表。"""
    query = db.query(QAAnswer).filter(QAAnswer.qa_id == question_id)

    if status:
        query = query.filter(QAAnswer.status == status)
    else:
        query = query.filter(QAAnswer.status == "approved")

    total = query.count()
    offset = (page - 1) * page_size
    answers = (
        query.order_by(QAAnswer.is_best.desc(), QAAnswer.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return answers, total


def update_answer(
    db: Session,
    answer_id: UUID,
    data: dict,
) -> Optional[QAAnswer]:
    """更新回答。"""
    answer = get_answer(db, answer_id)
    if not answer:
        return None

    if "content" in data and data["content"] is not None:
        answer.content = data["content"]

    db.commit()
    db.refresh(answer)
    return answer


def delete_answer(db: Session, answer_id: UUID) -> bool:
    """删除回答。"""
    answer = get_answer(db, answer_id)
    if not answer:
        return False
    question_id = answer.qa_id
    db.delete(answer)
    db.commit()
    _update_answer_count(db, question_id)
    return True


def accept_best_answer(db: Session, question_id: UUID, answer_id: UUID) -> Optional[QA]:
    """采纳最佳回答。"""
    question = get_question(db, question_id)
    if not question:
        return None

    answer = get_answer(db, answer_id)
    if not answer or answer.qa_id != question_id:
        return None

    # 取消该问题下其他最佳回答
    db.query(QAAnswer).filter(
        QAAnswer.qa_id == question_id,
        QAAnswer.is_best == True,
    ).update({"is_best": False})

    answer.is_best = True
    answer.status = "approved"
    question.is_resolved = True
    question.best_answer_id = answer_id

    db.commit()
    db.refresh(question)
    return question


def like_answer(db: Session, answer_id: UUID) -> Optional[QAAnswer]:
    """点赞回答。"""
    answer = get_answer(db, answer_id)
    if not answer:
        return None
    # C3: 原子 UPDATE 替换 answer.like_count += 1
    _atomic_increment(db, QAAnswer, answer_id, "like_count", 1)
    db.commit()
    db.refresh(answer)
    return answer


def _update_answer_count(db: Session, question_id: UUID) -> None:
    """更新问题回答数。"""
    count = db.query(QAAnswer).filter(QAAnswer.qa_id == question_id).count()
    question = get_question(db, question_id)
    if question:
        question.answer_count = count
        db.commit()
