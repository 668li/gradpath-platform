# backend/app/models/data_source.py
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class DataSource(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="api")
    api_url: Mapped[str | None] = mapped_column(Text)
    api_key: Mapped[str | None] = mapped_column(Text)
    data_mapping: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
