"""数据真实性接入层 — 录入管道 API（方案 C 落地实现）。

端点对齐系统设计 §3.2.M10.2 接口清单：
- POST /ingest：人工触发已注册爬虫（强制护栏限量，产物进 PENDING 审核队列）
- GET  /ingest/{run_id}：查询抓取运行状态（CrawlerRun.id，UUID 字符串）
- POST /confirm：人工确认字段入库（禁止自动入库 — 合规红线）

存量 admin/research.py（/api/admin/research-queue 审核链路）保持不变。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_admin_user
from app.database import get_db
from app.models.user import User
from app.schemas.ingestion import (
    IngestConfirmRequest,
    IngestRecordVO,
    IngestRunVO,
    IngestTriggerRequest,
)
from app.services.ingestion_service import (
    IngestionConflictError,
    confirm_ingest,
    get_ingest_run,
    trigger_ingest,
)

router = APIRouter(prefix="/api/admin/research", tags=["数据真实性-录入管道"])


@router.post("/ingest", response_model=IngestRunVO)
def trigger_ingest_endpoint(
    body: IngestTriggerRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """触发权威数据抓取（人工触发）。

    护栏强制生效（max_pages=1 / max_items=50 / rate_limit=1s），
    产物一律写入 PENDING 审核队列，不自动落业务表（合规红线）。
    """
    try:
        return trigger_ingest(
            db,
            source_system=body.source_system,
            url=body.url,
            target_type=body.target_type,
        )
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/ingest/{run_id}", response_model=IngestRunVO)
def get_ingest_run_endpoint(
    run_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """查询抓取运行状态。

    run_id 为 CrawlerRun.id（UUID 字符串），与 t_external_research_item.crawler_run_id 契约一致。
    """
    try:
        return get_ingest_run(db, run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/confirm", response_model=IngestRecordVO)
def confirm_ingest_endpoint(
    body: IngestConfirmRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """人工确认字段入库（禁止自动入库 — 合规红线）。

    校验 PENDING → 来源 URL 追溯 → promote 落业务表（幂等）→ 队列回填 APPROVED。
    审核人/审核时间写入 external_meta 与队列行，保证全程可追溯。
    """
    try:
        return confirm_ingest(
            db,
            record_id=body.record_id,
            run_id=body.run_id,
            confirmed_fields=body.confirmed_fields,
            source_url=body.source_url,
            source_system=body.source_system,
            operator_id=body.operator_id,
            note=body.note,
            reviewer=admin.email,
        )
    except IngestionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
