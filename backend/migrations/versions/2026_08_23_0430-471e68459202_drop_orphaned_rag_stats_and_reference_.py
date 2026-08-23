"""drop orphaned rag_stats and reference_snapshots tables

Revision ID: 471e68459202
Revises: 734e443c3f82
Create Date: 2026-08-23 04:30:21.963004+00:00

删除已废弃模型 RAGStats / ReferenceSnapshot 对应的孤儿表：
- rag_stats：RAG 统计表（统计实时计算自 document_embeddings，无历史数据依赖）
- reference_snapshots：测评快照缓存（表内数据为演示期残留，无业务读取）

注意：destination_decisions.reference_snapshot_id 为无外键的普通列，
仅历史记录引用，不构成依赖；RAG 管理 API 统计走 document_embeddings，不受影响。

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '471e68459202'
down_revision: Union[str, None] = '734e443c3f82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('rag_stats')
    op.drop_table('reference_snapshots')


def downgrade() -> None:
    """恢复孤儿表（仅结构，不恢复数据）。"""
    op.create_table(
        'rag_stats',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('total_documents', sa.Integer(), nullable=False),
        sa.Column('total_embeddings', sa.Integer(), nullable=False),
        sa.Column('last_rebuild_at', sa.String(length=50), nullable=True),
        sa.Column('source_counts', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'reference_snapshots',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=True),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.Column('source_type', sa.String(length=9), nullable=False),
        sa.Column('query_params', sa.JSON(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
