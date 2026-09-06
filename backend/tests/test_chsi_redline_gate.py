"""chsi（研招网）合规红线回归 — 对抗审计 F2 修复锁死（2026-09-06）。

红线性质 = 任何路径不可越，故三道防线各自实测：
1. 信任标签层：chsi 不在官方域名表，URL 不再自证 official_verified
2. 入库唯一咽喉：store_research_items 写入即拒（不落库、可审计计数）
3. 人工放行层：promote_external_item 对 chsi 行 raise（直写库旁路也挡）
另锁 yanzhao 审核 URL 不再伪造 chsi 域名。
"""

from urllib.parse import urlparse

import pytest

from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.services.research_ingestion import (
    _OFFICIAL_DOMAINS,
    _infer_credibility,
    is_redline_url,
    store_research_items,
)
from app.services.research_promote import promote_external_item

_CHSI_URL = "https://yz.chsi.com.cn/kyzx/other/202601/123456.html"
_REAL_SUBDOMAIN = "https://foo.yz.chsi.com.cn/x"  # yz.chsi.com.cn 子域同样命中红线


# ---------------------------------------------------------------- 防线 1：信任标签


def test_chsi_not_in_official_domains():
    """官方域名表不得含 chsi；chsi URL 最高只能拿 model_inferred。"""
    assert all("chsi" not in d for d in _OFFICIAL_DOMAINS)
    assert _infer_credibility(_CHSI_URL, "web") != "official_verified"
    assert _infer_credibility(_CHSI_URL, "web") == "model_inferred"


def test_redline_detector_covers_host_and_subdomain():
    assert is_redline_url(_CHSI_URL)
    assert is_redline_url(_REAL_SUBDOMAIN)
    assert is_redline_url("https://yz.chsi.com.cn#yanzhao:清华:计算机")  # 历史伪 URL 形态
    assert not is_redline_url("https://yjs.tsinghua.edu.cn/")
    assert not is_redline_url("curated://yanzhao/清华大学/计算机")
    assert not is_redline_url("")


# ---------------------------------------------------------------- 防线 2：入库咽喉


def test_store_rejects_chsi_before_queue(db_session):
    """chsi 条目经唯一咽喉 → 零落库、零入审核队列、redline_rejected 计数。"""
    result = store_research_items(
        db_session,
        crawler_name="real_data",  # 用白名单内爬虫名：白名单内也照样拒，红线不分亲疏
        item_type="kaoyan_news",
        items=[{"title": "伪官方公告", "content": "x" * 80, "source_url": _CHSI_URL}],
        source_platform="web",
        run_id="0" * 32,
    )
    assert result["inserted"] == 0
    assert result["redline_rejected"] == 1
    assert db_session.query(ExternalResearchItem).count() == 0
    assert db_session.query(ReviewQueueItem).count() == 0


def test_store_admits_non_redline_control(db_session):
    """对照组：同批次非红线 URL 正常入库——证明拒收是红线判定而非全量误杀。"""
    result = store_research_items(
        db_session,
        crawler_name="real_data",
        item_type="kaoyan_news",
        items=[
            {"title": "真公告", "content": "y" * 80, "source_url": "https://news.pku.edu.cn/a1"}
        ],
        source_platform="web",
        run_id="0" * 32,
    )
    assert result["inserted"] == 1
    assert result["redline_rejected"] == 0


# ---------------------------------------------------------------- 防线 3：人工放行纵深


def test_promote_rejects_chsi_row(db_session):
    """即使绕过入库层直写一条 chsi 行，人工 promote 也必须失败（不落业务表）。"""
    ext = ExternalResearchItem(
        crawler_name="real_data",
        crawler_run_id="0" * 32,
        item_type="kaoyan_news",
        title="直写旁路",
        content="z" * 80,
        source_url=_CHSI_URL,
        source_platform="web",
        credibility="model_inferred",
        review_status="PENDING",
    )
    db_session.add(ext)
    db_session.flush()
    with pytest.raises(ValueError, match="研招网红线"):
        promote_external_item(db_session, ext, "admin@example.com")


# ---------------------------------------------------------------- yanzhao 伪 URL 拆除


def test_yanzhao_review_url_never_chsi():
    """yanzhao 预置数据审核 URL：可映射校挂校官方页，不可映射走 curated://，全程无 chsi。"""
    from app.crawlers.grad.yanzhao_crawler import _review_url

    mapped = _review_url(
        {"university_name": "清华大学", "department": "计算机系", "major_name": "计算机"}
    )
    assert "chsi" not in mapped.lower()
    assert urlparse(mapped).hostname.endswith("tsinghua.edu.cn")

    unmapped = _review_url({"university_name": "不存在大学", "major_name": "冶金"})
    assert "chsi" not in unmapped.lower()
    assert unmapped.startswith("curated://yanzhao/")
    # 幂等：同条目重复生成 URL 不变（队列去重键依赖稳定性）
    assert unmapped == _review_url({"university_name": "不存在大学", "major_name": "冶金"})
