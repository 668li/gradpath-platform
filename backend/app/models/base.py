import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def _utcnow() -> datetime:
    """时区感知的当前 UTC 时间（带微秒精度）。

    用作 Python 端默认值，确保 SQLite（测试/开发）与 PostgreSQL（生产）下
    created_at/updated_at 都具备亚秒精度，从而按时间排序时行为确定。
    """
    return datetime.now(timezone.utc)


class JSONB(TypeDecorator):
    """跨方言 JSON 类型：PostgreSQL 上使用原生 JSONB，其它方言（如 SQLite 测试）回退为 JSON。"""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PG_JSONB())
        return dialect.type_descriptor(JSON())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        onupdate=_utcnow,
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
