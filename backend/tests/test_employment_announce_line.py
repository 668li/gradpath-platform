# backend/tests/test_employment_announce_line.py
"""就业公告线（EMP-3，2026-09-30）：参数化四处 + 白名单/契约 + 端点 + fixture 守护。

对应任务书：《就业专项任务书-2026-09-30.md》§EMP-3。
标定证据：docs/就业爬取类型调研-2026-09-30.md（4 校 parse_list_generic 实测）。
"""

import re
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.crawlers.compliance import ALLOWED_CRAWLER_SOURCES, is_allowed_crawler
from app.crawlers.line_registry import load_lines
from app.crawlers.registry import get_crawler
from app.crawlers.research.employment_announce_crawler import (
    EMPLOYMENT_SECTIONS,
    EmploymentAnnounceCrawler,
)
from app.crawlers.research.official_announce_crawler import (
    OfficialAnnounceCrawler,
    _load_known_urls,
    parse_list_generic,
)
from app.models.ingestion import ExternalResearchItem
from app.services.research_ingestion import _load_research_dedup_baseline
from app.services.research_promote import _FRESHNESS_SOURCE_ALIASES

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "employment_announce"


# ----------------------------------------------------------------------
# 1. fixture 守护解析（≥2 真实样本：中南/河工大，2026-09-30 录制）
# ----------------------------------------------------------------------
class TestFixtureParsing:
    def test_csu_list_parses_at_least_5(self):
        html = (FIXTURE_DIR / "csu_list.html").read_text(encoding="utf-8", errors="ignore")
        entries = parse_list_generic(
            html, "https://career.csu.edu.cn/news/index/tag/tzgg"
        )
        assert len(entries) >= 5
        rx = re.compile(r"/news/view/aid/\d+/tag/tzgg$")
        kept = [e for e in entries if rx.search(e["url"])]
        assert len(kept) >= 5
        # 日期证据齐（YYYY-MM-DD）
        assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]) for e in kept)

    def test_hebut_list_parses_at_least_5(self):
        html = (FIXTURE_DIR / "hebut_list.html").read_text(encoding="utf-8", errors="ignore")
        entries = parse_list_generic(
            html, "https://career.hebut.edu.cn/news/index.html"
        )
        assert len(entries) >= 5
        rx = re.compile(r"/news/content/id/\d+\.html$")
        kept = [e for e in entries if rx.search(e["url"])]
        assert len(kept) >= 5

    def test_sections_reference_validated_urls(self):
        """sections 的 4 个栏目 URL 必须来自 EMP-2 标定（edu.cn 域，非猜测）。"""
        assert len(EMPLOYMENT_SECTIONS) == 4
        for s in EMPLOYMENT_SECTIONS:
            assert s["list_url"].startswith("https://")
            assert ".edu.cn/" in s["list_url"]
            assert s["cms"] == "generic"


# ----------------------------------------------------------------------
# 2. 白名单不变量 + 线契约
# ----------------------------------------------------------------------
class TestComplianceAndContract:
    def test_whitelist_contains_employment_line(self):
        assert "employment_announce" in ALLOWED_CRAWLER_SOURCES
        assert is_allowed_crawler("employment_announce")

    def test_unknown_source_rejected(self):
        assert not is_allowed_crawler("employment_announce_evil_twin")
        assert not is_allowed_crawler("")

    def test_line_contract_loads(self):
        lines = load_lines()
        assert "employment_announce" in lines
        line = lines["employment_announce"]
        assert line.schedule == "30 * * * *"  # 与考研线 0 点错峰
        assert line.sla_hours == 24
        assert line.raw.get("rate_limit") == 2.5  # 任务书明确值
        assert line.enabled

    def test_registry_has_crawler(self):
        cls = get_crawler("employment_announce")
        assert cls is EmploymentAnnounceCrawler


# ----------------------------------------------------------------------
# 3. 参数化四处（考研线默认行为不变是硬断言）
# ----------------------------------------------------------------------
class TestParameterization:
    def test_param1_item_type_class_attribute(self):
        # ① 子类分流到就业语义；基类（考研线）默认不变
        assert EmploymentAnnounceCrawler.item_type == "employment_announce"
        assert OfficialAnnounceCrawler.item_type == "kaoyan_news"

    def test_param2_known_urls_isolated_by_line(self, db_session: Session, monkeypatch):
        # ② 增量基线按线隔离：就业线的已知 URL 集不含考研条目，反之亦然
        db_session.add_all(
            [
                ExternalResearchItem(
                    crawler_name="official_announce",
                    crawler_run_id="run-k",
                    item_type="kaoyan_news",
                    title="考研条目",
                    content="考研正文",
                    source_url="https://yjs.example.edu.cn/k1.htm",
                    source_platform="official",
                    review_status="APPROVED",
                ),
                ExternalResearchItem(
                    crawler_name="employment_announce",
                    crawler_run_id="run-e",
                    item_type="employment_announce",
                    title="就业条目",
                    content="就业正文",
                    source_url="https://career.example.edu.cn/e1.htm",
                    source_platform="official",
                    review_status="APPROVED",
                ),
            ]
        )
        db_session.commit()

        kaoyan_urls = _load_research_dedup_baseline(db_session, "kaoyan_news")[1]
        emp_urls = _load_research_dedup_baseline(db_session, "employment_announce")[1]
        assert any("k1.htm" in u for u in kaoyan_urls)
        assert not any("e1.htm" in u for u in kaoyan_urls)
        assert any("e1.htm" in u for u in emp_urls)
        assert not any("k1.htm" in u for u in emp_urls)

    def test_param2_load_known_urls_uses_item_type(self, monkeypatch):
        # ② 爬虫侧入口按 self.item_type 取基线（拦"子类共用考研基线"回归）
        from app.services import research_ingestion as ri

        captured = {}

        def fake_baseline(db, item_type):
            captured["item_type"] = item_type
            return [], {f"https://x.edu.cn/{item_type}.htm"}

        monkeypatch.setattr(ri, "_load_research_dedup_baseline", fake_baseline)
        # official_announce_crawler 通过模块名引用，patch 源头后重建入口函数行为
        import importlib
        import app.crawlers.research.official_announce_crawler as oac

        monkeypatch.setattr(oac, "_load_research_dedup_baseline", fake_baseline)
        urls = oac._load_known_urls("employment_announce")
        assert captured["item_type"] == "employment_announce"
        assert urls == {"https://x.edu.cn/employment_announce.htm"}

    def test_param3_dedup_baseline_types_constant(self):
        from app.services.research_ingestion import _DEDUP_BASELINE_TYPES

        assert "kaoyan_news" in _DEDUP_BASELINE_TYPES
        assert "employment_announce" in _DEDUP_BASELINE_TYPES
        # 其他类型（如 experience_post）不在提纯基线范围
        assert "experience_post" not in _DEDUP_BASELINE_TYPES

    def test_param4_freshness_alias(self):
        assert _FRESHNESS_SOURCE_ALIASES["employment_announce"] == "employment_announce"
        # 考研线别名行为不变
        assert _FRESHNESS_SOURCE_ALIASES["web_article_research"] == "kaoyan"

    def test_parse_passes_source_name_through_transformer(self):
        # transform_rss 只出白名单字段（category 还会被分类器覆盖），
        # 栏目名须按 source_url 映射挂回——端点 source_name 字段的供给线
        crawler = EmploymentAnnounceCrawler(config={"rate_limit": 0})
        raw = [
            {
                "title": "某高校2027届毕业生秋季双选会邀请函公告标题",
                "url": "https://career.hebut.edu.cn/news/content/id/999.html",
                "published_at": "2026-09-30",
                "detail_text": "正文内容" * 40,
                "source_name": "河北工业大学就业信息网重要通知",
            }
        ]
        parsed = crawler.parse(raw)
        assert len(parsed) >= 1
        first = parsed[0]
        assert first["source_url"] == raw[0]["url"]
        assert first.get("source_name") == "河北工业大学就业信息网重要通知"


# ----------------------------------------------------------------------
# 4. 公开端点 /api/employment/announces（PENDING 永不上前端）
# ----------------------------------------------------------------------
class TestAnnouncesEndpoint:
    def _seed(self, db_session: Session):
        db_session.add_all(
            [
                ExternalResearchItem(
                    crawler_name="employment_announce",
                    crawler_run_id="run-1",
                    item_type="employment_announce",
                    title="已审核公告A",
                    content="正文A",
                    source_url="https://career.csu.edu.cn/news/view/aid/1/tag/tzgg",
                    source_platform="official",
                    external_meta={
                        "source_name": "中南大学就业信息网通知公告",
                        "published_at": "2026-09-18",
                    },
                    credibility="official_verified",
                    review_status="APPROVED",
                ),
                ExternalResearchItem(
                    crawler_name="employment_announce",
                    crawler_run_id="run-1",
                    item_type="employment_announce",
                    title="待审公告B（不可见）",
                    content="正文B",
                    source_url="https://career.csu.edu.cn/news/view/aid/2/tag/tzgg",
                    source_platform="official",
                    review_status="PENDING",
                ),
                ExternalResearchItem(
                    crawler_name="employment_announce",
                    crawler_run_id="run-1",
                    item_type="employment_announce",
                    title="已拒公告C（不可见）",
                    content="正文C",
                    source_url="https://career.csu.edu.cn/news/view/aid/3/tag/tzgg",
                    source_platform="official",
                    review_status="REJECTED",
                ),
                # 考研线条目不得混入就业端点
                ExternalResearchItem(
                    crawler_name="official_announce",
                    crawler_run_id="run-1",
                    item_type="kaoyan_news",
                    title="考研公告D（不可见）",
                    content="正文D",
                    source_url="https://yjs.example.edu.cn/k2.htm",
                    source_platform="official",
                    review_status="APPROVED",
                ),
            ]
        )
        db_session.commit()

    def test_only_approved_employment_items_visible(self, client, db_session: Session):
        self._seed(db_session)
        resp = client.get("/api/employment/announces")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["title"] == "已审核公告A"
        assert item["published_at"] == "2026-09-18"
        assert item["source_name"] == "中南大学就业信息网通知公告"
        assert item["credibility"] == "official_verified"
        # 非敏感字段契约：不出 content/crawler_run_id/review_status
        assert set(item.keys()) == {
            "title",
            "source_url",
            "source_name",
            "published_at",
            "credibility",
        }

    def test_pagination(self, client, db_session: Session):
        self._seed(db_session)
        resp = client.get("/api/employment/announces?page=1&page_size=50")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
