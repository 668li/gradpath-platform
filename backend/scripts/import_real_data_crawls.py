"""历史真爬数据入库（2026-08-16 数据冲刺）：只导入经盘点的真实爬取数据。

数据源（backend/app/crawlers/real_data/，7 月 12–18 日多轮爬取）：
  1) college_details.json (599 院校)            → schools 直接入库（name 幂等）
  2) scorelines_real_data.json (55 国家线+127 院校线) → grad_scoreline_records
     （(university_name, major_name, year) 幂等；国家线 university_name='国家线' 诚实标注）
  3) 考研向资讯（unified 4 源 + koolearn/kaoyan/webfetch/firecrawl）
     → transform_rss 质量管线 → store_research_items（kaoyan_news, PENDING 审核队列）
  4) bilibili_loop.json (600 视频元数据)          → store_research_items
     （experience_post, PENDING；仅元数据+简介+外链，符合 B 站红线）

合规红线（本脚本强制）：
  - yz.chsi.com.cn 来源一律拒收并计数（研招网数据绝不入库）
  - 只导真爬文件；合成/生成数据（salary/company/dark/knowledge/market 等）不碰
  - 公考源（offcn 系 977 篇）/高考源/教育资讯源暂缓（无对应业务流，文件保留）
  - 全程 ORM 参数绑定；幂等可重复执行
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.crawlers.research.transformer import ResearchTransformer
from app.database import SessionLocal
from app.models.crawler_run import CrawlerRun
from app.models.grad_intel import GradScorelineRecord
from app.models.school import School
from app.services.research_ingestion import store_research_items

DATA_DIR = Path(__file__).resolve().parent.parent / "app" / "crawlers" / "real_data"

CHSI_HOST = "yz.chsi.com.cn"

# unified 里考研向源白名单（其余源：公考/高考/教育资讯暂缓，文件保留）
UNIFIED_KAOYAN_SOURCES = {"sina_edu", "eol_kaoyan", "gaokao_cn", "mofangge"}


def _load(fname: str):
    """BOM 容错 JSON 加载。"""
    with open(DATA_DIR / fname, encoding="utf-8-sig") as f:
        return json.load(f)


def _is_forbidden(url: str) -> bool:
    return CHSI_HOST in str(url or "")


def _to_int(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 1) 院校库 → schools
# ---------------------------------------------------------------------------
def _level_from_tags(tags: list) -> str | None:
    s = " ".join(str(t) for t in tags or [])
    if "985" in s:
        return "985"
    if "211" in s:
        return "211"
    if "双一流" in s:
        return "双一流"
    return None


def import_schools(db) -> dict:
    rows = _load("college_details.json")
    inserted = skipped_dup = skipped_bad = 0
    for r in rows:
        name = str(r.get("name") or "").strip()
        if not name or len(name) > 100:
            skipped_bad += 1
            continue
        if db.query(School.id).filter(School.name == name).first():
            skipped_dup += 1
            continue
        tags = r.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        db.add(
            School(
                name=name,
                slug="sch-" + hashlib.sha256(name.encode()).hexdigest()[:10],
                code=str(r.get("id") or "")[:10] or None,
                province=str(r.get("province") or "")[:20] or None,
                level=_level_from_tags(tags),
                report_index_url=str(r.get("graduate_school_url") or r.get("official_website") or "") or None,
                key_majors={"city": r.get("city"), "tags": tags} if (r.get("city") or tags) else None,
            )
        )
        inserted += 1
    db.commit()
    return {"inserted": inserted, "duplicated": skipped_dup, "skipped_bad": skipped_bad}


# ---------------------------------------------------------------------------
# 2) 分数线 → grad_scoreline_records
# ---------------------------------------------------------------------------
def import_scorelines(db) -> dict:
    d = _load("scorelines_real_data.json")
    inserted = duplicated = 0
    seen: set[tuple] = set()
    for key, default_uni in (("national_lines", "国家线"), ("university_scorelines", None)):
        for r in d.get(key) or []:
            uni = str(r.get("university") or default_uni or "").strip()
            major = str(r.get("major") or "").strip()
            year = _to_int(r.get("year"))
            if not uni or not major or not year:
                continue
            k = (uni, major, year, str(r.get("degree_type") or ""))
            if k in seen:
                duplicated += 1
                continue
            exists = (
                db.query(GradScorelineRecord.id)
                .filter(
                    GradScorelineRecord.university_name == uni,
                    GradScorelineRecord.major_name == major,
                    GradScorelineRecord.year == year,
                )
                .first()
            )
            if exists:
                duplicated += 1
                continue
            seen.add(k)
            db.add(
                GradScorelineRecord(
                    university_name=uni[:200],
                    major_name=major[:200],
                    degree_type=str(r.get("degree_type") or "")[:50] or None,
                    year=year,
                    total_score_line=_to_int(r.get("total")),
                    politics_score=_to_int(r.get("politics")),
                    foreign_language_score=_to_int(r.get("english")),
                    business_1_score=_to_int(r.get("major1")),
                    business_2_score=_to_int(r.get("major2")),
                    data_sources=["scorelines_real_data.json:2026-07-12"],
                )
            )
            inserted += 1
    db.commit()
    return {"inserted": inserted, "duplicated": duplicated}


# ---------------------------------------------------------------------------
# 3) 考研向资讯 → transform_rss → 审核队列（kaoyan_news）
# ---------------------------------------------------------------------------
def _collect_news_raws() -> tuple[list[dict], dict]:
    """汇总考研向资讯原始条目（含 chsi 过滤）。返回 (raws, 统计)。"""
    raws: list[dict] = []
    stats = {"chsi_rejected": 0, "no_url": 0}

    # unified 4 个考研向源
    unified = _load("unified_scrape_results.json")
    for src_name in UNIFIED_KAOYAN_SOURCES:
        for a in unified.get("sources", {}).get(src_name, {}).get("articles", []):
            url = str(a.get("url") or "").strip()
            if not url:
                stats["no_url"] += 1
                continue
            if _is_forbidden(url):
                stats["chsi_rejected"] += 1
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

    # koolearn（新东方考研）
    kd = _load("koolearn_crawled.json")
    for r in kd.get("data") or []:
        url = str(r.get("url") or "").strip()
        if not url:
            stats["no_url"] += 1
            continue
        if _is_forbidden(url):
            stats["chsi_rejected"] += 1
            continue
        raws.append(
            {
                "title": r.get("title") or "",
                "summary": str(r.get("markdown") or "")[:500],
                "content": r.get("markdown") or "",
                "source_url": url,
                "source_platform": "web",
                "published_at": None,
                "legacy_source": "koolearn",
            }
        )

    # kaoyan.com 直爬（首页 dump，质量过滤自然淘汰低质项）
    for r in _load("kaoyan_crawled.json"):
        url = str(r.get("url") or "").strip()
        if not url or _is_forbidden(url):
            stats["chsi_rejected" if url else "no_url"] += 1
            continue
        raws.append(
            {
                "title": r.get("title") or "",
                "summary": str(r.get("content") or "")[:500],
                "content": r.get("content") or "",
                "source_url": url,
                "source_platform": "web",
                "published_at": None,
                "legacy_source": "kaoyan",
            }
        )

    # webfetch（kaoyan.com 文章，无独立标题字段 → 正文首行启发式）
    for r in _load("webfetch_articles.json"):
        url = str(r.get("url") or "").strip()
        if not url or _is_forbidden(url):
            stats["chsi_rejected" if url else "no_url"] += 1
            continue
        content = str(r.get("content") or "")
        first_line = next((ln.strip(" #*>\t ") for ln in content.splitlines() if ln.strip(" #*>\t ")), "")
        title = (r.get("title") or first_line or "")[:120]
        raws.append(
            {
                "title": title,
                "summary": content[:500],
                "content": content,
                "source_url": url,
                "source_platform": "web",
                "published_at": None,
                "legacy_source": "webfetch",
                "title_extracted": not r.get("title"),
            }
        )

    # firecrawl（kaoyan.com 为主，剔除混入的 chsi）
    fd = _load("firecrawl_scraped.json")
    for r in fd.get("articles") or []:
        url = str(r.get("url") or "").strip()
        if not url or _is_forbidden(url):
            stats["chsi_rejected" if url else "no_url"] += 1
            continue
        raws.append(
            {
                "title": r.get("title") or "",
                "summary": str(r.get("content") or "")[:500],
                "content": r.get("content") or "",
                "source_url": url,
                "source_platform": "web",
                "published_at": None,
                "legacy_source": "firecrawl",
            }
        )
    return raws, stats


def import_news_queue(db) -> dict:
    raws, stats = _collect_news_raws()
    # transform_rss：质量打分 + 分类 + D 级过滤（低于阈值的自然淘汰）
    payloads = ResearchTransformer.transform_rss(raws)
    run_record = CrawlerRun(
        source_name="legacy_news_import",
        category="research",
        status="running",
    )
    db.add(run_record)
    db.commit()
    db.refresh(run_record)
    result = store_research_items(
        db,
        crawler_name="legacy_news_import",
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
        "note": "2026-08-16 历史真爬数据入库（real_data/ 多文件）",
        "raw_collected": len(raws),
        "quality_filtered": len(raws) - len(payloads),
        **stats,
    }
    db.commit()
    return {**result, "raw_collected": len(raws), "quality_filtered": len(raws) - len(payloads), **stats}


# ---------------------------------------------------------------------------
# 4) B 站视频元数据 → 审核队列（experience_post）
# ---------------------------------------------------------------------------
def import_bilibili_queue(db) -> dict:
    rows = _load("bilibili_loop.json")
    items = []
    chsi_rejected = 0
    for r in rows:
        url = str(r.get("url") or "").strip()
        if not url or _is_forbidden(url):
            chsi_rejected += 1
            continue
        desc = str(r.get("description") or "")
        keyword = str(r.get("keyword") or "").strip()
        items.append(
            {
                "title": str(r.get("title") or "")[:300],
                "summary": desc[:500],
                "content": desc,  # B 站红线：仅元数据 + 简介 + 外链
                "author": r.get("author") or "",
                "source_url": url,
                "view_count": _to_int(r.get("views")) or 0,
                "like_count": 0,
                "tags": [keyword] if keyword else [],
                "category": "考研经验",
                "source_platform": "bilibili",
            }
        )
    run_record = CrawlerRun(
        source_name="legacy_bilibili_import",
        category="research",
        status="running",
    )
    db.add(run_record)
    db.commit()
    db.refresh(run_record)
    result = store_research_items(
        db,
        crawler_name="legacy_bilibili_import",
        item_type="experience_post",
        items=items,
        source_platform="bilibili",
        run_id=str(run_record.id),
    )
    run_record.status = "success"
    run_record.items_fetched = len(items)
    run_record.items_stored = result["inserted"]
    run_record.items_duplicates = result["duplicated"]
    run_record.source_meta = {"note": "bilibili_loop.json 600 条视频元数据（2026-08-16 入库）"}
    db.commit()
    return {**result, "chsi_rejected": chsi_rejected}


def main() -> None:
    with SessionLocal() as db:
        print("[1/4] 院校库 → schools")
        print("   ", import_schools(db))
        print("[2/4] 分数线 → grad_scoreline_records")
        print("   ", import_scorelines(db))
        print("[3/4] 考研向资讯 → 审核队列（kaoyan_news）")
        print("   ", import_news_queue(db))
        print("[4/4] B 站视频元数据 → 审核队列（experience_post）")
        print("   ", import_bilibili_queue(db))
    print("完成（幂等：重复执行按去重键跳过）")


if __name__ == "__main__":
    main()
