# data_freshness.py
"""Data Freshness Engine - tracks freshness of all data sources."""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-freshness", tags=["data"])

SOURCES = {
    "yanzhao": "Yanzhao", "kaoyan": "Kaoyan", "offcn": "Offcn",
    "huatu": "Huatu", "sina_edu": "Sina", "eol_kaoyan": "EOL",
    "fenbi": "Fenbi", "mofangge": "MoFangGe", "51job": "51Job",
    "gaokao_cn": "Gaokao",
}


def _is_sqlite() -> bool:
    """检测当前数据库是否为 SQLite（开发环境，可能无 data_freshness 表）。"""
    return settings.DATABASE_URL.startswith("sqlite")


def _table_exists(db: Session, table_name: str) -> bool:
    """检测表是否存在（兼容 SQLite / PostgreSQL）。"""
    try:
        if _is_sqlite():
            r = db.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=:n"
            ), {"n": table_name}).fetchone()
        else:
            r = db.execute(text(
                "SELECT to_regclass(:n)"
            ), {"n": table_name}).fetchone()
        return bool(r and r[0])
    except Exception:
        return False


def _query_freshness_rows(db: Session) -> list:
    """安全查询 data_freshness 表，表不存在时返回空列表。

    修复 bug: 原先表不存在时直接抛 500，应返回空列表让上层走 fallback。
    """
    if not _table_exists(db, "data_freshness"):
        logger.info("data_freshness 表不存在（开发环境未迁移），返回空数据")
        return []
    try:
        return db.execute(text(
            "SELECT source_name, last_successful_crawl, records_count, status FROM data_freshness"
        )).fetchall()
    except Exception as e:
        logger.warning("查询 data_freshness 表失败，降级返回空: %s", e)
        return []


def _freshness_score(last_crawl):
    if not last_crawl:
        return 20
    now = datetime.now(timezone.utc)
    if last_crawl.tzinfo is None:
        last_crawl = last_crawl.replace(tzinfo=timezone.utc)
    hours = (now - last_crawl).total_seconds() / 3600
    if hours < 24:
        return 100
    if hours < 168:
        return 80
    if hours < 720:
        return 60
    if hours < 2160:
        return 40
    return 20


@router.get("/status")
def freshness_status(db: Session = Depends(get_db)):
    rows = _query_freshness_rows(db)
    existing = {r[0]: r for r in rows}
    results = []
    for sn, name in SOURCES.items():
        if sn in existing:
            r = existing[sn]
            results.append({
                "source": sn, "display_name": name,
                "score": _freshness_score(r[1]),
                "records": r[2] or 0,
                "last_crawl": r[1].isoformat() if r[1] else None,
                "status": r[3] or "unknown",
            })
        else:
            results.append({
                "source": sn, "display_name": name,
                "score": 20, "records": 0,
                "last_crawl": None, "status": "unknown",
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"sources": results, "total": len(results)}


@router.get("/dashboard")
def freshness_dashboard(db: Session = Depends(get_db)):
    rows = _query_freshness_rows(db)
    scores = [_freshness_score(r[1]) for r in rows]
    total_sources = len(SOURCES)
    active = sum(1 for r in rows if r[3] == "active")
    stale = sum(1 for s in scores if s < 60)
    total_records = sum(r[2] or 0 for r in rows)
    return {
        "total_sources": total_sources,
        "active": active,
        "stale": stale,
        "total_records": total_records,
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
    }


@router.post("/refresh/{source_name}")
def refresh_source(source_name: str, db: Session = Depends(get_db)):
    if source_name not in SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source '{source_name}'. Valid sources: {', '.join(sorted(SOURCES.keys()))}",
        )
    if not _table_exists(db, "data_freshness"):
        raise HTTPException(
            status_code=503,
            detail="data_freshness 表未初始化，无法触发刷新",
        )
    try:
        if _is_sqlite():
            # SQLite 不支持 ON CONFLICT，用 INSERT OR REPLACE 简化
            db.execute(text(
                "INSERT OR REPLACE INTO data_freshness "
                "(source_name, last_successful_crawl, records_count, status, updated_at) "
                "VALUES (:n, CURRENT_TIMESTAMP, 0, 'refreshing', CURRENT_TIMESTAMP)"
            ), {"n": source_name})
        else:
            db.execute(text(
                "INSERT INTO data_freshness (source_name, last_successful_crawl, records_count, status, updated_at) "
                "VALUES (:n, NOW(), 0, 'refreshing', NOW()) "
                "ON CONFLICT (source_name) DO UPDATE SET status='refreshing', updated_at=NOW()"
            ), {"n": source_name})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("Failed to refresh source %s: %s", source_name, e)
        raise HTTPException(status_code=500, detail=f"Failed to trigger refresh for {source_name}")
    return {"message": f"Refresh triggered for {source_name}"}
