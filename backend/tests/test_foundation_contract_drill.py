"""验收判据 1+2（spec 002 FR6/FR8）：虚构源走完契约的演练。

证明「加一条线 = 一个 yaml + 一个纯函数 parser + 录制样本 + 断言」是机械动作：
加线的人不需要读懂任何已有爬虫的代码，全链 = 契约加载 → 纯函数解析 →
证据盖章 → 入库咽喉。

红线声明（spec R1）：虚构源只存在于本测试进程——临时目录 yaml + 内存 sqlite，
不进合规白名单（白名单为演示临时 monkeypatch，真实名单文件不动）、
不进调度、不进生产库。与 46 个 official_announce fixture 同性质，非造假。
"""

import re
from pathlib import Path
from urllib.parse import urljoin

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.crawlers.line_registry import load_lines
from app.database import Base
from app.models.ingestion import ExternalResearchItem
from app.services.research_ingestion import _valid_evidence, store_research_items

# ===== 虚构源「校研招办通知」的三件套（加线的全部内容） =====

DEMO_YAML = """\
name: demo_source
schedule: "30 5 * * *"
sla_hours: 12
entry: "https://demo.example.edu.cn/notice/"
window: {start: "09-01", end: "10-31"}
"""

# 录制样本 1：列表页（虚构源的"真实页面"存档形态，同 eol fixture 模式）
DEMO_LIST_HTML = """
<html><body>
<div class="notice"><a href="./2026/09/a.shtml">2027 年硕士研究生招生简章发布</a>
<span class="pub">2026-09-10</span></div>
<div class="notice"><a href="./2026/09/b.shtml">推免生接收办法公示</a>
<span class="pub">2026-09-09</span></div>
<div class="notice"><a href="./2026/09/c.shtml">招生咨询会通知</a>
<span class="pub">2026-09-08</span></div>
</body></html>
"""

# 录制样本 2：详情页
DEMO_DETAIL_HTML = """
<html><body><div class="article-body"><p>一、招生专业与人数：计算机学院拟招收
硕士研究生 120 名，其中推免生不超过 60 名。</p><p>二、报名方式：全部通过
校研招办系统进行，截止时间为 2026 年 10 月 25 日。</p></div></body></html>
"""

_NOTICE_RE = re.compile(
    r'<div class="notice">\s*<a href="(?P<url>[^"]+)">(?P<title>[^<]+)</a>\s*'
    r'<span class="pub">(?P<date>[^<]+)</span>',
    re.S,
)
_BODY_RE = re.compile(r'<div class="article-body">(?P<body>.*?)</div>', re.S)

_BASE = "https://demo.example.edu.cn/notice/"


def parse_demo_notice(list_html: str, detail_html: str) -> list[dict]:
    """纯函数：输入 HTML 输出 dict——不发请求、不碰库（契约②）。"""
    m = _BODY_RE.search(detail_html or "")
    body = re.sub(r"<[^>]+>", " ", m.group("body")).strip() if m else ""
    items = []
    for n in _NOTICE_RE.finditer(list_html or ""):
        items.append(
            {
                "title": n.group("title").strip(),
                "source_url": urljoin(_BASE, n.group("url")),
                "content": body or n.group("title"),
            }
        )
    return items


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def test_step1_gate_blocks_unwhitelisted_name(tmp_path):
    """第一关：合规白名单硬闸先于一切——虚构名不 patch 白名单就加载即炸。"""
    (tmp_path / "demo_source.yaml").write_text(DEMO_YAML, encoding="utf-8")
    with pytest.raises(ValueError, match="不在合规白名单"):
        load_lines(tmp_path)


def test_step2_line_contract_loads(tmp_path, monkeypatch):
    """第二关：白名单演示放行（monkeypatch，真实名单文件不动）→ 契约字段全解析。"""
    import app.crawlers.line_registry as lr
    from app.crawlers.compliance import ALLOWED_CRAWLER_SOURCES

    (tmp_path / "demo_source.yaml").write_text(DEMO_YAML, encoding="utf-8")
    monkeypatch.setattr(
        lr, "ALLOWED_CRAWLER_SOURCES", ALLOWED_CRAWLER_SOURCES | {"demo_source"}
    )
    line = load_lines(tmp_path)["demo_source"]
    assert line.schedule == "30 5 * * *"
    assert line.sla_hours == 12
    assert line.entry == "https://demo.example.edu.cn/notice/"
    assert line.window == ("09-01", "10-31")
    assert line.in_window(9, 15) is True and line.in_window(11, 1) is False


def test_step3_parse_and_evidence_and_store_full_chain(tmp_path, monkeypatch, db):
    """第三关：解析 → 证据盖章 → 入库咽喉全链绿（fetched 态证据三齐全）。"""
    import app.crawlers.line_registry as lr
    from app.crawlers.compliance import ALLOWED_CRAWLER_SOURCES

    (tmp_path / "demo_source.yaml").write_text(DEMO_YAML, encoding="utf-8")
    monkeypatch.setattr(
        lr, "ALLOWED_CRAWLER_SOURCES", ALLOWED_CRAWLER_SOURCES | {"demo_source"}
    )
    assert "demo_source" in load_lines(tmp_path)  # 契约加载通过

    items = parse_demo_notice(DEMO_LIST_HTML, DEMO_DETAIL_HTML)
    assert len(items) == 3, "2 个录制样本必须解析出全部 3 条通知"
    assert items[0]["source_url"] == "https://demo.example.edu.cn/notice/2026/09/a.shtml"
    assert "120 名" in items[0]["content"], "详情正文必须进入条目内容"

    # 模拟 BaseCrawler.run() 的统一证据盖章（地基⑤）
    stamp = {
        "http_status": 200,
        "fetched_at": "2026-09-12T13:00:00+00:00",
        "sha256": "d" * 64,
    }
    assert _valid_evidence(stamp)
    for it in items:
        it["fetch_evidence"] = dict(stamp)

    result = store_research_items(
        db,
        crawler_name="demo_source",
        item_type="kaoyan_news",
        items=items,
        source_platform="web",
        run_id="demo0000000000000000000000000000",
    )
    assert result["inserted"] == 3 and result["evidence_rejected"] == 0
    rows = db.query(ExternalResearchItem).all()
    assert len(rows) == 3
    for row in rows:
        assert row.data_origin == "fetched"
        assert row.fetch_evidence["sha256"] == stamp["sha256"]
        assert row.review_status == "PENDING"


def test_step4_bad_sample_zero_output(tmp_path, monkeypatch, db):
    """判据 2：故意改坏样本（结构漂移）→ 解析零产出 → 无证据 → 咽喉拒收。

    「改坏一个 fixture 页 → CI 必红」的负例形态：漂移不静默、缺证据不落库。
    """
    broken_list = DEMO_LIST_HTML.replace('class="notice"', 'class="item-renamed"')
    items = parse_demo_notice(broken_list, DEMO_DETAIL_HTML)
    assert items == [], "结构漂移必须零产出"

    result = store_research_items(
        db,
        crawler_name="demo_source",
        item_type="kaoyan_news",
        items=[{"title": "t", "content": "c", "source_url": "https://demo.example.edu.cn/x"}],
        source_platform="web",
        run_id="demo0000000000000000000000000000",
    )
    assert result["inserted"] == 0 and result["evidence_rejected"] == 1, "无证据必拒"
