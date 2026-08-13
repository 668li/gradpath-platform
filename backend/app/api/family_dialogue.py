"""家庭对话脚手架 API — 帮大学生和父母沟通职业选择。

端点：
- POST /api/family-dialogue/start              — 启动会话（理解父母 + 准备弹药）
- GET  /api/family-dialogue/session/{id}        — 获取单条会话详情
- POST /api/family-dialogue/session/{id}/practice — 模拟对话练习（AI 扮演父母回复）
- GET  /api/family-dialogue/history             — 获取历史会话
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.family_dialogue import (
    PARENT_ARCHETYPES,
    FamilyDialogueResponse,
    FamilyDialogueStart,
    PracticeMessage,
    PracticeRequest,
)
from app.services import family_dialogue_service as svc

router = APIRouter(prefix="/api/family-dialogue", tags=["家庭对话脚手架"])


def _to_response(session) -> FamilyDialogueResponse:
    """把 ORM 对象序列化为响应 schema。"""
    return FamilyDialogueResponse(
        id=str(session.id),
        parent_concern=session.parent_concern,
        user_choice=session.user_choice,
        parent_archetype=session.parent_archetype,
        understanding=session.understanding or "",
        arguments=session.prepared_arguments or [],
        talking_tips=session.talking_tips or [],
        practice_messages=session.practice_messages or [],
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/start", response_model=FamilyDialogueResponse)
def start_session(
    body: FamilyDialogueStart,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """启动家庭对话脚手架会话。

    输入父母担忧 + 用户选择 + 父母类型，返回：
    - 理解父母的分析（为什么这么想、时代背景、合理部分）
    - 3-5 个 Argument（含父母话术/建议回应/数据支撑/共情提示）
    - 沟通技巧列表
    """
    if body.parent_archetype not in PARENT_ARCHETYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"parent_archetype 必须是: {', '.join(PARENT_ARCHETYPES)}",
        )

    session = svc.start_session(
        db,
        user.id,
        {
            "parent_concern": body.parent_concern,
            "user_choice": body.user_choice,
            "parent_archetype": body.parent_archetype,
        },
    )
    return _to_response(session)


@router.get("/session/{session_id}", response_model=FamilyDialogueResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单条会话详情。"""
    session = svc.get_session(db, session_id, user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )
    return _to_response(session)


@router.post("/session/{session_id}/practice", response_model=PracticeMessage)
def practice(
    session_id: str,
    body: PracticeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """模拟对话练习 — 用户输入要说的话，系统扮演父母回复。"""
    session = svc.get_session(db, session_id, user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在，请先调用 /start",
        )

    try:
        reply = svc.practice_reply(db, session_id, user.id, body.message)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )
    return PracticeMessage(role=reply["role"], content=reply["content"])


@router.get("/history", response_model=list[FamilyDialogueResponse])
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取用户的历史会话（按时间倒序）。"""
    sessions = svc.list_sessions(db, user.id)
    return [_to_response(s) for s in sessions]
