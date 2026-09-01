"""path_comparisons 加 share_token — 决策报告公开分享

Revision ID: d3e5f7a9b2c4
Revises: add_gwy_pos_indexes
Create Date: 2026-09-01 12:00:00.000000+00:00

把「我的报考决策报告」改造成可分享形态：path_comparisons 新增 share_token，
非空即表示该决策已生成公开分享链接（无独立开关列，token 存在即启用）。
token 用 secrets.token_urlsafe 生成，配合唯一索引防止枚举。
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd3e5f7a9b2c4'
down_revision: str | None = 'add_gwy_pos_indexes'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'path_comparisons',
        sa.Column('share_token', sa.String(length=64), nullable=True),
    )
    op.create_index('ix_path_comparisons_share_token', 'path_comparisons', ['share_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_path_comparisons_share_token', table_name='path_comparisons')
    op.drop_column('path_comparisons', 'share_token')
