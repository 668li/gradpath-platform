"""公考/就业赛道资讯入库（2026-08-16，用户拍板资讯中心接纳多赛道后）。

数据源：unified_scrape_results.json 中此前暂缓的非考研向源——
  公考 6 源：offcn / huatu / fenbi / offcn_shengkao / offcn_teacher / offcn_accounting（1027 篇）
  就业 1 源：51job（13 篇）
暂缓仍未入库：hqwx（医学职业资格）/ mofangge_eng（英语培训）/ eol_gaokao+gaokao_cn（高考，非三赛道）

链路与 import_real_data_crawls.py 一致：transform_rss 质量管线（D 级过滤 + simhash）
→ store_research_items（kaoyan_news, PENDING 审核队列）→ 之后再跑
bulk_review_real_data.py 质量门槛批量审核。
合规：chsi URL 拒收。幂等：source_url 去重（store 内建）。
"""
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.crawlers.research.transformer import ResearchTransformer
from app.database import SessionLocal
from app.models.crawler_run import CrawlerRun
from app.services.research_ingestion import store_research_items

DATA_FILE = BACKEND_ROOT / "app" / "crawlers" / "real_data" / "unified_scrape_results.json"
CHSI_HOST = "yz.chsi.com.cn"
CIVIL_SOURCES = {
    "offcn", "huatu", "fenbi", "offcn_shengkao", "offcn_teacher", "offcn_accounting", "51job",
}


def main() -> None:
    unified = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    raws = []
    chsi_rejected = no_url = 0
    for src_name in CIVIL_SOURCES:
        for a in unified.get("sources", {}).get(src_name, {}).get("articles", []):
            url = str(a.get("url") or "").strip()
            if not url:
                no_url += 1
                continue
            if CHSI_HOST in url:
                chsi_rejected += 1
                continue
            raws.append(
                {
                    "title": a.get("title") or "",
                    "summary": str(a.get("content") or "")[:500],
                    "content": a.get("content") or "",
                    "source_url": url,
                    "source_platform": "web",
                    "category": a.get("category") or "",
                    "published_at": a.get("scraped_at"),
                    "crawled_at": a.get("scraped_at"),
                    "legacy_source": src_name,
                }
            )

    payloads = ResearchTransformer.transform_rss(raws)
    with SessionLocal() as db:
        run_record = CrawlerRun(
            source_name="legacy_civil_news_import",
            category="research",
            status="running",
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)
        result = store_research_items(
            db,
            crawler_name="legacy_civil_news_import",
            item_type="kaoyan_news",
            items=payloads,
            source_platform="web",
            run_id=str(run_record.id),
        )
        run_record.status = "success"
        run_record.items_fetched = len(raws)
        run_record.items_stored = result["inserted"]
        run_record.items_duplicates = result["duplicated"]
        run_record.source_meta = {
            "note": "公考/就业赛道资讯入库（资讯中心多赛道拍板后）",
            "raw_collected": len(raws),
            "quality_filtered": len(raws) - len(payloads),
            "chsi_rejected": chsi_rejected,
            "no_url": no_url,
        }
        db.commit()
    print(
        f"采集 {len(raws)} | 质量过滤 {len(raws) - len(payloads)} | "
        f"入队 {result['inserted']} | 重复 {result['duplicated']} | chsi拒收 {chsi_rejected}"
    )


if __name__ == "__main__":
    main()
