# backend/app/api/resource_links.py
"""资源导航目录公开 API（RN-1b，2026-10-03 任务书）。

只读公开端点，无鉴权（目录=全站公共内容，链接可查证）。
消费出口：前端 /resources 资源导航页面。

点名制口径：
- active（用户终审转正）与 pending（候选）都外显；
- pending 条目带 pending_review=true 字段，前端渲染「待站长终审」琥珀徽章；
- killed / retired 不外显；
- forbidden 版权档在 seed 与本 API 双闸禁入（防御性过滤，正常不可能出现）。
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.resource_link import (
    RESOURCE_COPYRIGHT_FORBIDDEN,
    RESOURCE_STATUS_ACTIVE,
    RESOURCE_STATUS_PENDING,
    ResourceLink,
)

router = APIRouter(prefix="/api/resources", tags=["资源导航"])


class ResourceLinkOut(BaseModel):
    id: str
    name: str
    url: str
    track: str
    category: str
    note: str
    risk_note: str | None
    copyright_tier: str
    status: str
    pending_review: bool
    user_approved: bool
    added_via: str
    sources: list
    recently_added: bool


class ResourceListResponse(BaseModel):
    total: int
    items: list[ResourceLinkOut]
    active_count: int
    pending_count: int


def _to_out(link: ResourceLink) -> ResourceLinkOut:
    return ResourceLinkOut(
        id=str(link.id),
        name=link.name,
        url=link.url,
        track=link.track,
        category=link.category,
        note=link.note,
        risk_note=link.risk_note,
        copyright_tier=link.copyright_tier,
        status=link.status,
        pending_review=link.status == RESOURCE_STATUS_PENDING,
        user_approved=link.user_approved,
        added_via=link.added_via,
        sources=link.sources or [],
        recently_added=link.recently_added,
    )


def _visible_query(db: Session):
    """外显面：active + pending（pending 带徽章）；killed/retired/forbidden 不出。"""
    return db.query(ResourceLink).filter(
        ResourceLink.status.in_([RESOURCE_STATUS_ACTIVE, RESOURCE_STATUS_PENDING]),
        ResourceLink.copyright_tier != RESOURCE_COPYRIGHT_FORBIDDEN,
    )


@router.get("", response_model=ResourceListResponse)
def list_resources(
    track: str | None = Query(None, description="身份线：kaoyan/employment/common"),
    category: str | None = Query(None, description="分类：kaoyan_resources/official/employment/open_source/tool"),
    q: str | None = Query(None, description="关键词（名称/定位模糊匹配）"),
    db: Session = Depends(get_db),
):
    """资源导航列表（active 在前 pending 在后，同组按 recently_added/创建时间降序）。"""
    query = _visible_query(db)
    if track:
        query = query.filter(ResourceLink.track.in_([track, "common"]))
    if category:
        query = query.filter(ResourceLink.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                ResourceLink.name.ilike(like),
                ResourceLink.note.ilike(like),
                ResourceLink.url.ilike(like),
            )
        )
    links = (
        query.order_by(
            # active 优先于 pending（0=active, 1=pending）
            (ResourceLink.status != RESOURCE_STATUS_ACTIVE),
            ResourceLink.recently_added.desc(),
            ResourceLink.created_at.desc(),
        )
        .all()
    )
    return ResourceListResponse(
        total=len(links),
        items=[_to_out(l) for l in links],
        active_count=sum(1 for l in links if l.status == RESOURCE_STATUS_ACTIVE),
        pending_count=sum(1 for l in links if l.status == RESOURCE_STATUS_PENDING),
    )
