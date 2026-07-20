"""Prometheus 多进程指标收集 — 基于 prometheus_client。

设计要点（A14）：
1. 多 worker 支持：使用 `prometheus_client.multiprocess.MultiProcessCollector`
   聚合各 worker 进程的指标文件（位于 `PROMETHEUS_MULTIPROC_DIR` 目录）。
2. 与现有 `app/api/metrics.py` 共存：
   - `app/api/metrics.py` 继续提供 `/api/metrics`（自定义格式，兼容老测试）
   - `app/metrics.py` 通过 `/metrics`（无 /api 前缀）暴露 prometheus_client 标准格式
3. 指标定义：
   - REQUEST_COUNT (Counter, labels: method/path/status)
   - REQUEST_LATENCY (Histogram, labels: method/path)
   - LLM_CALL_COUNT (Counter, labels: model/status)
   - LLM_CALL_LATENCY (Histogram, labels: model)
   - ACTIVE_WEBSOCKETS (Gauge)
4. 启动时清理 multiproc 目录，避免旧文件污染。
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 多进程目录 — 必须在 prometheus_client 导入前设置
PROMETHEUS_MULTIPROC_DIR = os.environ.get(
    "PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc"
)


def _ensure_multiproc_dir() -> None:
    """确保多进程目录存在。

    每次进程启动时清空旧文件，避免僵尸 worker 残留文件污染聚合结果。
    仅在主进程（启动时）调用一次。
    """
    try:
        Path(PROMETHEUS_MULTIPROC_DIR).mkdir(parents=True, exist_ok=True)
        # 清空旧文件（仅清理 .db / .ldb 等指标文件）
        for entry in Path(PROMETHEUS_MULTIPROC_DIR).iterdir():
            try:
                if entry.is_file():
                    entry.unlink()
            except Exception:
                pass
    except Exception as e:
        logger.warning("初始化 PROMETHEUS_MULTIPROC_DIR 失败: %s", e)


# 模块导入时确保目录存在（仅在配置了环境变量时生效）
if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
    _ensure_multiproc_dir()


# ----------------------------------------------------------------------
# 指标定义 — 使用 prometheus_client
# ----------------------------------------------------------------------
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        CollectorRegistry,
        multiprocess,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )

    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client 未安装，多进程监控指标不可用")

# 全局 Registry（多进程模式下延迟创建）
_REGISTRY: Optional["CollectorRegistry"] = None


def _get_registry() -> "CollectorRegistry":
    """获取 CollectorRegistry。

    多进程模式（PROMETHEUS_MULTIPROC_DIR 已设置）下创建一个新的 CollectorRegistry
    并通过 MultiProcessCollector 聚合所有 worker 的指标文件；否则使用 prometheus_client
    的默认 REGISTRY（全局指标自动注册到此处）。
    """
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY

    if not _PROMETHEUS_AVAILABLE:
        raise RuntimeError("prometheus_client 未安装")

    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        # 多进程模式：用独立 registry 收集 multiproc 文件
        registry = CollectorRegistry()
        try:
            multiprocess.MultiProcessCollector(registry)
            logger.info("Prometheus 多进程指标收集已启用: dir=%s", PROMETHEUS_MULTIPROC_DIR)
        except Exception as e:
            logger.warning("启用多进程指标收集失败，降级到单进程: %s", e)
        _REGISTRY = registry
        return registry
    else:
        # 单进程模式：使用默认 REGISTRY（全局 Counter/Histogram/Gauge 自动注册到此处）
        from prometheus_client import REGISTRY as _DEFAULT_REGISTRY
        _REGISTRY = _DEFAULT_REGISTRY
        return _REGISTRY


# 指标定义（仅 prometheus_client 可用时定义）
if _PROMETHEUS_AVAILABLE:
    # 注意：Counter / Histogram / Gauge 必须在导入时定义一次（prometheus_client 的限制），
    # 多进程模式下指标文件会写入 PROMETHEUS_MULTIPROC_DIR，由 MultiProcessCollector 聚合。

    REQUEST_COUNT = Counter(
        "gradpath_http_requests_total",
        "Total HTTP requests count",
        ["method", "path", "status"],
    )

    REQUEST_LATENCY = Histogram(
        "gradpath_http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "path"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    LLM_CALL_COUNT = Counter(
        "gradpath_llm_calls_total",
        "Total LLM API calls",
        ["model", "status"],
    )

    LLM_CALL_LATENCY = Histogram(
        "gradpath_llm_call_duration_seconds",
        "LLM API call latency in seconds",
        ["model"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    )

    ACTIVE_WEBSOCKETS = Gauge(
        "gradpath_active_websockets",
        "Number of active WebSocket connections",
    )

    # C9 Web Vitals 指标 — 每个指标取最新值（Gauge），按 page + rating 标签维度
    WEB_VITALS_LCP = Gauge(
        "gradpath_web_vitals_lcp",
        "Largest Contentful Paint (ms) — 最新值",
        ["page", "rating"],
    )
    WEB_VITALS_CLS = Gauge(
        "gradpath_web_vitals_cls",
        "Cumulative Layout Shift — 最新值",
        ["page", "rating"],
    )
    WEB_VITALS_INP = Gauge(
        "gradpath_web_vitals_inp",
        "Interaction to Next Paint (ms) — 最新值",
        ["page", "rating"],
    )
    WEB_VITALS_TTFB = Gauge(
        "gradpath_web_vitals_ttfb",
        "Time to First Byte (ms) — 最新值",
        ["page", "rating"],
    )
    WEB_VITALS_FCP = Gauge(
        "gradpath_web_vitals_fcp",
        "First Contentful Paint (ms) — 最新值",
        ["page", "rating"],
    )
    WEB_VITALS_REPORT_COUNT = Counter(
        "gradpath_web_vitals_reports_total",
        "Total web-vitals reports received",
        ["name", "rating"],
    )
else:
    # 占位符 — 调用方仍可安全调用 .labels().inc() 等（无副作用）
    REQUEST_COUNT = None  # type: ignore
    REQUEST_LATENCY = None  # type: ignore
    LLM_CALL_COUNT = None  # type: ignore
    LLM_CALL_LATENCY = None  # type: ignore
    ACTIVE_WEBSOCKETS = None  # type: ignore
    WEB_VITALS_LCP = None  # type: ignore
    WEB_VITALS_CLS = None  # type: ignore
    WEB_VITALS_INP = None  # type: ignore
    WEB_VITALS_TTFB = None  # type: ignore
    WEB_VITALS_FCP = None  # type: ignore
    WEB_VITALS_REPORT_COUNT = None  # type: ignore


# ----------------------------------------------------------------------
# 便捷函数 — 供中间件与服务层调用
# ----------------------------------------------------------------------
def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    """记录一次 HTTP 请求的指标。

    供 main.py 的 request_logging_middleware 调用。同时调用原有 record_request
    保持 /api/metrics 兼容。
    """
    # prometheus_client 指标
    if _PROMETHEUS_AVAILABLE and REQUEST_COUNT is not None:
        try:
            REQUEST_COUNT.labels(method=method, path=path, status=str(status_code)).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration_seconds)
        except Exception as e:
            logger.debug("记录 prometheus HTTP 指标失败: %s", e)

    # 同时调用旧版 record_request 维持 /api/metrics 兼容
    try:
        from app.api.metrics import record_request
        record_request(method, path, status_code, duration_seconds * 1000.0)
    except Exception:
        pass


def record_llm_call(model: str, status: str, duration_seconds: float) -> None:
    """记录一次 LLM 调用的指标。

    供 ai_service.py 的 chat 方法调用。
    """
    if not _PROMETHEUS_AVAILABLE or LLM_CALL_COUNT is None:
        return
    try:
        LLM_CALL_COUNT.labels(model=model, status=status).inc()
        LLM_CALL_LATENCY.labels(model=model).observe(duration_seconds)
    except Exception as e:
        logger.debug("记录 prometheus LLM 指标失败: %s", e)


def set_active_websockets(count: int) -> None:
    """更新活跃 WebSocket 连接数。"""
    if not _PROMETHEUS_AVAILABLE or ACTIVE_WEBSOCKETS is None:
        return
    try:
        ACTIVE_WEBSOCKETS.set(count)
    except Exception as e:
        logger.debug("更新 prometheus WebSocket 指标失败: %s", e)


# C9 Web Vitals 指标名 → Prometheus Gauge 映射
_WEB_VITALS_GAUGE_MAP = {
    "LCP": "WEB_VITALS_LCP",
    "CLS": "WEB_VITALS_CLS",
    "INP": "WEB_VITALS_INP",
    "TTFB": "WEB_VITALS_TTFB",
    "FCP": "WEB_VITALS_FCP",
}


def record_web_vital(name: str, value: float, rating: str, page: str) -> None:
    """记录一条 web-vital 指标到 Prometheus。

    Args:
        name: 指标名（LCP/CLS/INP/TTFB/FCP）
        value: 指标值（LCP/INP/TTFB/FCP 单位 ms；CLS 无单位）
        rating: 评级（good/needs-improvement/poor）
        page: 触发指标的页面路径
    """
    if not _PROMETHEUS_AVAILABLE:
        return

    gauge_attr = _WEB_VITALS_GAUGE_MAP.get(name.upper())
    if gauge_attr is None:
        logger.debug("未知 web-vital 指标名: %s", name)
        return

    gauge = globals().get(gauge_attr)
    if gauge is None:
        return

    try:
        gauge.labels(page=page or "/", rating=rating).set(float(value))
    except Exception as e:
        logger.debug("记录 prometheus web-vital 指标失败: %s", e)

    if WEB_VITALS_REPORT_COUNT is not None:
        try:
            WEB_VITALS_REPORT_COUNT.labels(name=name.upper(), rating=rating).inc()
        except Exception as e:
            logger.debug("记录 prometheus web-vital 计数失败: %s", e)


def render_metrics() -> tuple[bytes, str]:
    """渲染 Prometheus 格式指标字节串与 Content-Type。

    供 /metrics 端点调用。
    """
    if not _PROMETHEUS_AVAILABLE:
        return b"# prometheus_client not installed\n", "text/plain; charset=utf-8"
    registry = _get_registry()
    return generate_latest(registry), CONTENT_TYPE_LATEST


def is_available() -> bool:
    """prometheus_client 是否可用。"""
    return _PROMETHEUS_AVAILABLE
