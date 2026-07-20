"""Structured logging — JSON output with request_id and correlation_id tracking."""
import logging
import sys
from logging.config import dictConfig

import contextvars

# Request ID context variable
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# Correlation ID — persists across middleware boundaries and downstream calls
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


class RequestIdFilter(logging.Filter):
    """Inject request_id and correlation_id into log records."""

    def filter(self, record):
        record.request_id = request_id_var.get()
        record.correlation_id = correlation_id_var.get()
        return True


def setup_logging(log_level: str = "INFO"):
    """Configure structured JSON logging.

    Uses console formatter for development (human-readable) with request_id;
    JSON formatter available for production log aggregation.
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
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s %(correlation_id)s",
            },
            "console": {
                "format": "%(asctime)s [%(levelname)s] %(name)s [req=%(request_id)s corr=%(correlation_id)s] %(message)s",
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
