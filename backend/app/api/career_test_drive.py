# backend/app/api/career_test_drive.py
"""职业试驾 API — 第一人称一日体验生成器。

路由前缀 /api/career-test-drive。生成接口走 LLM（未配置时回退模板），
历史与详情接口直接读库。所有接口需登录鉴权。
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.career_test_drive import (
    CareerTestDriveCreate,
    CareerTestDriveResponse,
    TimeBlock,
)
from app.services import career_test_drive_service as svc

router = APIRouter(prefix="/api/career-test-drive", tags=["职业试驾"])


def _to_response(drive) -> CareerTestDriveResponse:
    """把 ORM 记录展开为响应（experience_content 内含 time_blocks/summary/pros/cons）。"""
    content = drive.experience_content or {}
    blocks = [
        TimeBlock(
            time=b.get("time", ""),
            activity=b.get("activity", ""),
            description=b.get("description", ""),
            emotion=b.get("emotion", ""),
        )
        for b in (content.get("time_blocks") or [])
        if isinstance(b, dict)
    ]
    return CareerTestDriveResponse(
        id=drive.id,
        path_type=drive.path_type,
        target_role=drive.target_role,
        experience_content=blocks,
        summary=content.get("summary", ""),
        pros=content.get("pros") or [],
        cons=content.get("cons") or [],
        created_at=drive.created_at,
    )


@router.post("/generate", response_model=CareerTestDriveResponse)
async def generate_drive(
    request: CareerTestDriveCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """生成一日体验（AI 优先，回退模板）并持久化。"""
    drive = await svc.create_drive(db, user.id, request.path_type, request.target_role)
    return _to_response(drive)


@router.get("/history", response_model=list[CareerTestDriveResponse])
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的历史试驾记录（按创建时间倒序）。"""
    drives = svc.list_drives(db, user.id)
    return [_to_response(d) for d in drives]


@router.get("/{drive_id}", response_model=CareerTestDriveResponse)
def get_drive(
    drive_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单条试驾详情。"""
    drive = svc.get_drive(db, user.id, drive_id)
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="试驾记录不存在")
    return _to_response(drive)
