"""add gwy_score_line table

Revision ID: 9341ee5f3e2a
Revises: ea3210c5bf6c
Create Date: 2026-08-14 08:43:38.822586+00:00

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9341ee5f3e2a'
down_revision: Union[str, None] = 'ea3210c5bf6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 国考进面分数线（职位级聚合，无个人信息）；与采集器 fetch_gwy_interview.py
    # 列契约一致。手工裁剪：autogenerate 会把 create_all+stamp 的历史漂移带进来，
    # 与 gwy_position 迁移（ea3210c5bf6c）相同的处理方式。
    op.create_table('gwy_score_line',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('batch', sa.String(length=20), nullable=False),
    sa.Column('dept_name', sa.String(length=200), nullable=True),
    sa.Column('dept_code', sa.String(length=50), nullable=True),
    sa.Column('bureau', sa.String(length=200), nullable=True),
    sa.Column('position_name', sa.String(length=200), nullable=True),
    sa.Column('position_code', sa.String(length=50), nullable=False),
    sa.Column('min_score', sa.Float(), nullable=True),
    sa.Column('source_url', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('gwy_score_line', schema=None) as batch_op:
        batch_op.create_index('ix_gwy_score_line_year_code', ['year', 'position_code'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('gwy_score_line', schema=None) as batch_op:
        batch_op.drop_index('ix_gwy_score_line_year_code')
    op.drop_table('gwy_score_line')
