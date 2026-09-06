"""慢查询追踪（2026-09-06 性能体检 L3/L4 补全）。

挂 SQLAlchemy 引擎级事件：每次真实执行的 SQL 计时，
  - 全量进 Prometheus DB_QUERY_LATENCY 直方图（/metrics 可看 P95）
  - > SLOW_QUERY_MS 打 warning 日志（SQL 截断，附耗时与参数摘要）
  - > CRITICAL_QUERY_MS 额外走 Server酱即时告警——单条 SQL 到秒级极罕见，
    出现即真信号（缺索引/全表扫/锁等待）

设计约束：事件回调在请求热路径上，自身必须零额外 IO——
告警发放在后台线程做，绝不阻塞查询返回。
"""

from __future__ import annotations

import logging
import threading
import time

from sqlalchemy import event

from app.config import settings

logger = logging.getLogger(__name__)

# 500ms=慢（记日志），2s=严重（微信告警）；可用环境变量覆盖
SLOW_QUERY_MS = float(getattr(settings, "SLOW_QUERY_MS", 500))
CRITICAL_QUERY_MS = float(getattr(settings, "CRITICAL_QUERY_MS", 2000))

_registered = False


def _notify_critical_async(duration_ms: float, statement: str) -> None:
    """后台线程发 Server酱，失败只留日志（告警永不影响业务）。"""

    def _send() -> None:
        try:
            from app.core.push_notify import send_serverchan

            preview = " ".join(statement.split())[:120]
            send_serverchan(
                f"🐢 慢查询 {duration_ms:.0f}ms",
                f"耗时 {duration_ms:.0f}ms\n\n```sql\n{preview}\n```",
            )
        except Exception as e:  # noqa: BLE001 — 告警失败静默
            logger.warning("慢查询告警发送失败: %s", e)

    threading.Thread(target=_send, daemon=True, name="slow-query-alert").start()


def register_db_monitor(engine) -> None:
    """在 engine 上注册查询计时事件（幂等；测试里多引擎也不重复挂）。"""
    global _registered
    if _registered:
        return

    # 延迟导入 metrics：prometheus 多进程模式下避免 import 顺序问题
    from app.metrics import DB_QUERY_LATENCY, DB_SLOW_QUERY_TOTAL

    @event.listens_for(engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        context._gp_query_start = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        start = getattr(context, "_gp_query_start", None)
        if start is None:
            return
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            DB_QUERY_LATENCY.observe(duration_ms / 1000)
        except Exception:  # noqa: BLE001 — 指标失败不影响查询
            pass
        if duration_ms >= SLOW_QUERY_MS:
            preview = " ".join(statement.split())[:200]
            logger.warning(
                "慢查询 %.0fms: %s", duration_ms, preview
            )
            try:
                DB_SLOW_QUERY_TOTAL.inc()
            except Exception:  # noqa: BLE001
                pass
            if duration_ms >= CRITICAL_QUERY_MS and not settings.ENVIRONMENT.startswith(
                ("test", "development")
            ):
                _notify_critical_async(duration_ms, statement)

    _registered = True
