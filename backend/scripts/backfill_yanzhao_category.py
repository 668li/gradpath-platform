# backend/scripts/backfill_yanzhao_category.py
"""研招公告 category 一次性回填（2026-10-01 机制断修复的存量部分）。

背景：官方公告线（official_announce，36 栏目/每小时）此前在 transform_rss 里被
_infer_news_category 覆盖为 general/政策 等，而 grad_intel 院校公告接口按
``category LIKE '研招公告%'`` 过滤——官方线已批准存量在该接口全部不可见。
代码修复（transformer 保留显式打标 + 爬虫按线打标）只管新数据；本脚本回填存量：

1. ``kaoyan_news``：已 approved 且 source_url 能对上 official_announce 已批准 ext 条目、
   category 不带「研招公告」前缀的行 → 改为「研招公告·{栏目}」（栏目缺失则裸「研招公告」）；
2. ``t_external_research_item``：official_announce 的 PENDING 条目，external_meta.category
   不带前缀的 → 同规则写入（否则将来 promote 仍会落错 category）。

安全设计：默认 dry-run 只打印将改动的行；``--commit`` 才写库；幂等（带前缀的跳过）。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: F401

from app.database import SessionLocal
from app.models.ingestion import ExternalResearchItem
from app.models.kaoyan_news import KaoyanNews

PREFIX = "研招公告"


def _stamp(source_name: str | None) -> str:
    base = f"{PREFIX}·{source_name}" if source_name else PREFIX
    return base[:50]


def main() -> None:
    parser = argparse.ArgumentParser(description="回填研招公告 category（默认 dry-run）")
    parser.add_argument("--commit", action="store_true", help="实际写库（默认 dry-run 预览）")
    parser.add_argument("--json", action="store_true", help="JSON 摘要（供测试断言）")
    args = parser.parse_args()

    stats = {"news_updated": 0, "ext_meta_updated": 0, "skipped_already_stamped": 0}
    changes: list[dict] = []

    with SessionLocal() as db:
        # 栏目名映射：official_announce 已批准 ext 条目 source_url → meta.source_name
        url_to_source: dict[str, str | None] = {}
        for url, source_name in (
            db.query(ExternalResearchItem.source_url, ExternalResearchItem.external_meta)
            .filter(
                ExternalResearchItem.crawler_name == "official_announce",
                ExternalResearchItem.review_status == "APPROVED",
                ExternalResearchItem.deleted.is_(False),
            )
            .all()
        ):
            meta = source_name or {}
            url_to_source[url] = meta.get("source_name") if isinstance(meta, dict) else None

        # 1) 业务表回填
        news_rows = (
            db.query(KaoyanNews)
            .filter(KaoyanNews.status == "approved", KaoyanNews.source_url.in_(url_to_source))
            .all()
        )
        for row in news_rows:
            if (row.category or "").startswith(PREFIX):
                stats["skipped_already_stamped"] += 1
                continue
            new_cat = _stamp(url_to_source.get(row.source_url))
            changes.append({"table": "kaoyan_news", "id": str(row.id), "old": row.category, "new": new_cat})
            if args.commit:
                row.category = new_cat
            stats["news_updated"] += 1

        # 2) PENDING 条目 external_meta 回填（promote 时按 meta.category 落业务表）
        pending_rows = (
            db.query(ExternalResearchItem)
            .filter(
                ExternalResearchItem.crawler_name == "official_announce",
                ExternalResearchItem.review_status == "PENDING",
                ExternalResearchItem.deleted.is_(False),
            )
            .all()
        )
        for ext in pending_rows:
            meta = dict(ext.external_meta or {})
            if (meta.get("category") or "").startswith(PREFIX):
                stats["skipped_already_stamped"] += 1
                continue
            new_cat = _stamp(meta.get("source_name"))
            changes.append({"table": "ext_meta", "id": str(ext.id), "old": meta.get("category"), "new": new_cat})
            if args.commit:
                meta["category"] = new_cat
                ext.external_meta = meta  # 整体重赋值，确保 JSON 变更被 SQLAlchemy 检测
            stats["ext_meta_updated"] += 1

        if args.commit:
            db.commit()

    summary = {"mode": "commit" if args.commit else "dry-run", **stats, "changes": changes}
    if args.json:
        import json

        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return

    print(f"=== {'实际写库' if args.commit else 'dry-run（未写库）'} ===")
    print(
        f"kaoyan_news 回填 {stats['news_updated']} 行 | PENDING meta 回填 "
        f"{stats['ext_meta_updated']} 条 | 已带前缀跳过 {stats['skipped_already_stamped']}"
    )
    for c in changes[:20]:
        print(f"  [{c['table']}] {c['old']!r} -> {c['new']!r}")
    if len(changes) > 20:
        print(f"  ... 其余 {len(changes) - 20} 条略")
    if not args.commit:
        print("\n加 --commit 实际写库（幂等，可重复运行）。")


if __name__ == "__main__":
    main()
