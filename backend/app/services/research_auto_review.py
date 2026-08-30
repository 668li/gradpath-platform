"""无 LLM 分层自动放行 — 把审核成本从 O(条目) 降到 O(来源)。

调研依据（docs/data-acquisition-strategy-2026-08-30.md 杠杆 5）：
量上来后逐条人工审核必然积压（4001 条积压的前车之鉴）。三道闸门全过才自动放行，
任何一道不过保持 PENDING 留给人工：

  闸门 1 来源信誉：该爬虫历史已审核条目 approve 率 ≥ min_pass_rate，且历史量 ≥ min_history
        （历史由数据说话——web_article 0.76 会被挡下，rsshub 1.0 通过）
  闸门 2 质量分：与 bulk_review 同一套规则评分 ≥ min_score（60 = B 级以上，
        高于入库门槛 35，保证自动放行的质量高于人工平均）
  闸门 3 红线：研招网 yz.chsi.com.cn 防御性驳回（入库层已挡，此处兜底可审计）

零 LLM、纯规则，冻结期可用；LLM judge 解冻后可在闸门 2 处插入。
在定时爬虫任务成功落库后调用（见 tasks/crawler_tasks.py），也可 CLI 单跑。
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.crawlers.research.experience_quality import (
    detect_promotion,
    score_experience_item_detailed,
)
from app.crawlers.research.quality import score_item_detailed
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.models.user import User
from app.services.research_promote import promote_external_item

logger = logging.getLogger(__name__)

CHSI_HOST = "yz.chsi.com.cn"
SYSTEM_ADMIN_EMAIL = "system@gradpath.local"

DEFAULT_MIN_SCORE = 60
DEFAULT_MIN_HISTORY = 30
DEFAULT_MIN_PASS_RATE = 0.9


def _score(ext: ExternalResearchItem) -> int:
    """与 bulk_review_real_data 完全一致的规则评分。"""
    meta = ext.external_meta or {}
    if ext.item_type == "experience_post":
        tags = [t for t in (meta.get("tags") or []) if isinstance(t, str)]
        is_promotion, _conf, promo_reason = detect_promotion(ext.title or "", ext.content or "", tags)
        detail = score_experience_item_detailed(
            title=ext.title or "",
            content=ext.content or "",
            source_platform=ext.source_platform or "user",
            source_url=ext.source_url or "",
            external_view_count=int(meta.get("view_count") or 0),
            external_like_count=int(meta.get("like_count") or 0),
            is_promotion=is_promotion,
            promotion_reason=promo_reason,
        )
    else:
        detail = score_item_detailed(
            title=ext.title or "",
            content=ext.content or "",
            summary=meta.get("summary") or "",
            source_url=ext.source_url or "",
        )
    return int(detail["score"])


def source_reputation(db: Session) -> dict[str, dict[str, int]]:
    """各爬虫历史审核画像：{crawler_name: {approved, rejected, pass_rate}}。"""
    rows = (
        db.query(
            ExternalResearchItem.crawler_name,
            ExternalResearchItem.review_status,
        )
        .filter(ExternalResearchItem.review_status.in_(["APPROVED", "REJECTED"]))
        .all()
    )
    stats: dict[str, dict[str, int]] = {}
    for name, status in rows:
        s = stats.setdefault(name, {"approved": 0, "rejected": 0})
        s["approved" if status == "APPROVED" else "rejected"] += 1
    for s in stats.values():
        total = s["approved"] + s["rejected"]
        s["total"] = total
        s["pass_rate"] = round(s["approved"] / total, 4) if total else 0.0
    return stats


def auto_review_pending(
    db: Session,
    min_score: int = DEFAULT_MIN_SCORE,
    min_history: int = DEFAULT_MIN_HISTORY,
    min_pass_rate: float = DEFAULT_MIN_PASS_RATE,
    reviewer_email: str = SYSTEM_ADMIN_EMAIL,
    dry_run: bool = False,
) -> dict:
    """对 PENDING 队列跑三闸门自动放行。返回统计 dict（可审计日志用）。"""
    admin = db.query(User).filter(User.email == reviewer_email).first()
    if admin is None:
        admin = db.query(User).filter(User.is_admin.is_(True)).first()
    if admin is None:
        logger.warning("auto_review: 无可用管理员账号，跳过")
        return {"error": "no_admin"}

    reputation = source_reputation(db)
    pending = (
        db.query(ReviewQueueItem, ExternalResearchItem)
        .join(ExternalResearchItem, ExternalResearchItem.id == ReviewQueueItem.ref_item_id)
        .filter(ReviewQueueItem.review_status == "PENDING")
        .all()
    )

    stats = {
        "pending": len(pending),
        "auto_approved": 0,
        "promoted": 0,
        "gate_reputation": 0,
        "gate_score": 0,
        "chsi_rejected": 0,
    }
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for queue_item, ext in pending:
        if ext is None:
            continue
        # 闸门 3：研招网红线兜底驳回
        if CHSI_HOST in (ext.source_url or ""):
            if not dry_run:
                queue_item.review_status = "REJECTED"
                queue_item.reviewed_by = "auto_review"
                queue_item.reviewed_time = now
                queue_item.reject_reason = "研招网红线：yz.chsi.com.cn 数据不入库、不对外分发"
                ext.review_status = "REJECTED"
            stats["chsi_rejected"] += 1
            continue

        rep = reputation.get(ext.crawler_name or "", {"total": 0, "pass_rate": 0.0})
        if rep["total"] < min_history or rep["pass_rate"] < min_pass_rate:
            stats["gate_reputation"] += 1
            continue
        if _score(ext) < min_score:
            stats["gate_score"] += 1
            continue

        if not dry_run:
            result = promote_external_item(db, ext, "auto_review")
            stats["promoted"] += result.get("promoted", 0)
            queue_item.review_status = "APPROVED"
            queue_item.reviewed_by = "auto_review"
            queue_item.reviewed_time = now
            ext.review_status = "APPROVED"
        stats["auto_approved"] += 1

    if not dry_run:
        db.commit()
    logger.info("auto_review: %s", stats)
    return stats
