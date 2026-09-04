"""人生设计蓝图 API — 「认识自己」V1。

斯坦福人生设计访谈（life_design skill）⟨DONE⟩ 轮产出的《个人人生设计蓝图》
持久化与读取。蓝图按用户版本号递增（再访谈 = 新版本），transcript 保存
问答记录供复盘与 V3 版本 diff。

端点全部需要登录；无分享（V2 复用决策报告 token 模式）。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.life_design import LifeDesignBlueprint
from app.models.user import User
from app.schemas.life_design import (
    BlueprintCreate,
    BlueprintResponse,
    BlueprintSummary,
)

router = APIRouter(prefix="/api/life-design/blueprints", tags=["人生设计蓝图"])


def _next_version(db: Session, user_id) -> int:
    latest = (
        db.execute(
            select(LifeDesignBlueprint.version)
            .where(LifeDesignBlueprint.user_id == user_id)
            .order_by(LifeDesignBlueprint.version.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    return (latest or 0) + 1


@router.post("", response_model=BlueprintResponse, status_code=status.HTTP_201_CREATED)
def create_blueprint(
    body: BlueprintCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlueprintResponse:
    """保存一份人生设计蓝图（版本号自动递增）。"""
    version = _next_version(db, user.id)
    title = (body.title or "").strip() or f"我的人生蓝图 v{version}"
    record = LifeDesignBlueprint(
        user_id=user.id,
        conversation_id=body.conversation_id,
        title=title[:200],
        content=body.content,
        transcript=[t.model_dump() for t in body.transcript],
        status=body.status,
        version=version,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[BlueprintSummary])
def list_blueprints(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BlueprintSummary]:
    """列出我的蓝图（不含全文，按版本倒序）。"""
    rows = (
        db.execute(
            select(LifeDesignBlueprint)
            .where(LifeDesignBlueprint.user_id == user.id)
            .order_by(LifeDesignBlueprint.version.desc())
        )
        .scalars()
        .all()
    )
    return rows


@router.get("/latest", response_model=BlueprintResponse | None)
def latest_blueprint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlueprintResponse | None:
    """最新一份蓝图（无则 200 + null，前端按空态渲染）。"""
    row = (
        db.execute(
            select(LifeDesignBlueprint)
            .where(LifeDesignBlueprint.user_id == user.id)
            .order_by(LifeDesignBlueprint.version.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    return row


@router.get("/{blueprint_id}", response_model=BlueprintResponse)
def get_blueprint(
    blueprint_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlueprintResponse:
    row = (
        db.execute(
            select(LifeDesignBlueprint).where(
                LifeDesignBlueprint.id == blueprint_id,
                LifeDesignBlueprint.user_id == user.id,
            )
        )
        .scalars()
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="蓝图不存在")
    return row
