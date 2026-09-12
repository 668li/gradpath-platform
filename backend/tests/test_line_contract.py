"""地基③线契约测试（spec 002 FR2）。

- 白名单 10 源人人有线 yaml（缺一即红）；
- 生成的 DEFAULT_DAILY_SCHEDULES 与冻结的 5 条 cron 逐字一致（调度兼容）；
- 名字越界/非法 cron/非法窗口 = 加载即炸（合规硬闸负例）；
- 季节窗口判定含跨年窗口。
"""

from pathlib import Path

import pytest

from app.crawlers.compliance import ALLOWED_CRAWLER_SOURCES
from app.crawlers.line_registry import CrawlerLine, default_schedules, load_lines

CONFIG_DIR = Path(__file__).resolve().parents[1] / "app" / "crawlers" / "config"

# 2026-09-06 第一批终态冻结的 5 条默认 cron（值不得漂移；来源改为 yaml 生成）
EXPECTED_SCHEDULES = {
    "eol_kaoyan": "0 2 * * *",
    "official_announce": "0 * * * *",
    "rsshub_research": "30 2 * * *",
    "news_aggregates": "0 4 * * *",
    "bilibili_research": "0 3 * * 1",
}


def test_every_whitelisted_source_has_a_line_yaml():
    lines = load_lines()
    missing = ALLOWED_CRAWLER_SOURCES - set(lines)
    assert not missing, f"白名单源缺线契约 yaml: {sorted(missing)}（加线=放 yaml，地基③）"


def test_generated_schedules_frozen():
    schedules = default_schedules()
    assert schedules == EXPECTED_SCHEDULES, "默认调度必须与冻结的 5 条 cron 逐字一致"


def test_manual_lines_have_no_schedule():
    lines = load_lines()
    for name in ("real_data", "yanzhao", "yanzhao_program", "rss_news_research", "web_article_research"):
        assert lines[name].schedule is None, f"{name} 应为手动线（schedule: null）"


def test_sla_hours_present_for_scheduled_lines():
    lines = load_lines()
    for name in EXPECTED_SCHEDULES:
        assert lines[name].sla_hours > 0, f"{name} 缺 sla_hours（地基⑥新鲜度判据）"
    assert lines["official_announce"].sla_hours == 6


def test_rogue_yaml_name_rejected(tmp_path):
    """白名单硬闸：越界名字加载即炸（与 registry 不变量同源）。"""
    rogue = tmp_path / "rogue.yaml"
    rogue.write_text(
        "name: scoreline_real\nschedule: \"0 3 * * *\"\nentry: https://example.com\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="不在合规白名单"):
        load_lines(rogue.parent)


def test_bad_cron_rejected(tmp_path):
    cfg = tmp_path / "eol_kaoyan.yaml"
    cfg.write_text("name: eol_kaoyan\nschedule: weekly\n", encoding="utf-8")
    with pytest.raises(ValueError, match="不是合法 cron"):
        load_lines(tmp_path)


def test_bad_window_rejected(tmp_path):
    cfg = tmp_path / "eol_kaoyan.yaml"
    cfg.write_text(
        "name: eol_kaoyan\nschedule: null\nwindow: {start: 2月, end: 4月}\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="MM-DD"):
        load_lines(tmp_path)


def test_window_semantics_including_year_crossing():
    line = CrawlerLine(name="x", schedule=None, sla_hours=24, entry="", window=("11-01", "03-31"))
    assert line.in_window(12, 15) is True
    assert line.in_window(1, 15) is True
    assert line.in_window(6, 15) is False

    line2 = CrawlerLine(name="y", schedule=None, sla_hours=24, entry="", window=("02-15", "04-30"))
    assert line2.in_window(3, 1) is True
    assert line2.in_window(5, 1) is False
