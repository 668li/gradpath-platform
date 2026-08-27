# backend/scripts/import_real_data_to_queue.py
"""真实数据导入审核队列（成熟化补齐计划 Phase B3）。

把 ``app/crawlers/real_data/`` 下的真实抓取数据按 docs/research_mapping.md 的映射规则
批量送入 store_research_items（ExternalResearchItem + ReviewQueueItem，全部 PENDING），
管理员在 /admin/research-queue 人工 confirm 后由 research_promote 落业务表。

合规红线（与 B1/B2 一致，数据必须真实）：
- 只导入真实抓取数据；合成数据（dark_final.json source="seed"、civil_final.json 模板生成）不导入
- 全部走 PENDING 审核队列，不直接写业务表
- 幂等：source_url 唯一索引 + biz_req_no（md5(source_url)）去重，重复运行安全
- 数据来源标注：source_url / source_platform / external_meta 保留行级来源元数据

分组与爬虫名（crawler_runs.source_name，均在 B1 白名单内）：
- bilibili_*             → bilibili_research   / experience_post（B 站经验贴）
- 网页文章（yz/kaoyan/offcn/sina 等）→ web_article_research / kaoyan_news
- college_details.json   → real_data           / kaoyan_news（院校信息）
- v2ex/zhihu 社区帖      → real_data           / experience_post（community 组）

用法：
    py -3.13 scripts/import_real_data_to_queue.py                # dry-run 预览条数
    py -3.13 scripts/import_real_data_to_queue.py --commit       # 实际入库（PENDING）
    py -3.13 scripts/import_real_data_to_queue.py --only web --commit
    py -3.13 scripts/import_real_data_to_queue.py --limit 20
    py -3.13 scripts/import_real_data_to_queue.py --json         # JSON 摘要（测试断言用）
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

# 允许直接从 backend/ 目录运行：python scripts/import_real_data_to_queue.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models.crawler_run import CrawlerRun
from app.services.research_ingestion import store_research_items

REAL_DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "crawlers" / "real_data"

# 内容正文上限（防止整页 HTML dump 撑爆审核队列；确认入库时可再编辑）
MAX_CONTENT_CHARS = 20_000

# 站点壳标题标记：命中则改用 URL 派生的占位标题（webfetch/crawl4ai/firecrawl 类页面 dump）
_SITE_NAME_MARKERS = ("学而思考研帮", "kaoyan.com", "考研网")
_BOILER_RE = re.compile(r"^(上一篇[:：]|下一篇[:：]|未命名文章|$)")


# 适配器：raw 行 → store_research_items 接受的 {title, content, source_url, ...} 字典
# 除核心列（title/content/source_url/source_platform）外全部进 external_meta
def _to_int(value: Any) -> int:
    """宽松转 int；兼容 '1.2万' / '1,234' 等展示形态，失败返回 0。"""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value or "").replace(",", "").strip()
    if not s:
        return 0
    m = re.fullmatch(r"([\d.]+)\s*万", s)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.fullmatch(r"\d+", s)
    return int(m.group()) if m else 0


def _fallback_title(url: str) -> str:
    """无可用标题时，用 URL 路径尾段拼一个确定性的占位标题（同 URL 恒定，幂等友好）。"""
    parts = [p for p in urlparse(url).path.rstrip("/").split("/") if p]
    tail = parts[-1] if parts else ""
    if len(tail) > 8 and tail.isalnum():
        tail = tail[:8]
    return f"网页文章：{tail or 'unknown'}" if tail else "网页文章（无标题）"


def _clean_title(title: str, url: str) -> str:
    """去掉站点壳/上一篇等噪声，必要时回退到 URL 派生标题。"""
    title = title.strip()
    if any(m in title for m in _SITE_NAME_MARKERS):
        return _fallback_title(url)
    stripped = _BOILER_RE.sub("", title).strip()
    return stripped if stripped else _fallback_title(url)


def _first_line_text(md: str) -> str:
    """从 markdown/文本里抠第一行真实文字，用作 summary（供确认入库时展示）。"""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md or "")  # 图片
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # 链接保留文字
    text = re.sub(r"^[#>*\-\s]+", "", text, flags=re.M)
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:300]
    return ""


def _adapter_bilibili(rows: list[dict]) -> list[dict]:
    """B 站经验贴：title/author/views/description/url(/bvid/tags/keyword)。"""
    items: list[dict] = []
    for raw in rows:
        title = str(raw.get("title") or "").strip()
        url = str(raw.get("url") or "").strip()
        if url.startswith("//"):
            url = "https:" + url  # bilibili_round3 抓取时丢了 scheme
        if not title or not url:
            continue
        desc = str(raw.get("description") or "").strip()
        tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
        if not tags and raw.get("keyword"):
            tags = [str(raw["keyword"])]
        items.append(
            {
                "title": title,
                "summary": (desc or title)[:500],
                "content": desc or title,
                "author": str(raw.get("author") or "").strip(),
                "bvid": str(raw.get("bvid") or "").strip(),
                "source_url": url,
                "view_count": _to_int(raw.get("views")),
                "like_count": _to_int(raw.get("likes")),
                "tags": [t for t in tags if isinstance(t, str)][:20],
                "category": "考研经验",
            }
        )
    return items


def _adapter_web(rows: Any, *, channel: str | None = None) -> list[dict]:
    """网页文章：title/url/content(/markdown)，字段名不齐的做兜底。

    channel 用于 unified 聚合包（来源渠道名写进 external_meta 保留来源标注）。
    """
    items: list[dict] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or "").strip()
        content = str(raw.get("content") or raw.get("markdown") or "").strip()
        if not url or not content:
            continue
        title = _clean_title(str(raw.get("title") or ""), url)
        truncated = len(content) > MAX_CONTENT_CHARS
        tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
        if not tags and raw.get("source"):
            tags = [str(raw["source"])]
        item: dict[str, Any] = {
            "title": title,
            "summary": _first_line_text(content),
            "content": content[:MAX_CONTENT_CHARS],
            "source_url": url,
            "category": str(raw.get("category") or raw.get("source") or "考研资讯"),
            "tags": [t for t in tags if isinstance(t, str)][:20],
            "truncated": truncated,
        }
        if channel:
            item["source_channel"] = channel
        if raw.get("date"):
            item["published_at"] = str(raw["date"])
        if raw.get("views"):
            item["view_count"] = _to_int(raw["views"])
        items.append(item)
    return items


def _adapter_unified(data: dict) -> list[dict]:
    """unified_scrape_results.json：{sources: {渠道: {articles: [...]}}} 展平。

    23 个渠道的真实文章（yz.chsi.com.cn / offcn / sina_edu / 51job ...），
    渠道名写入 external_meta.source_channel 保留来源标注。
    """
    items: list[dict] = []
    for channel, bundle in data.items():
        if not isinstance(bundle, dict):
            continue
        items.extend(_adapter_web(bundle.get("articles") or [], channel=channel))
    return items


def _adapter_school(rows: list[dict]) -> list[dict]:
    """院校信息（college_details.json，真实官网数据，source_url 取研究生院/官网）。"""
    items: list[dict] = []
    for raw in rows:
        name = str(raw.get("name") or "").strip()
        url = str(raw.get("graduate_school_url") or raw.get("official_website") or "").strip()
        if not name or not url:
            continue

        def _join(v: Any) -> str:
            if isinstance(v, list):
                return "、".join(str(x) for x in v if str(x).strip())
            return str(v or "").strip()

        parts = []
        if raw.get("province"):
            parts.append(f"省份：{raw['province']}")
        if raw.get("city"):
            parts.append(f"城市：{raw['city']}")
        if raw.get("description"):
            parts.append(str(raw["description"]).strip())
        if raw.get("departments"):
            parts.append(f"院系：{_join(raw['departments'])}")
        if raw.get("key_majors"):
            parts.append(f"优势学科：{_join(raw['key_majors'])}")
        if raw.get("ranking"):
            parts.append(f"排名：{_join(raw['ranking'])}")
        if raw.get("employment_rate"):
            parts.append(f"就业率：{_join(raw['employment_rate'])}")
        if raw.get("phone"):
            parts.append(f"电话：{raw['phone']}")
        if raw.get("email"):
            parts.append(f"邮箱：{raw['email']}")
        tags = [t for t in (raw.get("tags") or []) if isinstance(t, str)] + ["院校信息"]
        items.append(
            {
                "title": f"院校信息：{name}",
                "summary": str(raw.get("description") or "")[:300],
                "content": "\n\n".join(parts) or name,
                "source_url": url,
                "category": "院校信息",
                "tags": tags[:20],
            }
        )
    return items


def _adapter_community(rows: list[dict]) -> list[dict]:
    """社区帖（v2ex topics / zhihu playwright）：title/content/url + 作者等元数据。"""
    items: list[dict] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or "").strip()
        title = str(raw.get("title") or "").strip()
        content = str(raw.get("content") or "").strip()
        if not url or not title or not content:
            continue
        item: dict[str, Any] = {
            "title": title,
            "summary": content[:300],
            "content": content,
            "source_url": url,
            "category": str(raw.get("category") or raw.get("node") or "社区讨论"),
            "tags": [t for t in (raw.get("tags") or []) if isinstance(t, str)][:20],
        }
        for k in ("author", "id", "node", "replies", "created", "source"):
            if raw.get(k) is not None:
                item[k] = raw[k]
        items.append(item)
    return items


# (文件名, 子键/None, 分组, 爬虫名, item_type, source_platform, 适配器)
# 子键 None = 文件顶层即列表；特殊值 "__unified__" = 整个 dict 交给 _adapter_unified
SOURCE_REGISTRY: list[tuple[str, str | None, str, str, str, str, Callable]] = [
    # —— bilibili 经验贴 → experience_post（B 站，user_reported 可信度）——
    (
        "bilibili_expand.json",
        None,
        "bilibili",
        "bilibili_research",
        "experience_post",
        "bilibili",
        _adapter_bilibili,
    ),
    (
        "bilibili_loop.json",
        None,
        "bilibili",
        "bilibili_research",
        "experience_post",
        "bilibili",
        _adapter_bilibili,
    ),
    (
        "bilibili_round3.json",
        None,
        "bilibili",
        "bilibili_research",
        "experience_post",
        "bilibili",
        _adapter_bilibili,
    ),
    (
        "bilibili_data.json",
        "videos",
        "bilibili",
        "bilibili_research",
        "experience_post",
        "bilibili",
        _adapter_bilibili,
    ),
    (
        "crawllee_bilibili.json",
        None,
        "bilibili",
        "bilibili_research",
        "experience_post",
        "bilibili",
        _adapter_bilibili,
    ),
    (
        "crawllee_bilibili2.json",
        None,
        "bilibili",
        "bilibili_research",
        "experience_post",
        "bilibili",
        _adapter_bilibili,
    ),
    (
        "fast_bilibili.json",
        None,
        "bilibili",
        "bilibili_research",
        "experience_post",
        "bilibili",
        _adapter_bilibili,
    ),
    (
        "round5_bilibili.json",
        None,
        "bilibili",
        "bilibili_research",
        "experience_post",
        "bilibili",
        _adapter_bilibili,
    ),
    # —— 网页文章 → kaoyan_news（web，官方域名 → official_verified）——
    (
        "crawl4ai_results.json",
        None,
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "crawlee_kaoyan.json",
        None,
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "crawllee_kaoyan.json",
        None,
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    ("crawllee_yz.json", None, "web", "web_article_research", "kaoyan_news", "web", _adapter_web),
    (
        "kaoyan_crawled.json",
        None,
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    ("kaoyan_round2.json", None, "web", "web_article_research", "kaoyan_news", "web", _adapter_web),
    ("round5_kaoyan.json", None, "web", "web_article_research", "kaoyan_news", "web", _adapter_web),
    ("real_articles.json", None, "web", "web_article_research", "kaoyan_news", "web", _adapter_web),
    ("fast_kaoyan.json", None, "web", "web_article_research", "kaoyan_news", "web", _adapter_web),
    ("fast_yz.json", None, "web", "web_article_research", "kaoyan_news", "web", _adapter_web),
    (
        "school_official.json",
        None,
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    ("yz_articles.json", None, "web", "web_article_research", "kaoyan_news", "web", _adapter_web),
    (
        "yz_articles_round2.json",
        None,
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "yz_articles_round3.json",
        None,
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "round5_yz.json",
        "articles",
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "fast_strategy.json",
        "articles",
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "firecrawl_scraped.json",
        "articles",
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "koolearn_crawled.json",
        "data",
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "webfetch_round2.json",
        "articles",
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "webfetch_round4.json",
        "articles",
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "batch_scrape_results.json",
        "kaoyan",
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "batch_scrape_results.json",
        "yz",
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    (
        "unified_scrape_results.json",
        "__unified__",
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_unified,
    ),
    (
        "civil_service_expanded.json",
        None,
        "web",
        "web_article_research",
        "kaoyan_news",
        "web",
        _adapter_web,
    ),
    # —— 院校信息 → kaoyan_news（web，real_data 爬虫名）——
    ("college_details.json", None, "school", "real_data", "kaoyan_news", "web", _adapter_school),
    # —— 社区帖 → experience_post（v2ex/zhihu，user_reported 可信度）——
    (
        "v2ex_data.json",
        "topics",
        "community",
        "real_data",
        "experience_post",
        "v2ex",
        _adapter_community,
    ),
    (
        "zhihu_playwright.json",
        None,
        "community",
        "real_data",
        "experience_post",
        "zhihu",
        _adapter_community,
    ),
]

# 明确不导入的文件及原因（B3 合规红线：数据必须真实）
EXCLUDED: dict[str, str] = {
    # —— B2 已处理 / 非内容数据 ——
    "salary_real.json": "已由 seed_salary_benchmarks（B2）导入薪资基准表",
    "salary_expand.json": "已由 seed_salary_benchmarks（B2）导入薪资基准表",
    "scoreline_final.json": "分数线数据，由 seed_scorelines（演示标注）管理",
    "scorelines_real_data.json": "分数线结构数据，由 seed_scorelines（演示标注）管理",
    "company_expand.json": "5000 条公司结构化数据，非内容条目",
    "market_expand.json": "496 条市场结构化数据，非内容条目",
    "major_crawled.json": "专业结构列表，非内容条目",
    "job_data.json": "空列表",
    "bilibili_round4.json": "空列表",
    "real_scraped_data.json": "空列表",
    # —— 合成数据（数据必须真实红线，B3 不导入）——
    "dark_final.json": "6225 条全部 source='seed'，确认合成",
    "civil_final.json": "450 条模板生成（标题带序号、正文重复），无真实来源",
    "civil_service_data.json": "爬取元数据字典（sources/statistics），非内容条目",
    # —— 无 source_url（store_research_items 会静默跳过，显式排除）——
    "zhihu_final.json": "200 条无 URL 字段，无法入库",
    "zhihu_kaoyan.json": "37 条无 URL 字段，无法入库",
    "weibo_data.json": "113 条无 URL 字段，无法入库",
    "xiaohongshu_deep.json": "150 条无 URL 字段，无法入库",
    "xiaohongshu_kaoyan.json": "36 条无 URL 字段，无法入库",
    "v2ex_career.json": "55 条无 URL 字段，无法入库",
    "knowledge_deep.json": "3000 条无 URL 字段，无法入库",
    "yanzhao_real_data.json": "院校/专业条目无 URL 字段（研招网数据仅人工查询确认）",
    "kaoyan_real_data.json": "50 条经验贴无 URL 字段，无法入库",
    "kaoyan_school_data.json": "院校/专业/调剂结构字典，无 URL",
    "college_details_round2.json": "20 条无官网 URL 字段，无法入库",
    "round5_colleges.json": "29 条无官网 URL 字段，无法入库",
    "scraped_data.json": "9 条只有站内导航链接（link），无文章 URL",
    # —— 页面垃圾（HTML/CSS 外壳或整页 dump，无正文标题）——
    "college_loop.json": "599 条 HTML/CSS 垃圾",
    "fast_colleges.json": "149 条 HTML/CSS 垃圾",
    "webfetch_articles.json": "50 条整页 HTML dump，无正文标题（round2/4 已并入干净版本）",
    "webfetch_round3.json": "30 条仅存 content_length，正文未落盘，无内容可入库",
    "firecrawl_loop.json": "33 条含首页 URL，32/33 标题为站点壳",
    "sina_koolearn.json": "2 条为频道首页 dump，无标题",
    # —— 爬取索引/中间件，非文章内容 ——
    "adjust_crawled.json": "调剂抓取元数据",
    "discovered_urls.json": "URL 列表，无内容",
    "yz_loop.json": "研招网栏目索引，无文章正文",
    "yz_round2.json": "研招网栏目索引，无文章正文",
    "yz_crawled.json": "研招网栏目索引，无文章正文",
    "bilibili_round2.json": "关键词 API 抓取统计，无视频列表",
    "batch_scrape_results.json[intel]": "240 条院校情报结构化数据，非内容条目",
    "batch_scrape_results.json[scorelines]": "240 条分数线结构化数据，非内容条目",
}


def _load_rows(filename: str, subkey: str | None) -> list[dict]:
    """按子键解包 JSON；统一 utf-8-sig 兼容 BOM（webfetch/yz_articles_round3）。"""
    path = REAL_DATA_DIR / filename
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    if subkey is None:
        return data if isinstance(data, list) else []
    if subkey == "__unified__":
        return data.get("sources") or {} if isinstance(data, dict) else {}
    if isinstance(data, dict):
        rows = data.get(subkey)
        return rows if isinstance(rows, list) else []
    return []


def _parse_items(filename: str, subkey: str | None, adapter: Callable, limit: int) -> list[dict]:
    """读取 + 适配为 store_research_items 可用的条目列表（--limit 截断）。"""
    rows = _load_rows(filename, subkey)
    items = adapter(rows)
    if limit > 0:
        items = items[:limit]
    return items


def main() -> None:
    parser = argparse.ArgumentParser(
        description="把 real_data/*.json 真实数据批量送进 PENDING 审核队列（B3）"
    )
    parser.add_argument("--commit", action="store_true", help="实际入库（默认 dry-run 预览）")
    parser.add_argument("--only", help="只处理指定分组，逗号分隔：bilibili,web,school,community")
    parser.add_argument("--limit", type=int, default=0, help="每个文件最多处理 N 条（测试用）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 摘要（供测试断言）")
    args = parser.parse_args()

    only_groups = {g.strip() for g in args.only.split(",")} if args.only else None
    registry = [e for e in SOURCE_REGISTRY if only_groups is None or e[2] in only_groups]
    if not registry:
        parser.error(f"--only 无匹配分组: {args.only}")

    per_file: dict[str, dict] = {}
    for filename, subkey, group, crawler, item_type, platform, adapter in registry:
        tag = filename if subkey is None else f"{filename}[{subkey}]"
        try:
            items = _parse_items(filename, subkey, adapter, args.limit)
            per_file[tag] = {
                "group": group,
                "crawler": crawler,
                "item_type": item_type,
                "platform": platform,
                "items": len(items),
                "items_list": items,  # commit 阶段直接复用，避免二次解析
                "inserted": 0,
                "duplicated": 0,
            }
        except FileNotFoundError as e:
            per_file[tag] = {"group": group, "error": str(e)}
        except Exception as e:  # JSON 解析等单文件失败不阻塞整批
            per_file[tag] = {"group": group, "error": f"{type(e).__name__}: {e}"}

    if not args.commit:
        # —— dry-run：只预览条数，不触碰数据库 ——
        summary = {"mode": "dry-run", "files": per_file, "totals": {}}
        for group in sorted({e[2] for e in registry}):
            summary["totals"][group] = sum(
                f["items"]
                for f in per_file.values()
                if f.get("group") == group and "error" not in f
            )
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return
        print(f"=== dry-run（未写库）===")
        for tag, info in per_file.items():
            if "error" in info:
                print(f"  [{info['group']:10s}] {tag:45s} ERROR {info['error']}")
            else:
                print(f"  [{info['group']:10s}] {tag:45s} {info['items']:5d} 条")
        print(f"\n合计（可入库 PENDING）: {sum(summary['totals'].values())} 条")
        for group, n in summary["totals"].items():
            print(f"  {group:10s}: {n} 条")
        print("加 --commit 实际入库（幂等，可重复运行）。")
        return

    # —— commit：每组建一条 CrawlerRun，再走 store_research_items（PENDING）——
    db = SessionLocal()
    try:
        now = datetime.now().isoformat(timespec="seconds")
        for tag, info in per_file.items():
            if "error" in info:
                continue
            items = info["items_list"]
            run_record = CrawlerRun(
                source_name=info["crawler"],
                category=info["group"],
                status="running",
            )
            db.add(run_record)
            db.commit()
            db.refresh(run_record)
            try:
                result = store_research_items(
                    db,
                    crawler_name=info["crawler"],
                    item_type=info["item_type"],
                    items=items,
                    source_platform=info["platform"],
                    run_id=str(run_record.id),
                )
                run_record.status = "success"
                run_record.items_fetched = len(items)
                run_record.items_stored = result["inserted"]
                run_record.items_duplicates = result["duplicated"]
                run_record.stored_count = result["inserted"]
                run_record.duplicate_count = result["duplicated"]
                run_record.source_meta = {
                    "script": "import_real_data_to_queue",
                    "file": tag,
                    "imported_at": now,
                }
                db.commit()
                info["inserted"] = result["inserted"]
                info["duplicated"] = result["duplicated"]
            except Exception:
                db.rollback()
                run_record.status = "failed"
                run_record.error_count = 1
                run_record.source_meta = {"script": "import_real_data_to_queue", "file": tag}
                db.commit()
                info["error"] = "入库失败（已回滚该文件）"
        print("=== commit 完成（全部 PENDING，待人工确认）===")
        total = sum(i["inserted"] for i in per_file.values())
        dup = sum(i["duplicated"] for i in per_file.values())
        for tag, info in per_file.items():
            if "error" in info:
                print(f"  [{info['group']:10s}] {tag:45s} ERROR {info['error']}")
            else:
                print(
                    f"  [{info['group']:10s}] {tag:45s} 入库 {info['inserted']:5d} / 去重 {info['duplicated']:5d}"
                )
        print(f"\n本次新增 PENDING 条目: {total}（重复跳过 {dup}）")
    finally:
        db.close()


if __name__ == "__main__":
    main()
