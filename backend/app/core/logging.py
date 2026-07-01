"""结构化日志配置 — JSON 格式输出，支持 request_id 追踪。"""
import logging
import sys
from logging.config import dictConfig

import contextvars

# 请求 ID 上下文变量
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """注入 request_id 到日志记录。"""

    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


def setup_logging(log_level: str = "INFO"):
    """配置结构化 JSON 日志。

    默认使用 console formatter（人类可读，便于开发），其中包含 request_id；
    JSON formatter 同样可用，便于生产环境对接日志聚合系统。
    """
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": RequestIdFilter,
            },
        },
        "formatters": {
            "json": {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s",
            },
            "console": {
                "format": "%(asctime)s [%(levelname)s] %(name)s [%(request_id)s] %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stderr,
                "filters": ["request_id"],
                "formatter": "console",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
    })
