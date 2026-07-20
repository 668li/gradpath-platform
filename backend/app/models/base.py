import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as _PG_UUID
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


class GUID(TypeDecorator):
    """跨方言 UUID 类型。

    - PostgreSQL：使用原生 UUID(as_uuid=True)
    - SQLite / 其它：使用 CHAR(32)，存储 UUID 的 hex（无连字符），Python 端为 uuid.UUID 对象

    解决 postgresql UUID 类型在 SQLite 上存储全零 UUID 时被错误转为整数 0 的问题。
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value.hex
        # 兼容字符串输入
        try:
            return uuid.UUID(str(value)).hex
        except (ValueError, AttributeError):
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            return uuid.UUID(value)
        # 兼容 SQLite 可能返回的整数（历史脏数据防护）
        if isinstance(value, int):
            return uuid.UUID(int=value)
        return value


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
        GUID(), primary_key=True, default=uuid.uuid4
    )
