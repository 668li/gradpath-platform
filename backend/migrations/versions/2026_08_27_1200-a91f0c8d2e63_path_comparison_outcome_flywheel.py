"""path comparison outcome flywheel

Revision ID: a91f0c8d2e63
Revises: b3e8c7a1f602
Create Date: 2026-08-27 12:00:00.000000+00:00

决策飞轮第一圈：path_comparisons 新增结果回传字段（用户选择 + 实际结果 + 满意度）。
仿 destination_decisions 的字段集，仅本表变更。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a91f0c8d2e63'
down_revision: Union[str, None] = 'b3e8c7a1f602'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('path_comparisons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('selected_path', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('selected_label', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('outcome_status', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('actual_outcome', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('satisfaction', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('path_comparisons', schema=None) as batch_op:
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('satisfaction')
        batch_op.drop_column('actual_outcome')
        batch_op.drop_column('outcome_status')
        batch_op.drop_column('selected_label')
        batch_op.drop_column('selected_path')
