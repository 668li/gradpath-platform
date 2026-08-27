"""数据真实性接入层 — 来源管理 API（方案 C 落地实现）。

端点对齐系统设计 §3.2.M10.2 接口清单；实现来源标注 CRUD + 可信度分级。
合规红线：外部数据来源必须可追溯（source_url / source_system / credibility）。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.database import get_db
from app.models.ingestion import DataSourceMeta
from app.models.user import User
from app.schemas.ingestion import DataSourceVO, SourceListVO, SourceUpdateRequest
from app.services.ingestion_service import list_sources, update_source

router = APIRouter(prefix="/api/admin/sources", tags=["数据真实性-来源管理"])


def _to_vo(source: DataSourceMeta) -> DataSourceVO:
    """model → VO 手动映射（DataSourceVO.source_id 为业务 ID，与主键不同名，
    from_attributes 无法自动映射，需显式构建）。"""
    return DataSourceVO(
        source_id=source.id,
        source_system=source.source_system,
        source_url=source.source_url,
        crawled_at=source.crawled_at,
        credibility=source.credibility,
        verify_count=source.verify_count or 0,
        reviewed_by=source.reviewed_by,
        review_status=source.review_status,
        created_at=source.created_time,
    )


@router.get("", response_model=SourceListVO)
def list_sources_endpoint(
    review_status: str | None = Query(None, description="按审核状态过滤"),
    credibility: str | None = Query(None, description="按可信度过滤"),
    source_system: str | None = Query(None, description="按来源系统过滤"),
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """来源与可信度配置列表（分页，最新在前）。

    幂等：GET 天然幂等。
    """
    rows, total = list_sources(
        db,
        review_status=review_status,
        credibility=credibility,
        source_system=source_system,
        page=page,
        page_size=page_size,
    )
    return SourceListVO(items=[_to_vo(row) for row in rows], total=total)


@router.put("/{source_id}", response_model=DataSourceVO)
def update_source_endpoint(
    source_id: int,
    body: SourceUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """更新来源可信度配置（部分更新；审核人回填为当前管理员）。

    幂等：是（id+version 乐观锁）。
    """
    try:
        source = update_source(
            db,
            source_id,
            credibility=body.credibility,
            review_status=body.review_status,
            verify_count=body.verify_count,
            reviewer=admin.email,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _to_vo(source)
