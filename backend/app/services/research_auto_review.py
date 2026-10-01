"""无 LLM 分层自动放行 — 把审核成本从 O(条目) 降到 O(来源)。

调研依据（docs/data-acquisition-strategy-2026-08-30.md 杠杆 5）：
量上来后逐条人工审核必然积压（4001 条积压的前车之鉴）。三道闸门全过才自动放行，
任何一道不过保持 PENDING 留给人工：

  闸门 1 来源信誉：该爬虫历史已审核条目 approve 率 ≥ min_pass_rate，且历史量 ≥ min_history
        （历史由数据说话——web_article 0.76 会被挡下，rsshub 1.0 通过）
  闸门 2 质量分：与 bulk_review 同一套规则评分 ≥ min_score（60 = B 级以上，
        高于入库门槛 35，保证自动放行的质量高于人工平均）
  闸门 3 红线：研招网 yz.chsi.com.cn 防御性驳回（入库层已挡，此处兜底可审计）

另有两条快速放行路径（都仍须过闸门 2 质量分）：
- 官方源快速通道：official_verified + 历史零驳回 + 历史 ≥5 条
- 内容快速通道（2026-10-01）：official_verified + 内容判定属招生情报
  （app/services/admission_content_rule.py，docs/爬取审核策略 §3.1 口径的首个
  代码实现）。只对官方域生效——噪声源不受益，避免放松 rsshub 那类低通过率来源。

零 LLM、纯规则，冻结期可用；LLM judge 解冻后可在闸门 2 处插入。
在定时爬虫任务成功落库后调用（见 tasks/crawler_tasks.py），也可 CLI 单跑：
``scripts/auto_review_queue.py``（默认 dry-run，``--commit`` 才写库，
``--explain`` 输出逐条判定明细供人工抽验定位卡点）。
"""

import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.crawlers.research.experience_quality import (
    detect_promotion,
    score_experience_item_detailed,
)
from app.crawlers.research.quality import score_item_detailed
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.models.user import User
from app.services.admission_content_rule import classify_admission_item
from app.services.research_promote import promote_external_item

logger = logging.getLogger(__name__)

CHSI_HOST = "yz.chsi.com.cn"
SYSTEM_ADMIN_EMAIL = "system@gradpath.local"

DEFAULT_MIN_SCORE = 60
DEFAULT_MIN_HISTORY = 30
DEFAULT_MIN_PASS_RATE = 0.9
# 官方源快速通道：edu.cn/gov.cn（credibility=official_verified）历史驳回为 0 且
# 已审核 ≥ OFFICIAL_MIN_HISTORY 条即可自动放行。否则新官方源会冷启动死锁：
# 没有历史→被信誉闸挡→要凑历史又必须先人工审 30 条。
OFFICIAL_MIN_HISTORY = 5


def _parse_ts(value: object) -> datetime | None:
    """解析采集侧写进 external_meta 的 ISO 时间串；无法解析一律 None（不抛）。

    naive 时间沿用 quality._freshness_score 的既有口径（按 UTC 处理），
    不在这里另立时区语义——口径要改必须单独拍板并加测试。
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        logger.debug("auto_review: 时间串无法解析，按缺失处理: %r", value[:40])
        return None


def _item_times(ext: ExternalResearchItem) -> tuple[datetime | None, datetime | None]:
    """取条目自身的发布时间/采集时间（时效分的数据源，此前漏传导致恒 0 分）。"""
    meta = ext.external_meta or {}
    return _parse_ts(meta.get("published_at")), _parse_ts(meta.get("crawled_at"))


def _score(ext: ExternalResearchItem) -> int:
    """与 bulk_review_real_data 完全一致的规则评分。"""
    meta = ext.external_meta or {}
    if ext.item_type == "experience_post":
        tags = [t for t in (meta.get("tags") or []) if isinstance(t, str)]
        is_promotion, _conf, promo_reason = detect_promotion(
            ext.title or "", ext.content or "", tags
        )
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
        published_at, crawled_at = _item_times(ext)
        detail = score_item_detailed(
            title=ext.title or "",
            content=ext.content or "",
            summary=meta.get("summary") or "",
            source_url=ext.source_url or "",
            published_at=published_at,
            crawled_at=crawled_at,
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


def _host_of(source_url: str | None) -> str:
    """取 source_url 的 hostname（小写），仅用于 explain 明细的可读性。"""
    return (urlparse(source_url or "").hostname or "").lower()


def auto_review_pending(
    db: Session,
    min_score: int = DEFAULT_MIN_SCORE,
    min_history: int = DEFAULT_MIN_HISTORY,
    min_pass_rate: float = DEFAULT_MIN_PASS_RATE,
    reviewer_email: str = SYSTEM_ADMIN_EMAIL,
    dry_run: bool = False,
    explain: bool = False,
    limit: int | None = None,
) -> dict:
    """对 PENDING 队列跑三闸门自动放行。返回统计 dict（可审计日志用）。

    Args:
        explain: True 时在返回 dict 里附 ``details``——逐条判定明细
            （verdict/score/reason），供 dry-run 决策与人工抽验定位卡点。
            默认 False，既有调用方（爬虫任务）零行为变化。
        limit: 只处理队列中最靠前的 N 条（配合确定性排序做小批量灰度）。
    """
    admin = db.query(User).filter(User.email == reviewer_email).first()
    if admin is None:
        admin = db.query(User).filter(User.is_admin.is_(True)).first()
    if admin is None:
        logger.warning("auto_review: 无可用管理员账号，跳过")
        return {"error": "no_admin"}

    reputation = source_reputation(db)
    query = (
        db.query(ReviewQueueItem, ExternalResearchItem)
        .join(ExternalResearchItem, ExternalResearchItem.id == ReviewQueueItem.ref_item_id)
        .filter(ReviewQueueItem.review_status == "PENDING")
        # 确定性排序：同一批 PENDING 两次 dry-run 必须给出同一份清单（逐条 diff 的前提）
        .order_by(ReviewQueueItem.id)
    )
    if limit:
        query = query.limit(limit)
    pending = query.all()

    stats = {
        "pending": len(pending),
        "auto_approved": 0,
        "promoted": 0,
        "gate_reputation": 0,
        "gate_score": 0,
        "chsi_rejected": 0,
        "details": [],
    }
    details: list[dict] = stats["details"]
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def _note(
        ext: ExternalResearchItem | None,
        verdict: str,
        reason: str,
        score: int | None = None,
    ) -> None:
        if not explain or ext is None:
            return
        details.append(
            {
                "ref_item_id": ext.id,
                "item_type": ext.item_type,
                "crawler_name": ext.crawler_name,
                "credibility": ext.credibility,
                "host": _host_of(ext.source_url),
                "title": (ext.title or "")[:120],
                "verdict": verdict,
                "score": score,
                "reason": reason,
            }
        )

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
            _note(ext, "reject_redline", "研招网红线兜底驳回")
            continue

        rep = reputation.get(
            ext.crawler_name or "",
            {"total": 0, "pass_rate": 0.0, "rejected": 0, "approved": 0},
        )
        rejected = rep.get("rejected", 0)
        official_fast_track = (
            rejected == 0
            and (ext.credibility or "") == "official_verified"
            and rep["total"] >= OFFICIAL_MIN_HISTORY
        )
        # 内容快速通道（2026-10-01）：官方域 + 招生情报内容 → 绕过来源信誉闸。
        # 只对 official_verified 生效（噪声源不受益），仍须过质量分闸。
        content_admission = False
        content_reason = ""
        if (ext.credibility or "") == "official_verified":
            content_admission, content_reason = classify_admission_item(ext.title, ext.content)
        if not official_fast_track and not content_admission:
            if rep["total"] < min_history or rep["pass_rate"] < min_pass_rate:
                stats["gate_reputation"] += 1
                _note(
                    ext,
                    "block_reputation",
                    f"来源信誉不足：历史 {rep['total']} 条（门槛 {min_history}）、"
                    f"通过率 {rep['pass_rate']}（门槛 {min_pass_rate}）"
                    + (f"；内容判定：{content_reason}" if content_reason else ""),
                )
                continue
        score = _score(ext)
        if score < min_score:
            stats["gate_score"] += 1
            _note(
                ext,
                "block_score",
                f"质量分 {score} < 门槛 {min_score}",
                score=score,
            )
            continue

        if not dry_run:
            result = promote_external_item(db, ext, "auto_review")
            stats["promoted"] += result.get("promoted", 0)
            queue_item.review_status = "APPROVED"
            queue_item.reviewed_by = "auto_review"
            queue_item.reviewed_time = now
            ext.review_status = "APPROVED"
        stats["auto_approved"] += 1
        if official_fast_track:
            verdict, why = "pass_official_fast_track", "官方源快速通道放行"
        elif content_admission:
            verdict, why = "pass_admission_content", f"招生情报内容放行（{content_reason}）"
        else:
            verdict, why = "pass_standard", "三闸门全过"
        _note(ext, verdict, why, score=score)

    if not dry_run:
        db.commit()
    logger.info("auto_review: %s", {k: v for k, v in stats.items() if k != "details"})
    return stats
