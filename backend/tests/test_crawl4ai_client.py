"""Crawl4AIClient 测试：SSRF/robots 护栏、结果对齐、降级路径。

不启动真实浏览器（crawl4ai 的懒 import 在 _render_many_async 内，测试全部
mock 该层），保证测试快速、确定、且不依赖 crawl4ai 是否安装。
"""

import pytest

from app.crawlers import crawl4ai_client as cc
from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.crawl4ai_client import Crawl4AIClient, Crawl4aiError, Crawl4aiResult


class _ConcreteCrawler(BaseCrawler):
    name = "test-concrete"
    category = "test"

    def fetch(self) -> list[dict]:
        return []

    def parse(self, raw_items: list[dict]) -> list[dict]:
        return raw_items

    def store(self, items: list[dict], db) -> int:
        return 0


@pytest.fixture(autouse=True)
def reset_singleton(monkeypatch):
    """每个测试重置单例（CRAWL4AI_ENABLED 用例需要干净的实例状态）。"""
    monkeypatch.setattr(Crawl4AIClient, "_instance", None)


def _fake_render_ok(urls, page_timeout, wait_until):
    return [Crawl4aiResult(url=u, success=True, markdown="md", title="T") for u in urls]


class TestSsrfGuard:
    def test_rejects_internal_and_metadata_before_render(self, monkeypatch):
        """内网/云元数据地址在浏览器启动前就被拒，且不触发渲染。"""
        called = {"render": False}

        def _fail_if_render(*args, **kwargs):
            called["render"] = True
            raise AssertionError("SSRF 拦截后不应进入渲染")

        c = Crawl4AIClient()
        monkeypatch.setattr(c, "_render_many_async", _fail_if_render)
        results = c.fetch_many(
            ["http://127.0.0.1:8000/health", "http://169.254.169.254/latest/meta-data/"]
        )
        assert not called["render"]
        assert len(results) == 2
        assert all(not r.success for r in results)
        assert all("URL 校验失败" in r.error_message for r in results)

    def test_max_pages_truncates(self, monkeypatch):
        """超 CRAWL4AI_MAX_PAGES 时截断（只渲染前 N 个）。"""
        monkeypatch.setattr(cc, "CRAWL4AI_MAX_PAGES", 2)
        c = Crawl4AIClient()

        def _fake_render(urls, page_timeout, wait_until):
            return [Crawl4aiResult(url=u, success=True) for u in urls]

        monkeypatch.setattr(c, "_render_many_async", _fake_render)
        results = c.fetch_many(["https://a.com/1", "https://a.com/2", "https://a.com/3"])
        assert [r.url for r in results] == ["https://a.com/1", "https://a.com/2"]


class TestRobotsGuard:
    def test_robots_denied_skips_render(self, monkeypatch):
        """robots.txt 不允许 → 不进浏览器，返回 success=False。"""
        monkeypatch.setattr(cc, "validate_outbound_url", lambda url: (True, ""))
        monkeypatch.setattr(cc.RobotsChecker, "check_allowed", lambda self, url: False)

        c = Crawl4AIClient()

        def _fail_if_render(*args, **kwargs):
            raise AssertionError("robots 拒绝后不应进入渲染")

        monkeypatch.setattr(c, "_render_many_async", _fail_if_render)
        results = c.fetch_many(["https://a.com/x"])
        assert len(results) == 1
        assert not results[0].success
        assert "robots.txt" in results[0].error_message


class TestResultAlignment:
    def test_results_aligned_with_input_order(self, monkeypatch):
        """结果与输入顺序一一对应；被拒 URL 保持在原位置。"""

        def _fake_validate(url):
            if "blocked" in url:
                return False, "blocked-for-test"
            return True, ""

        monkeypatch.setattr(cc, "validate_outbound_url", _fake_validate)
        monkeypatch.setattr(cc.RobotsChecker, "check_allowed", lambda self, url: True)

        c = Crawl4AIClient()
        rendered_pool = []

        def _fake_render(urls, page_timeout, wait_until):
            rendered_pool.extend(urls)
            return [Crawl4aiResult(url=u, success=True, markdown="md") for u in urls]

        monkeypatch.setattr(c, "_render_many_async", _fake_render)
        results = c.fetch_many(["https://a.com/1", "https://blocked/x", "https://a.com/2"])
        assert [r.url for r in results] == [
            "https://a.com/1",
            "https://blocked/x",
            "https://a.com/2",
        ]
        assert results[0].success and results[2].success
        assert not results[1].success
        # 被拒 URL 不进渲染
        assert rendered_pool == ["https://a.com/1", "https://a.com/2"]

    def test_render_failure_degrades_all_pending(self, monkeypatch):
        """浏览器不可用（Crawl4aiError）→ pending 全部降级，不吞异常。"""
        monkeypatch.setattr(cc, "validate_outbound_url", lambda url: (True, ""))
        monkeypatch.setattr(cc.RobotsChecker, "check_allowed", lambda self, url: True)

        c = Crawl4AIClient()

        def _raise(*args, **kwargs):
            raise Crawl4aiError("browser unavailable")

        monkeypatch.setattr(c, "_render_many_async", _raise)
        results = c.fetch_many(["https://a.com/1", "https://a.com/2"])
        assert len(results) == 2
        assert all(not r.success for r in results)
        assert all("browser unavailable" in r.error_message for r in results)


class TestToResult:
    def test_normalizes_container(self):
        """CrawlResultContainer(results=[CrawlResult]) → Crawl4aiResult。"""

        class _FakeRes:
            success = True
            markdown = "**md**"
            extracted_content = "fallback"
            error_message = ""
            status_code = 200
            metadata = {"title": "T"}

        class _FakeContainer:
            results = [_FakeRes()]

        out = Crawl4AIClient._to_result("https://a.com/1", _FakeContainer())
        assert out.success
        assert out.markdown == "**md**"
        assert out.title == "T"
        assert out.status_code == 200

    def test_single_result_without_wrapper(self):
        """直接传 CrawlResult（无 Container）也能归一化。"""

        class _FakeRes:
            success = True
            markdown = ""
            extracted_content = "fallback-only"
            error_message = ""
            status_code = 200
            metadata = None

        out = Crawl4AIClient._to_result("https://a.com/2", _FakeRes())
        assert out.success
        assert out.markdown == "fallback-only"


class TestDisabledEnv:
    def test_disabled_raises_on_get_instance(self, monkeypatch):
        """CRAWL4AI_ENABLED=false → get_instance 抛 Crawl4aiError。"""
        monkeypatch.setattr(cc, "CRAWL4AI_ENABLED", False)
        with pytest.raises(Crawl4aiError):
            Crawl4AIClient.get_instance()

    def test_module_fetch_markdown_returns_none_when_disabled(self, monkeypatch):
        """模块级 fetch_markdown：客户端不可用 → None（调用方降级 HTTP）。"""
        monkeypatch.setattr(cc, "CRAWL4AI_ENABLED", False)
        assert cc.fetch_markdown("https://a.com/1") is None

    def test_instance_unchanged_after_failed_init(self, monkeypatch):
        """失败的 __init__ 不留下半初始化单例。"""
        monkeypatch.setattr(cc, "CRAWL4AI_ENABLED", False)
        with pytest.raises(Crawl4aiError):
            Crawl4AIClient.get_instance()
        assert Crawl4AIClient._instance is None

    def test_get_instance_blocks_after_singleton_built(self, monkeypatch):
        """单例已创建后运行时关闭开关，get_instance 仍拒绝（每次访问均检查）。"""
        built = Crawl4AIClient.get_instance()  # ENABLED=true 先建单例
        assert built is Crawl4AIClient._instance
        monkeypatch.setattr(cc, "CRAWL4AI_ENABLED", False)
        with pytest.raises(Crawl4aiError):
            Crawl4AIClient.get_instance()


class TestBaseCrawlerMixin:
    def test_mixin_returns_none_when_client_unavailable(self, monkeypatch):
        """BaseCrawler.fetch_markdown：客户端不可用 → None。"""
        monkeypatch.setattr(cc, "CRAWL4AI_ENABLED", False)
        c = _ConcreteCrawler()
        assert c.fetch_markdown("https://a.com/1") is None

    def test_mixin_delegates_to_client(self, monkeypatch):
        """BaseCrawler.fetch_markdown 委托客户端，返回 Crawl4aiResult。"""
        fake_client = Crawl4aiResult(url="https://a.com/1", markdown="md", success=True)
        monkeypatch.setattr(
            Crawl4AIClient,
            "get_instance",
            lambda: type("F", (), {"fetch_markdown": lambda self, u, **k: fake_client})(),
        )
        c = _ConcreteCrawler()
        out = c.fetch_markdown("https://a.com/1")
        assert out.success
        assert out.markdown == "md"

    def test_mixin_catches_crawl4ai_error(self, monkeypatch):
        """get_instance 抛 Crawl4aiError → mixin 返回 None 不冒泡。"""
        monkeypatch.setattr(cc, "CRAWL4AI_ENABLED", False)
        c = _ConcreteCrawler()
        assert c.fetch_markdown("https://a.com/1") is None
