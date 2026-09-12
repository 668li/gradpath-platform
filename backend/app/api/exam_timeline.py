"""考公流程时间线 API（feature 001 / M2）— 契约见 .specify/.../contracts/timeline-api.md。

浏览公开（C1/C2/C7），订阅/回传登录态（C3-C6）；错误语义：401/404/409/422。
本文件不写业务——全部下沉 timeline_service（router→service 分层纪律）。
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.exam_timeline import NodeFeedbackStatus
from app.models.user import User
from app.schemas.exam_timeline import (
    ExamDetail,
    ExamListItem,
    FeedbackRequest,
    MyExamItem,
    NodeVO,
    SubscribeResult,
)
from app.services import timeline_service as tl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/civil-service/timeline", tags=["考公时间线"])


@router.get("/exams", response_model=list[ExamListItem])
def list_exams_endpoint(track: str | None = None, db: Session = Depends(get_db)) -> Any:
    """C1 考次列表（公开）。"""
    return tl.list_exams(db, track=track)


@router.get("/exams/{code}", response_model=ExamDetail)
def exam_detail_endpoint(code: str, db: Session = Depends(get_db)) -> Any:
    """C2 考次详情+12 节点（公开，诚实字段全暴露）。"""
    try:
        return tl.get_exam_detail(db, code)
    except tl.ExamNotFound:
        raise HTTPException(status_code=404, detail="考次不存在") from None


@router.post("/exams/{code}/subscribe", response_model=SubscribeResult, status_code=201)
def subscribe_endpoint(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    """C3 订阅考次（登录）。重复 409。"""
    try:
        sub = tl.subscribe(db, uuid.UUID(str(user.id)), code)
    except tl.ExamNotFound:
        raise HTTPException(status_code=404, detail="考次不存在") from None
    except tl.AlreadySubscribed:
        raise HTTPException(status_code=409, detail="已订阅该考试") from None
    return SubscribeResult(exam_code=code, notify_channels=list(sub.notify_channels))


@router.delete("/exams/{code}/subscription", status_code=204)
def unsubscribe_endpoint(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """C4 软退订（登录）：保留回传史。无有效订阅 404。"""
    try:
        ok = tl.unsubscribe(db, uuid.UUID(str(user.id)), code)
    except tl.ExamNotFound:
        raise HTTPException(status_code=404, detail="考次不存在") from None
    if not ok:
        raise HTTPException(status_code=404, detail="未订阅该考试")
    return Response(status_code=204)


@router.get("/me", response_model=list[MyExamItem])
def my_exams_endpoint(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Any:
    """C5 我的订阅+进度+下一节点（登录）。"""
    return tl.get_my_exams(db, uuid.UUID(str(user.id)))


@router.put("/nodes/{node_id}/feedback", response_model=NodeVO)
def node_feedback_endpoint(
    node_id: str,
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    """C6 节点回传（登录，须已订阅；跨考写回统一 404 防探测）。"""
    try:
        tl.set_feedback(db, uuid.UUID(str(user.id)), node_id, NodeFeedbackStatus(payload.status))
    except tl.ExamNotFound:
        raise HTTPException(status_code=404, detail="节点不存在或未订阅该考") from None
    return tl.get_node_payload(db, node_id)


@router.get("/nodes/{node_id}", response_model=NodeVO)
def node_detail_endpoint(node_id: str, db: Session = Depends(get_db)) -> Any:
    """C7 单节点卡深链（公开，分享/通知落地页用）。"""
    try:
        return tl.get_node_payload(db, node_id)
    except tl.ExamNotFound:
        raise HTTPException(status_code=404, detail="节点不存在") from None
