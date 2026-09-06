"""爬取增量架构测试：per-host 节流 + URL 级增量 + 公告线提频迁移。

- per-host 节流：同域间隔 ≥ rate_limit（礼貌性不降级）；跨域互不等待
  （修复全局串行"一慢全慢"），且锁不跨 sleep 持有。
- URL 级增量：已收录条目（归一化 URL 命中基线）跳过详情抓取并计数
  known_skipped——高频轮询下 90%+ 条目是重复，这是吞吐的关键。
- 提频：official_announce 默认 cron 每小时；seed 对旧 cron 存量 job 做一次性迁移。
"""

import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crawlers.career import boss_crawler, interview_crawler, lagou_crawler  # noqa: E402
from app.crawlers.research.dedup import normalize_url  # noqa: E402
from app.crawlers.research.official_announce_crawler import (  # noqa: E402
    OfficialAnnounceCrawler,
    _load_known_urls,
    _parse_list_entries,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "official_announce"

_UESTC_LIST = (FIXTURE_DIR / "uestc_tz118.html").read_text(encoding="utf-8")
_UESTC_BASE = "https://gr.uestc.edu.cn/tongzhi/118"

_DETAIL_HTML = (
    "<html><head><title>t</title></head><body><div class='v_news_content'>"
    "正文内容用于占位，长度必须超过八字截断线，否则走降级正则也无妨，反正是同一份响应。"
    "</div></body></html>"
)


# ===== per-host 节流 =====


class _ThrottleCrawler:
    """借用 OfficialAnnounceCrawler 的节流基类，只测 _throttle 本身。"""

    def __new__(cls):
        from app.crawlers.base_crawler import BaseCrawler

        class _Minimal(BaseCrawler):
            name = "throttle_probe"
            category = "test"

            def fetch(self):
                return []

            def parse(self, raw):
                return raw

            def store(self, items, db=None):
                return 0

        return _Minimal(config={"rate_limit": 0.3})


def test_per_host_throttle_same_domain_gap():
    crawl = _ThrottleCrawler()
    crawl._throttle("a.edu.cn")
    t0 = time.monotonic()
    crawl._throttle("a.edu.cn")
    assert time.monotonic() - t0 >= 0.28, "同域第二次请求必须等待 ≥ rate_limit"


def test_per_host_throttle_cross_domain_no_wait():
    crawl = _ThrottleCrawler()
    crawl._throttle("a.edu.cn")
    t0 = time.monotonic()
    crawl._throttle("b.edu.cn")
    assert time.monotonic() - t0 < 0.15, "跨域不应被 a 域的上次请求拖住"


def test_per_host_throttle_cross_domain_parallel_throughput():
    crawl = _ThrottleCrawler()
    barrier = threading.Barrier(2)

    def worker(host):
        barrier.wait()
        crawl._throttle(host)
        crawl._throttle(host)

    t0 = time.monotonic()
    threads = [threading.Thread(target=worker, args=(h,)) for h in ("x.edu.cn", "y.edu.cn")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.monotonic() - t0
    assert wall < 0.55, f"两域并行应各等一次 0.3s（≈0.3s），实测 {wall:.2f}s——疑似退化回全局串行"


# ===== URL 级增量 =====


def _make_official(detail_calls: list):
    """构造 uestc 单栏目爬虫：_request 全 mock（不打外网），统计详情请求数。"""

    class _Patched(OfficialAnnounceCrawler):
        def _request(self, url, method="GET", **kwargs):
            if url == _UESTC_BASE:
                resp = type("R", (), {})()
                resp.text = _UESTC_LIST
                resp.status_code = 200
                return resp
            detail_calls.append(url)
            resp = type("R", (), {})()
            resp.text = _DETAIL_HTML
            resp.status_code = 200
            return resp

    return _Patched(
        config={
            "sections": [
                {
                    "name": "uestc 通知",
                    "list_url": _UESTC_BASE,
                    "cms": "generic",
                    "detail_url_re": r"tongzhi/\d+/\d+",
                }
            ],
            "rate_limit": 0,
            "fetch_detail": True,
        }
    )


def _entry_urls() -> list:
    return [e["url"] for e in _parse_list_entries(_UESTC_LIST, "generic", _UESTC_BASE)]


def test_official_increment_skips_all_known(monkeypatch):
    entries = _entry_urls()
    assert len(entries) >= 5, "夹具前提：uestc 列表应有足量条目"
    monkeypatch.setattr(
        "app.crawlers.research.official_announce_crawler._load_known_urls",
        lambda: {normalize_url(u) for u in entries},
    )
    detail_calls: list = []
    crawl = _make_official(detail_calls)
    crawl.fetch()
    assert len(detail_calls) == 0, "全部已收录时不应再抓任何详情"
    assert crawl.stats.get("known_skipped") == len(entries)


def test_official_increment_fetches_only_unknown(monkeypatch):
    entries = _entry_urls()
    known = {normalize_url(entries[0])}
    monkeypatch.setattr(
        "app.crawlers.research.official_announce_crawler._load_known_urls",
        lambda: known,
    )
    detail_calls: list = []
    crawl = _make_official(detail_calls)
    crawl.fetch()
    assert len(detail_calls) == len(entries) - 1, "只应抓取未收录条目的详情"
    assert crawl.stats.get("known_skipped") == 1


def test_load_known_urls_degrades_to_empty_on_db_failure(monkeypatch):
    """基线加载失败必须退化为空集（全量抓取），绝不丢数据。"""

    def _boom(db):
        raise RuntimeError("db down")

    monkeypatch.setattr(
        "app.crawlers.research.official_announce_crawler._load_kaoyan_dedup_baseline", _boom
    )
    assert _load_known_urls() == set()


# ===== 提频与 seed 迁移 =====


def test_default_schedule_official_hourly():
    from app.api.crawlers import DEFAULT_DAILY_SCHEDULES

    assert DEFAULT_DAILY_SCHEDULES["official_announce"] == "0 * * * *"
    assert DEFAULT_DAILY_SCHEDULES["eol_kaoyan"] == "0 2 * * *", "其他源默认频率不受影响"
    assert DEFAULT_DAILY_SCHEDULES["news_aggregates"] == "0 4 * * *", "资讯聚合每日 04:00"


def test_news_aggregate_crawler_registered():
    """资讯聚合爬虫：注册 + 白名单 + 栏目表就位（量的来源线）。"""
    from app.crawlers.compliance import ALLOWED_CRAWLER_SOURCES
    from app.crawlers.registry import get_crawler

    cls = get_crawler("news_aggregates")
    assert cls is not None, "news_aggregates 应已注册"
    assert "news_aggregates" in ALLOWED_CRAWLER_SOURCES
    crawler = cls(config={"fetch_detail": False})
    assert len(crawler.sections) == 5
    assert crawler.DEFAULT_SECTIONS_OVERRIDE is not None


def test_seed_replaces_stale_cron(monkeypatch):
    """存量 02:00 job（seed 体系旧默认）应被一次性迁移到每小时。"""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.memory import MemoryJobStore

    import app.api.crawlers as api_crawlers

    sched = BackgroundScheduler(jobstores={"default": MemoryJobStore()})
    sched.start()
    try:
        sched.add_job(
            api_crawlers._run_scheduled_crawler,
            "cron",
            id="crawler_official_announce",
            kwargs={"source_name": "official_announce"},
            replace_existing=True,
            minute="2",
            hour="2",
            day="*",
            month="*",
            day_of_week="*",
        )
        monkeypatch.setattr(api_crawlers, "get_scheduler", lambda: sched)
        api_crawlers.seed_default_schedules()

        job = sched.get_job("crawler_official_announce")
        assert job is not None
        assert api_crawlers._job_cron_str(job) == "0 * * * *", "旧 cron 存量 job 应被替换为每小时"
        eol = sched.get_job("crawler_eol_kaoyan")
        assert api_crawlers._job_cron_str(eol) == "0 2 * * *", "其他源照常补齐"
    finally:
        sched.shutdown(wait=False)


# ===== 假就业源注销 =====


def test_synthetic_career_crawlers_deregistered():
    """random.seed/_COMPANIES 合成生成器不得再出现在注册表（防 581 重演）。"""
    from app.crawlers.registry import get_crawler

    for name in ("boss", "lagou", "interview", "company_review", "salary_data"):
        assert get_crawler(name) is None, f"{name} 应已注销注册"
    assert boss_crawler.BossCrawler is not None and lagou_crawler.LagouCrawler is not None
    assert interview_crawler.InterviewCrawler is not None, "类本身保留（文件不删）"
