"""历史队列批量审核（2026-08-16 数据冲刺）：处理 7 月入库后积压的 4001 条 PENDING。

复用与审核 API 完全相同的逻辑（promote_external_item + _apply_review 语义），
审核人 = 本地管理员，幂等（只处理 PENDING）：

  阶段 A — 研招网红线：source_url 含 yz.chsi.com.cn 的 PENDING 条目一律驳回
           （理由写明红线，条目保留可审计，绝不 promote / 对外分发）。
  阶段 B — 质量门槛批量通过：
           - kaoyan_news：score_item_detailed 预打分 ≥ 35（C 级以上，与入库阈值一致）
           - experience_post：score_experience_item_detailed（含 detect_promotion 输入，
             与 promote 同参）≥ 35
           通过 → promote_external_item 落业务表（Phase I：quality_reasons + 证据链自动注入）
           低于阈值 → 保持 PENDING（留给管理员人工决定，不代做判断）
  批量提交：每 100 条 commit 一次，避免长事务。
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.crawlers.research.experience_quality import (
    detect_promotion,
    score_experience_item_detailed,
)
from app.crawlers.research.quality import score_item_detailed
from app.database import SessionLocal
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.models.user import User
from app.services.research_ingestion import QUALITY_MIN_SCORE
from app.services.research_promote import promote_external_item

CHSI_HOST = "yz.chsi.com.cn"
ADMIN_EMAIL = "localadmin@gradpath.com"
BATCH = 100


def _apply_review(queue_item, ext_item, new_status: str, admin, reject_reason=None) -> None:
    """与 app/api/admin/research_queue.py:_apply_review 相同语义（不 commit）。"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    queue_item.review_status = new_status
    queue_item.reviewed_by = admin.email
    queue_item.reviewed_time = now
    if reject_reason is not None:
        queue_item.reject_reason = reject_reason
    if ext_item is not None:
        ext_item.review_status = new_status


def _news_score(ext) -> int:
    meta = ext.external_meta or {}
    detail = score_item_detailed(
        title=ext.title or "",
        content=ext.content or "",
        summary=meta.get("summary") or "",
        source_url=ext.source_url or "",
    )
    return int(detail["score"])


def _exp_score(ext) -> int:
    meta = ext.external_meta or {}
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
    return int(detail["score"])


def main() -> None:
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if admin is None or not admin.is_admin:
            print(f"!! 管理员 {ADMIN_EMAIL} 不存在或非管理员，先运行 bootstrap_local_admin.py")
            return

        rows = (
            db.query(ReviewQueueItem, ExternalResearchItem)
            .join(ExternalResearchItem, ExternalResearchItem.id == ReviewQueueItem.ref_item_id)
            .filter(ReviewQueueItem.review_status == "PENDING")
            .all()
        )
        print(f"PENDING 总数: {len(rows)}")

        stats = {
            "chsi_rejected": 0,
            "approved": 0,
            "promoted": 0,
            "promote_skipped_dup": 0,
            "below_threshold_kept": 0,
            "no_ext_item": 0,
        }
        pending_since_commit = 0

        for queue_item, ext in rows:
            if ext is None:
                stats["no_ext_item"] += 1
                continue

            # 阶段 A：chsi 红线驳回
            if CHSI_HOST in (ext.source_url or ""):
                _apply_review(
                    queue_item,
                    ext,
                    "REJECTED",
                    admin,
                    reject_reason="研招网红线：yz.chsi.com.cn 数据不入库、不对外分发",
                )
                stats["chsi_rejected"] += 1

            # 阶段 B：质量门槛通过
            else:
                try:
                    score = _news_score(ext) if ext.item_type == "kaoyan_news" else _exp_score(ext)
                except Exception:
                    score = 0
                if score < QUALITY_MIN_SCORE:
                    stats["below_threshold_kept"] += 1
                    continue
                result = promote_external_item(db, ext, admin.email)
                _apply_review(queue_item, ext, "APPROVED", admin)
                stats["approved"] += 1
                stats["promoted"] += result.get("promoted", 0)
                stats["promote_skipped_dup"] += result.get("skipped", 0)

            pending_since_commit += 1
            if pending_since_commit >= BATCH:
                db.commit()
                pending_since_commit = 0
                print(
                    f"  进度: chsi驳回 {stats['chsi_rejected']} | 通过 {stats['approved']}"
                    f" | 落库 {stats['promoted']} | 低质保留 {stats['below_threshold_kept']}"
                )

        db.commit()
        print("完成:", stats)


if __name__ == "__main__":
    main()
