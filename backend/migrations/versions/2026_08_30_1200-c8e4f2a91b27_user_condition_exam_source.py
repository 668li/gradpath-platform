"""user_condition_status 加 exam_source — 条件账本扩展省考赛道

Revision ID: c8e4f2a91b27
Revises: b5f2a7c81d34
Create Date: 2026-08-30 12:00:00.000000+00:00

国考/省考职位分表存储（gwy_position / gwy_province_position），
勾选状态表加 exam_source 区分赛道，唯一约束同步扩展。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8e4f2a91b27'
down_revision: str | None = 'b5f2a7c81d34'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'user_condition_status',
        sa.Column('exam_source', sa.String(length=10), nullable=False, server_default='national'),
    )
    # 唯一约束带上赛道（SQLite 建表即含新约束；PG 侧重建约束）
    op.drop_constraint('uq_user_condition_key', 'user_condition_status', type_='unique')
    op.create_unique_constraint(
        'uq_user_condition_key', 'user_condition_status',
        ['user_id', 'exam_source', 'position_id', 'condition_key'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_user_condition_key', 'user_condition_status', type_='unique')
    op.create_unique_constraint(
        'uq_user_condition_key', 'user_condition_status',
        ['user_id', 'position_id', 'condition_key'],
    )
    op.drop_column('user_condition_status', 'exam_source')
