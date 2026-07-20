"""考研爬虫单元测试。

使用 mock 替代真实 HTTP 请求，覆盖 RealDataCrawler 的抓取、解析、存储逻辑。
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

import httpx

from app.crawlers.grad.real_data_crawler import (
    RealDataCrawler,
    _get_random_headers,
    _fetch_with_retry,
    _parse_yanzhao_search,
    _parse_cdgdc_rank,
    _SCHOOL_CACHE,
    _PROGRAM_CACHE,
)


# ======================================================================
# 辅助函数测试
# ======================================================================


class TestHelperFunctions:
    def test_get_random_headers_returns_valid_headers(self):
        """验证随机请求头包含必要的 Header。"""
        headers = _get_random_headers()
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Mozilla" in headers["User-Agent"] or "Chrome" in headers["User-Agent"]

    def test_parse_yanzhao_search_with_valid_html(self):
        """验证研招网搜索结果解析。"""
        html = """
        <html>
        <body>
        <table class="vT-srch-result-list-bid">
            <tr>
                <td>清华大学</td>
                <td>计算机科学与技术</td>
                <td>学硕</td>
                <td>2026</td>
            </tr>
        </table>
        </body>
        </html>
        """
        results = _parse_yanzhao_search(html)
        assert len(results) == 1
        assert results[0]["university"] == "清华大学"
        assert results[0]["major"] == "计算机科学与技术"

    def test_parse_yanzhao_search_with_empty_html(self):
        """验证空 HTML 返回空列表。"""
        results = _parse_yanzhao_search("")
        assert results == []

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
        results = _parse_cdgdc_rank("")
        assert results == []


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

    def test_crawler_with_config(self):
        """验证爬虫配置参数。"""
        config = {"use_cache": True, "rate_limit": 2.0}
        crawler = RealDataCrawler(config=config)
        assert crawler._use_cache is True

    def test_fetch_returns_data_when_real_sources_fail(self):
        """验证真实数据源失败时回退到缓存。"""
        crawler = RealDataCrawler(config={"use_cache": False})

        # Mock all real data fetches to fail
        with patch.object(crawler, "_fetch_yanzhao_data", return_value=[]), \
             patch.object(crawler, "_fetch_school_data", return_value=[]), \
             patch.object(crawler, "_fetch_discipline_data", return_value=[]):
            raw = crawler.fetch()

        # Should fall back to cache
        assert len(raw) > 0
        assert any(item["source"] == "cache" for item in raw)

    def test_fetch_with_real_yanzhao_data(self):
        """验证研招网数据抓取。"""
        crawler = RealDataCrawler()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <table class="vT-srch-result-list-bid">
            <tr>
                <td>北京大学</td>
                <td>软件工程</td>
                <td>专硕</td>
                <td>2026</td>
            </tr>
        </table>
        </html>
        """

        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_client.return_value = mock_instance

            results = crawler._fetch_yanzhao_data()

        assert len(results) == 1
        assert results[0]["source"] == "研招网"
        assert results[0]["data"]["university"] == "北京大学"

    def test_fetch_with_school_data(self):
        """验证高校官网数据抓取。"""
        crawler = RealDataCrawler()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>招生信息</html>"

        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_client.return_value = mock_instance

            results = crawler._fetch_school_data()

        # 应该抓取了前5所学校的数据
        assert len(results) > 0
        assert all(item["source"] == "高校官网" for item in results)

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
        result = crawler._parse_school_data(data, "cache")

        assert result["school_name"] == "清华大学"
        assert result["school_tier"] == "985"
        assert "计算机" in result["disciplines"]

    def test_parse_program_data(self):
        """验证专业目录数据解析。"""
        crawler = RealDataCrawler()
        data = {
            "university": "北京大学",
            "department": "信息科学技术学院",
            "major": "计算机科学与技术",
            "degree_type": "学硕",
            "quota": 22,
            "subjects": "数学一、英语一",
        }
        result = crawler._parse_program_data(data, "研招网")

        assert result["school_name"] == "北京大学"
        assert result["major_name"] == "计算机科学与技术"
        assert result["enrollment_quota"] == 22

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

    def test_parse_returns_multiple_types(self):
        """验证解析多种数据类型。"""
        crawler = RealDataCrawler()
        raw_items = [
            {"source": "cache", "type": "school", "data": {"name": "清华大学", "tier": "985"}},
            {"source": "研招网", "type": "program", "data": {"university": "北京大学", "major": "软件工程"}},
            {"source": "学位网", "type": "discipline", "data": {"discipline": "计算机", "university": "清华", "rating": "A+"}},
        ]

        parsed = crawler.parse(raw_items)
        assert len(parsed) == 3
        assert any(item.get("school_name") == "清华大学" for item in parsed)
        assert any(item.get("major_name") == "软件工程" for item in parsed)

    def test_fetch_with_retry_success(self):
        """验证重试机制在成功时停止。"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_client.return_value = mock_instance

            result = _fetch_with_retry(mock_instance, "https://example.com")

        assert result is not None
        assert result.status_code == 200

    def test_fetch_with_retry_handles_timeout(self):
        """验证超时异常处理。"""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = httpx.TimeoutException("timeout")
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_client.return_value = mock_instance

            result = _fetch_with_retry(mock_instance, "https://example.com", max_retries=2, base_delay=0.1)

        assert result is None

    def test_fetch_with_retry_handles_rate_limit(self):
        """验证 429 限流处理。"""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429

        success_response = MagicMock()
        success_response.status_code = 200

        with patch("httpx.Client") as mock_client, \
             patch("time.sleep"):
            mock_instance = MagicMock()
            mock_instance.get.side_effect = [rate_limit_response, success_response]
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_client.return_value = mock_instance

            result = _fetch_with_retry(mock_instance, "https://example.com", base_delay=0.01)

        assert result is not None
        assert result.status_code == 200

    def test_get_cached_data_returns_valid_structure(self):
        """验证缓存数据结构正确。"""
        crawler = RealDataCrawler()
        cached = crawler._get_cached_data()

        assert len(cached) > 0
        assert any(item["type"] == "school" for item in cached)
        assert any(item["type"] == "program" for item in cached)

    def test_store_saves_to_database(self, db_session):
        """验证数据存储到数据库。"""
        crawler = RealDataCrawler()

        items = [
            {
                "school_name": "测试大学",
                "major_name": "计算机科学",
                "school_tier": "211",
                "data_sources": ["test"],
                "tags": ["test"],
            }
        ]

        with patch.object(crawler, "batch_upsert", return_value=1) as mock_upsert:
            count = crawler.store(items, db_session)

        assert count == 1
        mock_upsert.assert_called_once()

    def test_store_skips_items_without_school_name(self, db_session):
        """验证跳过没有学校名称的条目。"""
        crawler = RealDataCrawler()

        items = [
            {"major_name": "计算机", "data_sources": []},
            {"school_name": "", "major_name": "软件工程", "data_sources": []},
            {"school_name": "有效大学", "major_name": "有效专业", "data_sources": []},
        ]

        with patch.object(crawler, "batch_upsert", return_value=1) as mock_upsert:
            count = crawler.store(items, db_session)

        # 只有第三条会被存储
        assert count == 1

    def test_full_run_workflow(self, db_session):
        """验证完整的爬取-解析-存储流程。"""
        crawler = RealDataCrawler(config={"use_cache": False})

        # Mock all fetch methods to return cache data
        cache_data = [
            {"source": "cache", "type": "school", "data": {"name": "测试大学", "tier": "985"}},
            {"source": "cache", "type": "program", "data": {"university": "测试大学", "major": "计算机", "degree_type": "学硕", "quota": 10}},
        ]

        with patch.object(crawler, "_fetch_yanzhao_data", return_value=[]), \
             patch.object(crawler, "_fetch_school_data", return_value=[]), \
             patch.object(crawler, "_fetch_discipline_data", return_value=[]), \
             patch.object(crawler, "_get_cached_data", return_value=cache_data), \
             patch.object(crawler, "batch_upsert", return_value=1):
            result = crawler.run(db=db_session)

        assert result["status"] == "success"
        assert result["fetched"] == 2
        assert result["stored"] == 2


# ======================================================================
# 缓存数据测试
# ======================================================================


class TestCacheData:
    def test_school_cache_covers_top_universities(self):
        """验证缓存包含主要 985 院校。"""
        assert "清华大学" in _SCHOOL_CACHE
        assert "北京大学" in _SCHOOL_CACHE
        assert "复旦大学" in _SCHOOL_CACHE
        assert "上海交通大学" in _SCHOOL_CACHE
        assert "浙江大学" in _SCHOOL_CACHE

    def test_program_cache_has_required_fields(self):
        """验证专业目录缓存包含必要字段。"""
        for program in _PROGRAM_CACHE:
            assert "university" in program
            assert "major" in program
            assert "degree_type" in program
            assert "quota" in program

    def test_school_cache_has_contact_info(self):
        """验证学校缓存包含联系方式。"""
        for school_name, info in _SCHOOL_CACHE.items():
            assert "phone" in info
            assert "website" in info
