"""声明式爬虫线契约（数据地基③，spec 002 FR2）。

**一线一 yaml**：线契约直接承载在既有 ``config/*.yaml`` 上（单一事实源，
拒绝"调度 yaml + 配置 yaml"双轨）。契约字段：

.. code-block:: yaml

    name: eol_kaoyan              # 必须在合规白名单（硬闸：越界=加载即炸）
    schedule: "0 2 * * *"         # cron（北京时间）；null=手动线（不进默认调度）
    sla_hours: 24                 # 新鲜度 SLA（心跳老化/死线的判据，地基⑥消费）
    entry: https://kaoyan.eol.cn/nnews/   # 主入口
    window:                       # 可选季节窗口（MM-DD），窗口外调度跳过
      start: "02-15"
      end: "04-30"

既有运行时字段（rate_limit/max_retries/keywords/routes/sections…）照旧由
``crawler_config.load_config`` 消费，本模块只负责**契约层校验与调度生成**：
- 白名单硬闸：yaml 名不在 ALLOWED_CRAWLERS → ValueError（注册表==白名单
  不变量的姊妹闸：加线必须先过合规评审进白名单，否则连配置都加载不了）；
- cron 校验：schedule 非空必须可被 APScheduler CronTrigger 解析；
- 默认调度生成：``default_schedules()`` 替代手写 DEFAULT_DAILY_SCHEDULES
  （加一条线 = 放 yaml，调度自动补齐，不动 api 层一行代码）。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from apscheduler.triggers.cron import CronTrigger

from app.crawlers.compliance import ALLOWED_CRAWLER_SOURCES

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent / "config"

# 季节窗口字段格式
_WINDOW_FIELDS = ("start", "end")


@dataclass
class CrawlerLine:
    """一条声明式爬虫线（契约字段 + 原始配置）。"""

    name: str
    schedule: str | None  # cron 字符串；None=手动线
    sla_hours: int
    entry: str
    window: tuple[str, str] | None = None
    enabled: bool = True
    raw: dict = field(default_factory=dict)

    def in_window(self, month: int, day: int) -> bool:
        """是否在季节窗口内（跨年窗口语义：start>end 视为跨年区间）。"""
        if not self.window:
            return True
        start_m, start_d = (int(x) for x in self.window[0].split("-"))
        end_m, end_d = (int(x) for x in self.window[1].split("-"))
        today = month * 100 + day
        start, end = start_m * 100 + start_d, end_m * 100 + end_d
        if start <= end:
            return start <= today <= end
        return today >= start or today <= end  # 跨年窗口


def _parse_window(raw_window: dict, name: str) -> tuple[str, str]:
    if not isinstance(raw_window, dict) or not all(f in raw_window for f in _WINDOW_FIELDS):
        raise ValueError(f"爬虫线 {name}: window 需为 {{start: MM-DD, end: MM-DD}}")
    for f in _WINDOW_FIELDS:
        parts = str(raw_window[f]).split("-")
        if len(parts) != 2 or not all(p.isdigit() and 1 <= int(p) <= 99 for p in parts) or not (
            1 <= int(parts[0]) <= 12 and 1 <= int(parts[1]) <= 31
        ):
            raise ValueError(f"爬虫线 {name}: window.{f} 需为 MM-DD 格式，收到 {raw_window[f]!r}")
    return str(raw_window["start"]), str(raw_window["end"])


def _validate_schedule(name: str, schedule) -> str | None:
    if schedule in (None, "", False):
        return None
    try:
        CronTrigger.from_crontab(str(schedule))
    except ValueError as e:
        raise ValueError(f"爬虫线 {name}: schedule {schedule!r} 不是合法 cron: {e}") from e
    return str(schedule)


def load_lines(config_dir: Path | None = None) -> dict[str, CrawlerLine]:
    """加载并校验全部线契约。目录缺省 = 空注册（允许无配置启动）；
    **名字越界 = ValueError**（合规硬闸，加载即炸）。
    """
    directory = Path(config_dir) if config_dir else CONFIG_DIR
    lines: dict[str, CrawlerLine] = {}
    if not directory.exists():
        return lines
    for path in sorted(directory.glob("*.yaml")):
        try:
            cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"爬虫线配置 {path.name} YAML 解析失败: {e}") from e
        name = (cfg.get("name") or "").strip()
        if not name:
            logger.warning("线契约 %s 缺 name 字段，跳过", path.name)
            continue
        if name not in ALLOWED_CRAWLER_SOURCES:
            raise ValueError(
                f"爬虫线 {name}（{path.name}）不在合规白名单——加线必须先过合规评审"
                f"（ALLOWED_CRAWLERS 显式 diff）"
            )
        schedule = _validate_schedule(name, cfg.get("schedule"))
        window = _parse_window(cfg["window"], name) if cfg.get("window") else None
        sla = int(cfg.get("sla_hours", 48))
        lines[name] = CrawlerLine(
            name=name,
            schedule=schedule,
            sla_hours=sla,
            entry=str(cfg.get("entry", "")),
            window=window,
            enabled=bool(cfg.get("enabled", True)),
            raw=cfg,
        )
    return lines


def default_schedules(config_dir: Path | None = None) -> dict[str, str]:
    """从线契约生成默认调度表（enabled 且有 cron 的线）。

    替代手写 DEFAULT_DAILY_SCHEDULES：加线 = 放 yaml，调度自动补齐。
    """
    return {
        name: line.schedule
        for name, line in load_lines(config_dir).items()
        if line.enabled and line.schedule
    }
