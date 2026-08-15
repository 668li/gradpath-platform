"""kaoyan news purity columns

Revision ID: 8d1a91d30ed3
Revises: 8bff65fa26e8
Create Date: 2026-08-15 08:51:30.910757+00:00

考研信息差升级：kaoyan_news 新增提纯与质量列。
注意：autogenerate 带入的历史漂移已手动裁剪，仅保留本表变更。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.base import JSONB

# revision identifiers, used by Alembic.
revision: str = '8d1a91d30ed3'
down_revision: Union[str, None] = '8bff65fa26e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('kaoyan_news', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ai_summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('quality_score', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('quality_grade', sa.String(length=2), nullable=True))
        batch_op.add_column(sa.Column('key_dates', JSONB(), nullable=False))
        batch_op.add_column(sa.Column('is_expired', sa.Boolean(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('kaoyan_news', schema=None) as batch_op:
        batch_op.drop_column('is_expired')
        batch_op.drop_column('key_dates')
        batch_op.drop_column('quality_grade')
        batch_op.drop_column('quality_score')
        batch_op.drop_column('ai_summary')
