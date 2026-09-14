"""地基①守卫：app/crawlers 内禁止裸外发请求（spec 002 FR1）。

一切外发 HTTP 只许经 transport.fetch（直接调用或经 BaseCrawler._request 委托），
SSRF/robots/限速/错误分级/证据采集才有唯一落点。本测试静态扫描源码文本，
凡 httpx.get/httpx.Client/requests.get/requests.Session/urlopen 出现在
传输层与渲染层之外的爬虫文件里即红——防新增绕过，不靠自觉。

豁免（各自有完整护栏或本身即是护栏）：
- transport.py：统一传输层本体
- base_crawler.py：robots.txt 拉取（urllib）+ sender 注入会话
- crawl4ai_client.py：浏览器渲染层（自有 SSRF 护栏）
- url_safety.py：SSRF 校验器，不发请求

2026-09-13 清场注记：crawl4ai_scraper.py（自declared废弃的 ad-hoc 验证脚本，
绕 SSRF/绕审核队列）已物理删除并从豁免名单摘除。
"""

import re
from pathlib import Path

CRAWLERS_DIR = Path(__file__).resolve().parents[1] / "app" / "crawlers"

EXEMPT = {
    "transport.py",
    "base_crawler.py",
    "crawl4ai_client.py",
    "url_safety.py",
}

_RAW_PATTERNS = re.compile(
    r"httpx\.(get|post|put|delete|head|request|Client|AsyncClient)\b"
    r"|requests\.(get|post|put|delete|head|request|Session)\b"
    r"|urlopen\("
)


def test_no_raw_outbound_http_outside_transport():
    offenders: list[str] = []
    for py in sorted(CRAWLERS_DIR.rglob("*.py")):
        if py.name in EXEMPT or py.name == "__init__.py":
            continue
        src = py.read_text(encoding="utf-8")
        for m in _RAW_PATTERNS.finditer(src):
            line_no = src.count("\n", 0, m.start()) + 1
            offenders.append(f"{py.relative_to(CRAWLERS_DIR)}:{line_no}: {m.group(0)}")
    assert (
        not offenders
    ), "发现裸外发请求（必须走 transport.fetch / BaseCrawler._request）：\n" + "\n".join(offenders)


def test_redline_host_never_fetched():
    """传输层红线闸：研招网域任何形态的外发都必须在 fetch() 入口被拒。"""
    from app.crawlers.transport import HttpFetchError, fetch, is_redline_fetch_url

    assert is_redline_fetch_url("https://yz.chsi.com.cn/zsml/queryAction.do")
    assert is_redline_fetch_url("https://sub.yz.chsi.com.cn/x")
    assert not is_redline_fetch_url("https://gaokao.chsi.com.cn/")  # 09-06 豁免子域
    assert not is_redline_fetch_url("https://kaoyan.eol.cn/")

    import pytest

    with pytest.raises(HttpFetchError, match="红线域名禁止外发"):
        fetch("https://yz.chsi.com.cn/zsml/queryAction.do")
