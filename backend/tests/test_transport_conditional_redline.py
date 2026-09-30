"""研招网红线分层处置（2026-09-30 用户拍板"内部辅助"后新增）。

原语义（2026-09-12 起）：红线域任何路径一律拒绝外发。
现语义：路径分层——
  · 非白名单路径（网报/调剂/登录/专业目录查询）→ 硬拒，消息不变；
  · 白名单公开静态路径（``REDLINE_ALLOWED_PATHS``）→ 条件放行，但
    per-domain 限速加严至 ``REDLINE_MIN_INTERVAL_S``、遇 WAF 状态码即域级熔断。

不变量（防未来有人"顺手"把某道闸也放开）：
  · ``is_redline_fetch_url`` 与入库咽喉 ``research_ingestion.is_redline_url``
    语义保持一致——外发放行 ≠ 入库放行；
  · ``REDLINE_FETCH_HOSTS`` 不因外发放行而缩减。
"""

import pytest

from app.crawlers import transport
from app.crawlers.transport import (
    HttpFetchError,
    REDLINE_ALLOWED_PATHS,
    REDLINE_FETCH_HOSTS,
    REDLINE_MIN_INTERVAL_S,
    _QUARANTINE_STATUSES,
    _QUARANTINE_TTL_S,
    classify_redline_url,
    fetch,
    is_redline_fetch_url,
)


@pytest.fixture(autouse=True)
def _clean_process_state():
    """隔离进程级限速桶与熔断名单，避免用例间污染。"""
    transport._reset_quarantine_for_tests()
    yield
    transport._reset_quarantine_for_tests()


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "ok", content: bytes | None = None):
        self.status_code = status_code
        self.text = text
        self.content = content if content is not None else text.encode()
        self.headers = {"content-type": "text/html"}


def _sender_for(status: int, calls: list | None = None):
    def _send(method, url, headers, timeout):
        if calls is not None:
            calls.append(url)
        return _FakeResponse(status)

    return _send


# ===== 1. 分类判定 =====


def test_non_redline_host_is_not_classified():
    assert classify_redline_url("https://yz.suda.edu.cn/8386/list.htm") is None
    assert classify_redline_url("https://kaoyan.eol.cn/") is None


def test_redline_allowed_path_is_conditional():
    assert classify_redline_url("https://yz.chsi.com.cn/kyzx/fsfsx34/") == "conditional"
    assert classify_redline_url("https://yz.chsi.com.cn/kyzx/other-topic.html") == "conditional"


@pytest.mark.parametrize(
    "url",
    [
        "https://yz.chsi.com.cn/zsml/queryAction.do",  # 专业目录查询（需登录态遍历）
        "https://yz.chsi.com.cn/login",  # 学信网账号体系
        "https://yz.chsi.com.cn/reg",
        "https://yz.chsi.com.cn/yjs/wsb/index.jsp",  # 网报系统
        "https://yz.chsi.com.cn/tjhl/adj",  # 调剂系统
        "https://yz.chsi.com.cn/",  # 根路径不在白名单
    ],
)
def test_redline_non_allowed_paths_are_blocked(url):
    assert classify_redline_url(url) == "blocked"


def test_subdomain_of_redline_inherits_classification():
    assert classify_redline_url("https://sub.yz.chsi.com.cn/kyzx/x") == "conditional"
    assert classify_redline_url("https://sub.yz.chsi.com.cn/zsml/x") == "blocked"


def test_sibling_subdomain_still_exempt():
    """09-06 既定豁免：gaokao.chsi.com.cn 不在红线域内，不得被牵连。"""
    assert not is_redline_fetch_url("https://gaokao.chsi.com.cn/")
    assert classify_redline_url("https://gaokao.chsi.com.cn/kyzx/") is None


# ===== 2. 闸门行为：条件放行 / 硬拒 =====


def test_conditional_path_actually_fetches(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(transport, "_host_throttle", lambda host, interval: None)
    monkeypatch.setattr(transport, "_host_throttle_redline", lambda host, interval: None)
    result = fetch(
        "https://yz.chsi.com.cn/kyzx/fsfsx34/",
        sender=_sender_for(200, calls),
        crawler_name="unit",
    )
    assert result.status_code == 200
    assert calls == ["https://yz.chsi.com.cn/kyzx/fsfsx34/"]


def test_blocked_path_raises_before_network(monkeypatch):
    calls: list[str] = []
    with pytest.raises(HttpFetchError, match="红线域名禁止外发"):
        fetch("https://yz.chsi.com.cn/zsml/queryAction.do", sender=_sender_for(200, calls))
    assert calls == [], "硬拒路径不得发出任何网络请求"


# ===== 3. 限速差异化 =====


def test_conditional_host_rate_limit_is_floored(monkeypatch):
    """红线域走专属节流器；下限只抬不降。"""
    seen: list[tuple[str, float]] = []
    monkeypatch.setattr(transport, "_host_throttle_redline", lambda host, interval: seen.append((host, interval)))
    monkeypatch.setattr(transport, "_host_throttle", lambda host, interval: pytest.fail("红线域不得走普通节流器"))
    fetch("https://yz.chsi.com.cn/kyzx/x", rate_limit=0.1, sender=_sender_for(200))
    assert seen == [("yz.chsi.com.cn", REDLINE_MIN_INTERVAL_S)]


def test_conditional_host_keeps_higher_caller_interval(monkeypatch):
    """调用方给得更宽松时也不下调——红线域下限只抬不降。"""
    seen: list[tuple[str, float]] = []
    monkeypatch.setattr(transport, "_host_throttle_redline", lambda host, interval: seen.append((host, interval)))
    fetch("https://yz.chsi.com.cn/kyzx/x", rate_limit=9.0, sender=_sender_for(200))
    assert seen == [("yz.chsi.com.cn", 9.0)]


def test_normal_host_keeps_caller_interval(monkeypatch):
    """5 秒下限只作用于红线域，不得污染其他站点的节流。"""
    seen: list[tuple[str, float]] = []
    monkeypatch.setattr(transport, "_host_throttle", lambda host, interval: seen.append((host, interval)))
    fetch("https://yz.suda.edu.cn/8386/list.htm", rate_limit=0.3, sender=_sender_for(200))
    assert seen == [("yz.suda.edu.cn", 0.3)]


def test_conditional_first_hit_still_waits(monkeypatch):
    """红线域冷桶首击也必须等满下限——普通域的空桶豁免不适用于条件放行路径。

    （09-30 真机冒烟实测发现：冷桶首次调用等待 0s，若沿用普通域逻辑，
    条件放行路径的首个请求会绕过 5 秒下限。纯桩测试测不出这点，故此处
    直接断言节流实现而非打桩它。）
    """
    slept: list[float] = []
    monkeypatch.setattr(transport.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(transport.time, "monotonic", lambda: 1000.0)

    transport._host_throttle_redline("yz.chsi.com.cn", REDLINE_MIN_INTERVAL_S)
    assert slept == [REDLINE_MIN_INTERVAL_S], "红线域首击必须等满下限"

    slept.clear()
    transport._reset_quarantine_for_tests()
    transport._host_throttle("yz.example.edu.cn", 5.0)
    assert slept == [], "普通域冷桶首击仍豁免（避免新域首请求被凭空延迟）"


# ===== 4. 域级熔断（WAF 表达"不欢迎"即停） =====


@pytest.mark.parametrize("status", sorted(_QUARANTINE_STATUSES))
def test_waf_status_quarantines_domain(monkeypatch, status):
    calls: list[str] = []
    monkeypatch.setattr(transport, "_host_throttle", lambda host, interval: None)
    sender = _sender_for(status, calls)
    with pytest.raises(HttpFetchError):
        fetch("https://yz.suda.edu.cn/a.htm", sender=sender)
    assert transport._quarantined_host("yz.suda.edu.cn")
    # 隔离期内同域再次请求：不发网络
    with pytest.raises(HttpFetchError, match="已隔离"):
        fetch("https://yz.suda.edu.cn/b.htm", sender=sender)
    assert len(calls) == 1, "隔离期内不得再发请求"


def test_quarantine_is_scoped_to_one_host(monkeypatch):
    monkeypatch.setattr(transport, "_host_throttle", lambda host, interval: None)
    with pytest.raises(HttpFetchError):
        fetch("https://yz.suda.edu.cn/a.htm", sender=_sender_for(403))
    assert transport._quarantined_host("yz.suda.edu.cn")
    assert not transport._quarantined_host("yzjzu.edu.cn"), "熔断必须按域隔离，不得连坐"


def test_ordinary_4xx_does_not_quarantine(monkeypatch):
    """404/400 是"这一页没有"，不是"不欢迎我们"，不得熔断整域。"""
    monkeypatch.setattr(transport, "_host_throttle", lambda host, interval: None)
    with pytest.raises(HttpFetchError):
        fetch("https://yz.suda.edu.cn/gone.htm", sender=_sender_for(404))
    assert not transport._quarantined_host("yz.suda.edu.cn")


def test_quarantine_expires(monkeypatch):
    """WAF 策略会变；TTL 到期后允许重探。"""
    clock = {"t": 1000.0}
    monkeypatch.setattr(transport.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(transport, "_host_throttle", lambda host, interval: None)
    with pytest.raises(HttpFetchError):
        fetch("https://yz.suda.edu.cn/a.htm", sender=_sender_for(403))
    assert transport._quarantined_host("yz.suda.edu.cn")
    clock["t"] += _QUARANTINE_TTL_S + 1
    assert not transport._quarantined_host("yz.suda.edu.cn")


def test_blocked_redline_path_not_quarantined(monkeypatch):
    """硬拒是本层判定，不产生网络请求，也就无从触发熔断。"""
    monkeypatch.setattr(transport, "_host_throttle", lambda host, interval: None)
    with pytest.raises(HttpFetchError, match="红线域名禁止外发"):
        fetch("https://yz.chsi.com.cn/zsml/x", sender=_sender_for(200))
    assert not transport._quarantined_host("yz.chsi.com.cn")


# ===== 5. 与入库闸的不变量（外发放行 ≠ 入库放行） =====


def test_redline_hosts_tuple_unchanged():
    """外发放行不得缩减红线名单本身——它是入库咽喉的单一事实源。"""
    assert REDLINE_FETCH_HOSTS == ("yz.chsi.com.cn",)
    assert REDLINE_ALLOWED_PATHS  # 条件放行走独立白名单，不动红线名单


def test_ingestion_gate_still_rejects_redline():
    """入库咽喉对红线域仍全部拒收：chsi 数据不进资讯队列，只进分数线业务表。"""
    from app.services.research_ingestion import is_redline_url

    for url in (
        "https://yz.chsi.com.cn/kyzx/fsfsx34/",  # 外发条件放行的路径
        "https://yz.chsi.com.cn/zsml/queryAction.do",
    ):
        assert is_redline_url(url), f"入库闸不得被外发放行牵连：{url}"
        assert is_redline_fetch_url(url)


def test_conditional_allowlist_excludes_business_systems():
    """白名单只许静态公开页，不得含网报/调剂/登录/目录查询。"""
    for forbidden in ("/zsml", "/login", "/reg", "/yjs", "/tjhl"):
        assert not any(forbidden in p for p in REDLINE_ALLOWED_PATHS)
