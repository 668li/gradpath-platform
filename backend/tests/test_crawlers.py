"""考研爬虫单元测试（RealDataCrawler，spec 002 收敛版）。

2026-09-12 地基收敛后覆盖：
- 红线根除断言：研招网抓取分支与预置缓存补位已物理删除（宁缺毋假）；
- 解析纯函数：学科评级；
- store 走审核队列 + 地基⑤证据透传（旧 KNOWN DEFECT"伪研招网 URL 被拒"
  已随 _review_url 改挂校主页/学位网翻案为正向断言）。
"""

from unittest.mock import MagicMock, patch

import pytest

from app.crawlers.grad.real_data_crawler import (
    _SCHOOL_CACHE,
    RealDataCrawler,
    _get_random_headers,
    _parse_cdgdc_rank,
    _to_queue_item,
)

_EVIDENCE = {"http_status": 200, "fetched_at": "2026-09-12T12:00:00+00:00", "sha256": "e" * 64}


# ======================================================================
# 辅助函数测试
# ======================================================================


class TestHelperFunctions:
    def test_get_random_headers_returns_valid_headers(self):
        """验证随机请求头包含必要的 Header。"""
        headers = _get_random_headers()
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Mozilla" in headers["User-Agent"] or "Chrome" in headers["User-Agent"]

    def test_parse_cdgdc_rank_with_valid_html(self):
        """验证学位网学科评级解析。"""
        html = """
        <html>
        <body>
        <table>
            <tr><td>计算机科学与技术</td><td>清华大学</td><td>A+</td></tr>
            <tr><td>计算机科学与技术</td><td>北京大学</td><td>A+</td></tr>
        </table>
        </body>
        </html>
        """
        results = _parse_cdgdc_rank(html)
        assert len(results) == 2
        assert results[0]["discipline"] == "计算机科学与技术"
        assert results[0]["rating"] == "A+"

    def test_parse_cdgdc_rank_with_empty_html(self):
        """验证空 HTML 返回空列表。"""
        assert _parse_cdgdc_rank("") == []


# ======================================================================
# RealDataCrawler 测试
# ======================================================================


class TestRealDataCrawler:
    def test_crawler_initialization(self):
        """验证爬虫初始化。"""
        crawler = RealDataCrawler()
        assert crawler.name == "real_data"
        assert crawler.category == "grad"
        assert "真实数据" in crawler.description

    def test_redline_branch_eradicated(self):
        """红线根除（spec 002）：研招网分支与预置缓存补位必须物理消失。"""
        crawler = RealDataCrawler()
        assert not hasattr(crawler, "_fetch_yanzhao_data"), "研招网抓取分支必须已删除（R2）"
        assert not hasattr(crawler, "_get_cached_data"), "预置缓存补位必须已删除（R6 宁缺毋假）"
        import app.crawlers.grad.real_data_crawler as mod

        src = mod.__doc__ or ""
        assert "yz.chsi.com.cn" not in getattr(mod, "_REAL_DATA_SOURCES", {})
        assert "红线" in src, "模块文档必须如实记载红线根除"

    def test_fetch_never_falls_back_to_preset(self):
        """宁缺毋假：真实抓取全部失败 → 空手而归，绝不回退预置数据。"""
        crawler = RealDataCrawler(config={"rate_limit": 0})
        with (
            patch.object(crawler, "_fetch_school_data", return_value=[]),
            patch.object(crawler, "_fetch_discipline_data", return_value=[]),
        ):
            raw = crawler.fetch()
        assert raw == [], "抓取失败=空手而归（spec R6）"

    def test_fetch_school_data_through_unified_transport(self):
        """高校官网抓取走统一传输层（self._request，带证据）。"""
        crawler = RealDataCrawler(config={"rate_limit": 0})

        resp = MagicMock()
        resp.status_code = 200
        resp.text = "<html>招生信息</html>"
        with patch.object(crawler, "_request", return_value=resp) as mock_req:
            results = crawler._fetch_school_data()

        assert len(results) == 5, "应抓取前 5 所目标校"
        assert all(item["source"] == "高校官网" for item in results)
        assert mock_req.call_count == 5

    def test_to_queue_item_propagates_evidence(self):
        """地基⑤：队列映射必须透传抓取证据（fetched 态入库闸的前提）。"""
        item = {
            "school_name": "测试大学",
            "school_tier": "211",
            "data_sources": ["高校官网"],
            "tags": ["学校信息"],
            "website": "https://yz.test-university.edu.cn/",
            "fetch_evidence": dict(_EVIDENCE),
        }
        queue_item = _to_queue_item(item)
        assert queue_item["fetch_evidence"] == _EVIDENCE
        assert queue_item["source_url"].startswith("https://yz.test-university.edu.cn/")

    def test_review_url_never_chsi(self):
        """来源回退 URL 只允许校主页/学位网，绝不构造研招网红线域（F2 语义）。"""
        from app.crawlers.grad.real_data_crawler import _review_url

        url = _review_url(
            {"data_sources": ["学位网"], "school_name": "测试大学", "discipline": "计算机"}
        )
        assert "chsi" not in url
        assert url.startswith("https://www.cdgdc.edu.cn/")

    def test_parse_school_data(self):
        """验证学校数据解析。"""
        crawler = RealDataCrawler()
        data = {
            "name": "清华大学",
            "tier": "985",
            "location": "北京",
            "website": "https://yz.tsinghua.edu.cn/",
            "disciplines": ["计算机", "电子信息"],
            "strengths": ["工科"],
        }
        result = crawler._parse_school_data(data, "高校官网")

        assert result["school_name"] == "清华大学"
        assert result["school_tier"] == "985"
        assert "计算机" in result["disciplines"]

    def test_parse_discipline_data(self):
        """验证学科评级数据解析。"""
        crawler = RealDataCrawler()
        data = {
            "discipline": "计算机科学与技术",
            "university": "清华大学",
            "rating": "A+",
        }
        result = crawler._parse_discipline_data(data, "学位网")

        assert result["discipline"] == "计算机科学与技术"
        assert result["school_name"] == "清华大学"
        assert result["rating"] == "A+"

    def test_parse_ignores_unknown_types(self):
        """未知类型（含已根除的 program/cache）不得产出条目。"""
        crawler = RealDataCrawler()
        raw_items = [
            {"source": "cache", "type": "school", "data": {"name": "清华大学", "tier": "985"}},
            {
                "source": "cache",
                "type": "program",
                "data": {"university": "北京大学", "major": "软件工程"},
            },
            {
                "source": "学位网",
                "type": "discipline",
                "data": {"discipline": "计算机", "university": "清华", "rating": "A+"},
            },
        ]
        parsed = crawler.parse(raw_items)
        assert len(parsed) == 2, "program 类型已随预置数据根除，不再产出"
        assert all(item.get("major_name") is None or item.get("discipline") for item in parsed)

    # ===== store（审核队列 + 三态证据闸） =====

    @pytest.fixture
    def _db(self, db_session):
        return db_session

    def test_store_saves_evidenced_items_to_queue(self, db_session):
        """证据齐全 → PENDING 审核队列（旧 KNOWN DEFECT 翻案：URL 已改挂真实域）。"""
        from app.models.grad_intel import GradSchoolIntel
        from app.models.ingestion import ExternalResearchItem, ReviewQueueItem

        crawler = RealDataCrawler()
        items = [
            {
                "school_name": "测试大学",
                "major_name": "计算机科学",
                "school_tier": "211",
                "data_sources": ["高校官网"],
                "tags": ["学校信息"],
                "website": "https://yz.test-university.edu.cn/",
                "fetch_evidence": dict(_EVIDENCE),
            }
        ]
        count = crawler.store(items, db_session)

        assert count == 1, "真实 URL + 齐全证据必须入队（KNOWN DEFECT 已翻案）"
        ext = db_session.query(ExternalResearchItem).one()
        assert ext.review_status == "PENDING"
        assert ext.data_origin == "fetched"
        assert ext.fetch_evidence["sha256"] == _EVIDENCE["sha256"]
        assert db_session.query(ReviewQueueItem).count() == 1
        assert db_session.query(GradSchoolIntel).count() == 0, "绝不旁路直落业务表"

    def test_store_rejects_items_without_evidence(self, db_session):
        """地基⑤：store 直调（未经 run() 盖章）的无证据条目被闸拒收。"""
        from app.models.ingestion import ExternalResearchItem

        crawler = RealDataCrawler()
        items = [
            {"school_name": "无证据大学", "data_sources": ["高校官网"]},
            {"major_name": "计算机", "data_sources": []},  # 无校名，前置过滤
            {"school_name": "", "major_name": "软件工程", "data_sources": []},  # 无校名
        ]
        count = crawler.store(items, db_session)
        assert count == 0
        assert db_session.query(ExternalResearchItem).count() == 0

    def test_full_run_workflow(self, db_session):
        """完整 run：真实 _request 链（sender 缝打桩）→ 证据自然流动 → PENDING 队列。

        打桩必须打在 sender 缝（_send_via_session）而非 fetch 方法上——否则
        run() 的统一证据盖章没有数据源，三态闸会如实拒收（那正是闸在工作）。
        """
        from app.models.grad_intel import GradSchoolIntel
        from app.models.ingestion import ExternalResearchItem

        crawler = RealDataCrawler(config={"rate_limit": 0})

        resp = MagicMock()
        resp.status_code = 200
        resp.text = "<html>招生信息</html>"
        resp.content = b"<html>ok</html>"
        resp.headers = {}

        with (
            patch.object(crawler, "_validate_outbound_url", return_value=(True, "")),
            patch.object(crawler, "_check_robots_allowed", return_value=True),
            patch.object(crawler, "_send_via_session", return_value=resp),
        ):
            result = crawler.run(db=db_session)

        assert result["status"] == "success"
        assert result["fetched"] == 5, "5 所目标校全部探测成功"
        assert result["stored"] == 5, "真实 _request 链产生证据 → 全部入队"
        # 6 次外发 = 5 所高校官网 + 1 次学位网（学位网解析该 mock 页得 0 条，不入库）
        assert len(crawler.fetch_evidence_log) == 6, "每次外发都必须留证据"
        pending = (
            db_session.query(ExternalResearchItem)
            .filter(ExternalResearchItem.review_status == "PENDING")
            .count()
        )
        assert pending == 5
        assert db_session.query(GradSchoolIntel).count() == 0


# ======================================================================
# 抓取目标清单（配置语义，非数据）
# ======================================================================


class TestSchoolTargets:
    def test_targets_cover_top_universities(self):
        """抓取目标清单覆盖主要 985 院校。"""
        assert "清华大学" in _SCHOOL_CACHE
        assert "北京大学" in _SCHOOL_CACHE
        assert "复旦大学" in _SCHOOL_CACHE
        assert "上海交通大学" in _SCHOOL_CACHE
        assert "浙江大学" in _SCHOOL_CACHE

    def test_targets_have_contact_info(self):
        """目标清单包含联系方式与官网（用于驱动真实抓取）。"""
        for school_name, info in _SCHOOL_CACHE.items():
            assert "phone" in info
            assert info["website"].startswith("http")
