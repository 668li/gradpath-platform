# backend/tests/test_base_crawler.py
"""爬虫基类外发安全护栏测试（Phase I，Mimosa 强制约束）。

覆盖：
- _validate_outbound_url：仅 http/https；file/ftp 拒；localhost/环回/私有/
  链路本地/多播/保留/未指定 全拒；IPv4 映射 IPv6 解映射防绕过；
  域名经 socket 解析逐一校验（mock，解析失败 fail-safe 拒绝）
- _request：校验失败 / robots 不允许 → 直接抛异常，不发起请求
- _check_robots_allowed：允许/禁止/取不到 fail-safe；每 host 缓存一次
- _fetch_robots_parser：4xx 放行、5xx/网络失败 fail-safe 拒绝
"""
import socket

import pytest
import requests

from app.crawlers.base_crawler import BaseCrawler


class _ConcreteCrawler(BaseCrawler):
    """最小可实例化子类（BaseCrawler 有抽象方法）。"""

    name = "test_base"
    category = "research"
    description = "测试用"

    def fetch(self) -> list[dict]:
        return []

    def parse(self, raw_items: list[dict]) -> list[dict]:
        return []

    def store(self, items: list[dict], db=None) -> int:
        return 0


def _make_crawler(**config) -> _ConcreteCrawler:
    return _ConcreteCrawler(config=config)


class TestValidateOutboundUrl:
    """URL host 校验：scheme + 受限地址全拒 + DNS fail-safe。"""

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",                    # 非 http(s)
            "ftp://example.com/file",                # 非 http(s)
            "javascript:alert(1)",                   # 非 http(s)
            "http://localhost/",                     # 保留主机名
            "http://localhost.localdomain/",         # 保留主机名
            "http://127.0.0.1/",                     # 环回
            "http://127.0.0.1:8000/admin",           # 环回带端口
            "http://[::1]/",                         # IPv6 环回
            "http://10.1.2.3/",                      # 私有 A
            "http://192.168.1.1/",                   # 私有 C
            "http://172.16.0.1/",                    # 私有 B
            "http://169.254.169.254/latest/meta-data/",  # 链路本地（元数据）
            "http://0.0.0.0/",                       # 未指定
            "http://224.0.0.1/",                     # 多播
            "http://240.0.0.1/",                     # 保留
            "http://[::ffff:127.0.0.1]/",            # IPv4 映射环回
            "http://[::ffff:192.168.1.1]/",          # IPv4 映射私有
            "http://",                               # 缺主机名
        ],
    )
    def test_rejects_all_restricted(self, url):
        ok, reason = _make_crawler()._validate_outbound_url(url)
        assert ok is False, f"应拒绝: {url}"
        assert reason, "拒绝原因不能为空"

    def test_accepts_public_literal_ip(self):
        ok, reason = _make_crawler()._validate_outbound_url("http://93.184.216.34/")
        assert ok is True
        assert reason == ""

    def test_accepts_public_domain_via_dns(self, monkeypatch):
        """域名解析到公网 IP → 放行（mock socket 不发真实 DNS）。"""
        monkeypatch.setattr(
            "app.crawlers.base_crawler.socket.getaddrinfo",
            lambda host, _: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ],
        )
        ok, reason = _make_crawler()._validate_outbound_url("https://example.com/a")
        assert ok is True
        assert reason == ""

    def test_dns_resolving_to_private_rejected(self, monkeypatch):
        """域名解析到私有地址 → 拒绝（DNS 重绑定防护）。"""
        monkeypatch.setattr(
            "app.crawlers.base_crawler.socket.getaddrinfo",
            lambda host, _: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))
            ],
        )
        ok, reason = _make_crawler()._validate_outbound_url("https://evil.example.com/")
        assert ok is False
        assert "受限地址" in reason

    def test_dns_resolving_to_mixed_ips_rejected(self, monkeypatch):
        """多解析结果中任一受限 → 整体拒绝。"""
        monkeypatch.setattr(
            "app.crawlers.base_crawler.socket.getaddrinfo",
            lambda host, _: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0)),
            ],
        )
        ok, _ = _make_crawler()._validate_outbound_url("https://mixed.example.com/")
        assert ok is False

    def test_dns_failure_fail_safe_rejected(self, monkeypatch):
        """解析失败（gaierror）→ fail-safe 拒绝，不发起请求。"""
        monkeypatch.setattr(
            "app.crawlers.base_crawler.socket.getaddrinfo",
            lambda host, _: (_ for _ in ()).throw(socket.gaierror("nodename not known")),
        )
        ok, reason = _make_crawler()._validate_outbound_url("https://nope.invalid/")
        assert ok is False
        assert "解析失败" in reason

    def test_ipv4_mapped_ipv6_unmapped_before_check(self):
        """IPv4 映射 IPv6 解映射后再判定（防 ::ffff: 绕过）。"""
        restricted = BaseCrawler._is_restricted_ip(
            __import__("ipaddress").ip_address("::ffff:127.0.0.1")
        )
        assert restricted is True
        public = BaseCrawler._is_restricted_ip(
            __import__("ipaddress").ip_address("::ffff:93.184.216.34")
        )
        assert public is False


class TestRequestGuards:
    """_request 入口护栏：校验失败/robots 不允许 → 抛异常不真发请求。"""

    def test_validation_failure_raises_without_request(self, monkeypatch):
        c = _make_crawler()
        monkeypatch.setattr(c, "_validate_outbound_url", lambda url: (False, "仅允许 http/https"))
        monkeypatch.setattr(c, "_check_robots_allowed", lambda url: True)
        called = []

        def fake_request(*a, **kw):
            called.append(a)
            return None

        monkeypatch.setattr(c.session, "request", fake_request)
        with pytest.raises(requests.RequestException, match="外发 URL 校验失败"):
            c._request("file:///etc/passwd")
        assert called == []

    def test_robots_denied_raises_without_request(self, monkeypatch):
        c = _make_crawler()
        monkeypatch.setattr(c, "_validate_outbound_url", lambda url: (True, ""))
        monkeypatch.setattr(c, "_check_robots_allowed", lambda url: False)
        called = []
        monkeypatch.setattr(
            c.session, "request",
            lambda *a, **kw: called.append(a) or None,
        )
        with pytest.raises(requests.RequestException, match="robots.txt 不允许抓取"):
            c._request("https://example.com/page")
        assert called == []

    def test_allowed_path_hits_network(self, monkeypatch):
        """校验 + robots 均通过 → 真正发请求（mock session.request）。"""
        c = _make_crawler()
        monkeypatch.setattr(c, "_validate_outbound_url", lambda url: (True, ""))
        monkeypatch.setattr(c, "_check_robots_allowed", lambda url: True)
        called = []

        class _Resp:
            def raise_for_status(self):
                pass

        monkeypatch.setattr(
            c.session, "request",
            lambda *a, **kw: called.append((a[0], a[1])) or _Resp(),
        )
        monkeypatch.setattr("app.crawlers.base_crawler.time.sleep", lambda s: None)
        c._request("https://example.com/page")
        assert called == [("GET", "https://example.com/page")]


class TestRobotsCompliance:
    """robots.txt 判定 + 缓存 + 拉取 fail-safe。"""

    def test_allowed_when_parser_allows(self, monkeypatch):
        c = _make_crawler()

        class _Parser:
            def can_fetch(self, ua, url):
                return True

        monkeypatch.setattr(c, "_fetch_robots_parser", lambda key: _Parser())
        assert c._check_robots_allowed("https://example.com/p") is True

    def test_denied_when_parser_disallows(self, monkeypatch):
        c = _make_crawler()

        class _Parser:
            def can_fetch(self, ua, url):
                return False

        monkeypatch.setattr(c, "_fetch_robots_parser", lambda key: _Parser())
        assert c._check_robots_allowed("https://example.com/p") is False

    def test_fetch_failure_fail_safe_denied(self, monkeypatch):
        """robots.txt 获取失败 → fail-safe 拒绝（无法确认即不爬）。"""
        c = _make_crawler()
        monkeypatch.setattr(c, "_fetch_robots_parser", lambda key: None)
        assert c._check_robots_allowed("https://example.com/p") is False

    def test_non_http_never_checked(self, monkeypatch):
        c = _make_crawler()
        monkeypatch.setattr(
            c, "_fetch_robots_parser",
            lambda key: pytest.fail("非 http(s) URL 不应拉取 robots"),
        )
        assert c._check_robots_allowed("file:///tmp/x") is False

    def test_parser_cached_per_host(self, monkeypatch):
        """同主机只拉取一次 robots（缓存），跨主机各自拉取。"""
        c = _make_crawler()
        calls: list[str] = []

        def fake_fetch(key: str):
            calls.append(key)

            class _P:
                def can_fetch(self, ua, url):
                    return True

            return _P()

        monkeypatch.setattr(c, "_fetch_robots_parser", fake_fetch)
        # 直接走真实缓存逻辑：_fetch_robots_parser 已打桩
        c._check_robots_allowed("https://example.com/a")
        c._check_robots_allowed("https://example.com/b")  # 同主机 → 不重复拉取
        c._check_robots_allowed("https://other.com/x")    # 新主机 → 拉取
        assert calls == ["https://example.com", "https://other.com"]

    def test_fetch_robots_404_passes_through(self, monkeypatch):
        """404 → 视为无 robots.txt → 放行（默认允许）。"""
        import urllib.error

        c = _make_crawler()

        def fake_urlopen(req, timeout=10):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

        monkeypatch.setattr("app.crawlers.base_crawler.urllib.request.urlopen", fake_urlopen)
        rp = c._fetch_robots_parser("https://example.com")
        assert rp is not None
        assert rp.can_fetch(c.USER_AGENT, "https://example.com/x") is True

    def test_fetch_robots_5xx_fail_safe(self, monkeypatch):
        """500 → 无法确认 → fail-safe 拒绝（返回 None）。"""
        import urllib.error

        c = _make_crawler()

        def fake_urlopen(req, timeout=10):
            raise urllib.error.HTTPError(req.full_url, 500, "Internal Server Error", {}, None)

        monkeypatch.setattr("app.crawlers.base_crawler.urllib.request.urlopen", fake_urlopen)
        assert c._fetch_robots_parser("https://example.com") is None

    def test_fetch_robots_network_error_fail_safe(self, monkeypatch):
        """网络失败（超时/连接错误）→ fail-safe 拒绝。"""
        c = _make_crawler()

        def fake_urlopen(req, timeout=10):
            raise OSError("connection timed out")

        monkeypatch.setattr("app.crawlers.base_crawler.urllib.request.urlopen", fake_urlopen)
        assert c._fetch_robots_parser("https://example.com") is None
