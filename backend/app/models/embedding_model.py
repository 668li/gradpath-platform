"""文档向量模型 — 存储 Embedding 用于 RAG 检索。"""
import uuid

from sqlalchemy import Column, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB as CustomJSONB, TimestampMixin, UUIDMixin


class DocumentEmbedding(UUIDMixin, TimestampMixin, Base):
    """文档向量表 — 存储各数据源的文本 Embedding。

    用于 RAG 检索，支持向量相似度搜索和元数据过滤。
    """
    __tablename__ = "document_embeddings"
    __table_args__ = (
        Index("ix_embedding_source", "source_table", "source_id"),
        Index("ix_embedding_doc_metadata_gin", "doc_metadata", postgresql_using="gin"),
    )

    source_table: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_metadata: Mapped[dict] = mapped_column(CustomJSONB, nullable=False, default=dict)
    # embedding 列由 pgvector 提供，这里用 Text 存储以兼容迁移
    # 实际查询时使用原生 SQL + vector 类型
    embedding_vector: Mapped[str | None] = mapped_column(Text, nullable=True)


class RAGStats(UUIDMixin, TimestampMixin, Base):
    """RAG 系统统计 — 记录向量化进度和统计信息。"""
    __tablename__ = "rag_stats"

    total_documents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_embeddings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_rebuild_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_counts: Mapped[dict] = mapped_column(CustomJSONB, nullable=False, default=dict)
